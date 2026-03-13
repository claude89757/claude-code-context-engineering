"""Scheduler and patrol orchestration for Context Engineering Observatory.

Periodically checks for new Claude Code versions, runs test scenarios,
extracts data, computes diffs, and generates analysis reports.
Supports analyzing specific versions and batch multi-version analysis.

All heavy work (npm install, subprocess, DB) runs in a thread pool so
the async event loop stays responsive for API requests.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import PATROL_INTERVAL_MINUTES, TRACES_DIR
from backend.database import SessionLocal
from backend.models import (
    AnalysisReport,
    ExtractedData,
    TestRun,
    Version,
    VersionDiff,
)
from backend.scenarios import SCENARIOS
from backend.services.differ import compute_version_diffs
from backend.services.extractor import extract_from_jsonl
from backend.services.test_runner import run_multi_turn_scenario, run_single_prompt_scenario
from backend.services.version_checker import (
    get_all_npm_versions,
    get_latest_npm_version,
    get_npm_metadata,
    install_claude_code_version,
)

logger = logging.getLogger(__name__)

# Dedicated thread pool for patrol work so it doesn't block the event loop
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="patrol")

_patrol_status: dict = {
    "running": False,
    "last_run": None,
    "current_task": None,
    "error": None,
}


def get_patrol_status() -> dict:
    """Return a copy of the current patrol status."""
    return copy.deepcopy(_patrol_status)


# ---------------------------------------------------------------------------
# Public async entry points (safe to call from the event loop)
# ---------------------------------------------------------------------------

async def run_patrol(target_version: str | None = None) -> None:
    """Main patrol job — single-version entry point with lock management."""
    global _patrol_status

    if _patrol_status["running"]:
        logger.info("Patrol already running, skipping.")
        return

    _patrol_status["running"] = True
    _patrol_status["error"] = None

    try:
        loop = asyncio.get_event_loop()
        if target_version:
            version = target_version
        else:
            version = await loop.run_in_executor(_executor, get_latest_npm_version)
        _patrol_status["current_task"] = f"analyzing {version}"
        await loop.run_in_executor(_executor, _sync_patrol_for_version, version)
    except Exception as exc:
        logger.exception("Patrol failed")
        _patrol_status["error"] = str(exc)
    finally:
        _patrol_status["running"] = False
        _patrol_status["current_task"] = None
        _patrol_status["last_run"] = datetime.now(timezone.utc).isoformat()


async def run_batch_patrol(versions: list[str]) -> None:
    """Analyze multiple Claude Code versions sequentially in a thread pool."""
    global _patrol_status

    if _patrol_status["running"]:
        logger.info("Patrol already running, skipping batch.")
        return

    _patrol_status["running"] = True
    _patrol_status["error"] = None
    total = len(versions)
    loop = asyncio.get_event_loop()

    try:
        for i, version in enumerate(versions, 1):
            logger.info("Batch patrol: processing version %s (%d/%d)", version, i, total)
            _patrol_status["current_task"] = f"batch: {version} ({i}/{total})"
            await loop.run_in_executor(_executor, _sync_patrol_for_version, version)
    except Exception as exc:
        logger.exception("Batch patrol failed")
        _patrol_status["error"] = str(exc)
    finally:
        _patrol_status["running"] = False
        _patrol_status["current_task"] = None
        _patrol_status["last_run"] = datetime.now(timezone.utc).isoformat()

    logger.info("Batch patrol completed for %d versions", total)


async def get_available_versions_async() -> list[str]:
    """Return npm versions not yet in the database (non-blocking)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, get_available_versions)


def get_available_versions() -> list[str]:
    """Return npm versions that are not yet in the database."""
    db = SessionLocal()
    try:
        all_versions = get_all_npm_versions()
        existing = {v.version for v in db.query(Version.version).all()}
        return [v for v in all_versions if v not in existing]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Synchronous patrol logic (runs in thread pool)
# ---------------------------------------------------------------------------

def _sync_patrol_for_version(version: str) -> None:  # noqa: C901
    """Core patrol logic for a single version. Runs in a worker thread."""
    db = SessionLocal()

    try:
        # 1. Check if already in DB
        existing = db.query(Version).filter(Version.version == version).first()
        if existing:
            logger.info("Version %s already exists in DB, skipping.", version)
            return

        # 2. Create Version record
        _patrol_status["current_task"] = f"registering version {version}"
        npm_meta = get_npm_metadata(version)
        version_record = Version(
            version=version,
            npm_metadata=json.dumps(npm_meta),
            status="testing",
        )
        db.add(version_record)
        db.commit()
        db.refresh(version_record)

        # 3. Install claude-code
        _patrol_status["current_task"] = f"installing claude-code@{version}"
        install_dir = str(TRACES_DIR / version / "_install")
        claude_cli_path = install_claude_code_version(version, install_dir)
        logger.info("Installed claude-code at %s", claude_cli_path)

        # 4. Run all scenarios
        for scenario in SCENARIOS:
            key = scenario["key"]
            mode = scenario["mode"]
            _patrol_status["current_task"] = f"running scenario: {key} ({version})"
            logger.info("Running scenario: %s", key)

            test_run = TestRun(
                version_id=version_record.id,
                scenario_key=key,
                scenario_name=scenario.get("name"),
                scenario_group=scenario.get("group"),
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.add(test_run)
            db.commit()
            db.refresh(test_run)

            try:
                if mode == "single_prompt" or mode == "paired":
                    result = run_single_prompt_scenario(
                        claude_cli_path=claude_cli_path,
                        prompt=scenario["prompt"],
                        scenario_key=key,
                        version=version,
                    )
                elif mode == "multi_turn":
                    result = run_multi_turn_scenario(
                        claude_cli_path=claude_cli_path,
                        turns=scenario.get("turns", []),
                        scenario_key=key,
                        version=version,
                    )
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown mode: {mode}",
                        "raw_jsonl": None,
                    }

                if result["success"] and result.get("raw_jsonl"):
                    test_run.raw_jsonl = result["raw_jsonl"]
                    test_run.status = "success"

                    # Extract structured data
                    extracted = extract_from_jsonl(result["raw_jsonl"])
                    extracted_record = ExtractedData(
                        test_run_id=test_run.id,
                        system_prompt=extracted.get("system_prompt"),
                        system_blocks=json.dumps(extracted.get("system_blocks", [])),
                        tools=json.dumps(extracted.get("tools", [])),
                        tool_names=json.dumps(extracted.get("tool_names", [])),
                        deferred_tools=json.dumps(extracted.get("deferred_tools", [])),
                        messages_chain=json.dumps(extracted.get("messages_chain", [])),
                        api_calls=json.dumps(extracted.get("api_calls", [])),
                        system_reminders=json.dumps(extracted.get("system_reminders", [])),
                        cache_strategy=json.dumps(extracted.get("cache_strategy", [])),
                        token_usage=json.dumps(extracted.get("token_usage", {})),
                        model_used=extracted.get("model_used"),
                    )
                    db.add(extracted_record)
                else:
                    test_run.status = "error"
                    test_run.error_message = result.get("error", "Unknown error")
            except Exception as exc:
                logger.exception("Error running scenario %s", key)
                test_run.status = "error"
                test_run.error_message = str(exc)

            test_run.finished_at = datetime.now(timezone.utc)
            db.commit()

        # 5. Compute diffs against previous version (non-fatal)
        try:
            _patrol_status["current_task"] = f"computing diffs ({version})"
            prev_version = (
                db.query(Version)
                .filter(Version.id != version_record.id, Version.status.in_(["analyzed", "testing"]))
                .order_by(Version.detected_at.desc())
                .first()
            )

            if prev_version:
                for scenario in SCENARIOS:
                    key = scenario["key"]
                    new_run = (
                        db.query(TestRun)
                        .filter(
                            TestRun.version_id == version_record.id,
                            TestRun.scenario_key == key,
                            TestRun.status == "success",
                        )
                        .first()
                    )
                    old_run = (
                        db.query(TestRun)
                        .filter(
                            TestRun.version_id == prev_version.id,
                            TestRun.scenario_key == key,
                            TestRun.status == "success",
                        )
                        .first()
                    )
                    if not new_run or not old_run:
                        continue

                    new_data = new_run.extracted_data
                    old_data = old_run.extracted_data
                    if not new_data or not old_data:
                        continue

                    old_extracted = _extracted_record_to_dict(old_data)
                    new_extracted = _extracted_record_to_dict(new_data)

                    diffs = compute_version_diffs(old_extracted, new_extracted)
                    for diff in diffs:
                        diff_content = diff.get("diff_content", "")
                        if isinstance(diff_content, (dict, list)):
                            diff_content = json.dumps(diff_content)
                        diff_record = VersionDiff(
                            version_id=version_record.id,
                            prev_version_id=prev_version.id,
                            scenario_key=key,
                            diff_type=diff.get("diff_type"),
                            diff_content=diff_content,
                            change_summary=diff.get("change_summary"),
                            significance=diff.get("significance"),
                        )
                        db.add(diff_record)

                db.commit()
        except Exception:
            logger.exception("Error computing diffs for version %s", version)

        # 6. Generate LLM report (sync httpx call from thread)
        _patrol_status["current_task"] = f"generating LLM report ({version})"
        try:
            _sync_generate_report(db, version_record, version)
        except ImportError:
            logger.warning("llm_analyzer not available, skipping report generation.")
        except Exception:
            logger.exception("Error generating LLM report")

        # 7. Mark version as analyzed
        version_record.status = "analyzed"
        db.commit()
        logger.info("Patrol completed for version %s", version)

    finally:
        db.close()


def _sync_generate_report(db, version_record, version: str) -> None:
    """Generate LLM report synchronously (called from worker thread)."""
    import httpx

    from backend.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    from backend.services.llm_analyzer import generate_version_report

    extracted_samples = []
    diffs_for_report = []
    completed_runs = (
        db.query(TestRun)
        .filter(
            TestRun.version_id == version_record.id,
            TestRun.status == "success",
        )
        .all()
    )
    for run in completed_runs:
        if run.extracted_data:
            sample = _extracted_record_to_dict(run.extracted_data)
            sample["scenario_key"] = run.scenario_key
            extracted_samples.append(sample)

    # Collect diffs for report
    version_diffs = (
        db.query(VersionDiff)
        .filter(VersionDiff.version_id == version_record.id)
        .all()
    )
    for d in version_diffs:
        diffs_for_report.append({
            "name": f"{d.scenario_key}/{d.diff_type}",
            "content": d.diff_content or "",
        })

    if not extracted_samples:
        logger.warning("No extracted samples for version %s, skipping report.", version)
        return

    # Build the same prompt that generate_version_report would build,
    # but call the LLM synchronously so we stay in the worker thread.
    diffs_text = ""
    for i, d in enumerate(diffs_for_report, 1):
        file_name = d.get("name", f"diff_{i}")
        diff_content = d.get("content", "")
        diffs_text += f"\n### Diff {i}: {file_name}\n```\n{diff_content}\n```\n"

    samples_text = ""
    for i, s in enumerate(extracted_samples, 1):
        scenario = s.get("scenario_key", f"sample_{i}")
        samples_text += f"\n### Sample {i}: {scenario}\n"
        for k, v in s.items():
            if k == "scenario_key":
                continue
            samples_text += f"- **{k}**: {v}\n"

    prompt = f"""你是 Claude Code 版本变更分析专家。请根据以下信息对 Claude Code {version} 版本进行深入分析。

## 变更 Diff

{diffs_text}

## 提取的样本数据

{samples_text}

请从以下五个维度进行分析，使用 Markdown 格式输出：

### 1. 变更概述
简要总结本次版本更新的主要变更内容。

### 2. 上下文工程分析
分析 system prompt、工具定义、消息链等上下文工程层面的变化，包括 prompt 结构、指令措辞、工具能力等方面的调整。

### 3. 意图推测
基于变更内容，推测 Anthropic 团队的产品意图和技术方向。

### 4. 影响评估
评估这些变更对用户体验、模型行为、开发者工作流的潜在影响。

### 5. 趋势判断
结合已知的 Claude Code 发展脉络，判断这些变更所体现的产品演进趋势。
"""

    # Synchronous HTTP call
    url = f"{LLM_BASE_URL}/v1/messages"
    headers = {
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": LLM_MODEL,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }

    with httpx.Client(timeout=120) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    text_parts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block["text"])
    content = "\n".join(text_parts)

    usage = data.get("usage", {})
    model_used = data.get("model", LLM_MODEL)
    token_cost = {
        "input": usage.get("input_tokens", 0),
        "output": usage.get("output_tokens", 0),
    }

    report_record = AnalysisReport(
        version_id=version_record.id,
        report_type="version_summary",
        title=f"Version {version} Analysis Report",
        content=content,
        model_used=model_used,
        token_cost=json.dumps(token_cost),
    )
    db.add(report_record)
    db.commit()


def _extracted_record_to_dict(record: ExtractedData) -> dict:
    """Convert an ExtractedData ORM record back to a plain dict."""

    def _safe_json_loads(val: str | None, default=None):
        if val is None:
            return default if default is not None else []
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else []

    return {
        "system_prompt": record.system_prompt or "",
        "system_blocks": _safe_json_loads(record.system_blocks),
        "tools": _safe_json_loads(record.tools),
        "tool_names": _safe_json_loads(record.tool_names),
        "deferred_tools": _safe_json_loads(record.deferred_tools),
        "messages_chain": _safe_json_loads(record.messages_chain),
        "api_calls": _safe_json_loads(record.api_calls),
        "system_reminders": _safe_json_loads(record.system_reminders),
        "cache_strategy": _safe_json_loads(record.cache_strategy),
        "token_usage": _safe_json_loads(record.token_usage, default={}),
        "model_used": record.model_used,
    }


def start_scheduler() -> AsyncIOScheduler:
    """Create and start the APScheduler with the patrol job."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_patrol,
        "interval",
        minutes=PATROL_INTERVAL_MINUTES,
        id="patrol_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started, patrol interval: %d minutes", PATROL_INTERVAL_MINUTES
    )
    return scheduler
