"""Scheduler and patrol orchestration for CC Observatory.

Periodically checks for new Claude Code versions, runs test scenarios,
extracts data, computes diffs, and generates analysis reports.
"""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime, timezone

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
    get_latest_npm_version,
    get_npm_metadata,
    install_claude_code_version,
)

logger = logging.getLogger(__name__)

_patrol_status: dict = {
    "running": False,
    "last_run": None,
    "current_task": None,
    "error": None,
}


def get_patrol_status() -> dict:
    """Return a copy of the current patrol status."""
    return copy.deepcopy(_patrol_status)


async def run_patrol() -> None:  # noqa: C901
    """Main patrol job.

    Checks for a new Claude Code npm version and, when one is found,
    installs it, runs every scenario, extracts data, computes diffs
    against the previous version, and generates an LLM analysis report.
    """
    global _patrol_status

    if _patrol_status["running"]:
        logger.info("Patrol already running, skipping.")
        return

    _patrol_status["running"] = True
    _patrol_status["error"] = None
    _patrol_status["current_task"] = "checking latest version"
    db = SessionLocal()

    try:
        # 1. Get latest npm version
        latest = get_latest_npm_version()
        logger.info("Latest npm version: %s", latest)

        # 2. Check if already in DB
        existing = db.query(Version).filter(Version.version == latest).first()
        if existing:
            logger.info("Version %s already exists in DB, skipping.", latest)
            _patrol_status["current_task"] = None
            return

        # 3. Create Version record
        _patrol_status["current_task"] = f"registering version {latest}"
        npm_meta = get_npm_metadata(latest)
        version_record = Version(
            version=latest,
            npm_metadata=json.dumps(npm_meta),
            status="testing",
        )
        db.add(version_record)
        db.commit()
        db.refresh(version_record)

        # 4. Install claude-code
        _patrol_status["current_task"] = f"installing claude-code@{latest}"
        install_dir = str(TRACES_DIR / latest / "_install")
        claude_cli_path = install_claude_code_version(latest, install_dir)
        logger.info("Installed claude-code at %s", claude_cli_path)

        # 5. Run all scenarios
        for scenario in SCENARIOS:
            key = scenario["key"]
            mode = scenario["mode"]
            _patrol_status["current_task"] = f"running scenario: {key}"
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
                        version=latest,
                    )
                elif mode == "multi_turn":
                    result = run_multi_turn_scenario(
                        claude_cli_path=claude_cli_path,
                        turns=scenario.get("turns", []),
                        scenario_key=key,
                        version=latest,
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

        # 6. Compute diffs against previous version
        _patrol_status["current_task"] = "computing diffs"
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

        # 7. Generate LLM report
        _patrol_status["current_task"] = "generating LLM report"
        try:
            from backend.services.llm_analyzer import generate_version_report

            extracted_samples = {}
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
                    extracted_samples[run.scenario_key] = _extracted_record_to_dict(
                        run.extracted_data
                    )

            if extracted_samples:
                report = generate_version_report(latest, extracted_samples)
                report_record = AnalysisReport(
                    version_id=version_record.id,
                    report_type="version_summary",
                    title=f"Version {latest} Analysis Report",
                    content=report.get("content", ""),
                    model_used=report.get("model_used"),
                    token_cost=json.dumps(report.get("token_cost")),
                )
                db.add(report_record)
                db.commit()
        except ImportError:
            logger.warning("llm_analyzer not available, skipping report generation.")
        except Exception:
            logger.exception("Error generating LLM report")

        # 8. Mark version as analyzed
        version_record.status = "analyzed"
        db.commit()
        logger.info("Patrol completed for version %s", latest)

    except Exception as exc:
        logger.exception("Patrol failed")
        _patrol_status["error"] = str(exc)
    finally:
        _patrol_status["running"] = False
        _patrol_status["current_task"] = None
        _patrol_status["last_run"] = datetime.now(timezone.utc).isoformat()
        db.close()


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
