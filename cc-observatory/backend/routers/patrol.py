import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import AnalysisReport, ExtractedData, TestRun, Version
from backend.services.extractor import extract_from_jsonl
from backend.services.scheduler import (
    get_available_versions_async,
    get_patrol_status,
    run_batch_patrol,
    run_patrol,
)

router = APIRouter(prefix="/api/patrol", tags=["patrol"])


@router.get("/status")
def patrol_status():
    return get_patrol_status()


@router.post("/trigger")
async def trigger_patrol():
    asyncio.create_task(run_patrol())
    return {"message": "Patrol triggered"}


@router.get("/available-versions")
async def available_versions():
    """List npm versions not yet analyzed."""
    versions = await get_available_versions_async()
    return {"versions": versions}


class BatchTriggerRequest(BaseModel):
    versions: list[str]


@router.post("/trigger-batch")
async def trigger_batch_patrol(req: BatchTriggerRequest):
    """Trigger patrol for multiple specific versions."""
    if not req.versions:
        raise HTTPException(status_code=400, detail="No versions specified")
    asyncio.create_task(run_batch_patrol(req.versions))
    return {"message": f"Batch patrol triggered for {len(req.versions)} versions", "versions": req.versions}


class ImportRequest(BaseModel):
    version: str
    scenario_key: str
    scenario_name: str = ""
    scenario_group: str = ""
    raw_jsonl: str


@router.post("/import")
def import_trace(req: ImportRequest, db: Session = Depends(get_db)):
    """Import a raw JSONL trace file for a given version and scenario."""
    # Get or create version
    version_record = db.query(Version).filter(Version.version == req.version).first()
    if not version_record:
        version_record = Version(
            version=req.version,
            status="analyzed",
        )
        db.add(version_record)
        db.commit()
        db.refresh(version_record)

    # Create test run
    now = datetime.now(timezone.utc)
    test_run = TestRun(
        version_id=version_record.id,
        scenario_key=req.scenario_key,
        scenario_name=req.scenario_name or req.scenario_key,
        scenario_group=req.scenario_group,
        status="success",
        started_at=now,
        finished_at=now,
        raw_jsonl=req.raw_jsonl,
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    # Extract structured data
    extracted = extract_from_jsonl(req.raw_jsonl)
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
    db.commit()

    return {
        "message": "Import successful",
        "version_id": version_record.id,
        "test_run_id": test_run.id,
        "extracted": {
            "model_used": extracted.get("model_used"),
            "system_prompt_length": len(extracted.get("system_prompt", "")),
            "tool_count": len(extracted.get("tool_names", [])),
            "api_call_count": len(extracted.get("api_calls", [])),
        },
    }


@router.post("/fix-stuck")
async def fix_stuck_versions(db: Session = Depends(get_db)):
    """Fix versions stuck in 'testing' status by marking them as 'analyzed'."""
    stuck = db.query(Version).filter(Version.status == "testing").all()
    fixed = []
    for v in stuck:
        v.status = "analyzed"
        fixed.append(v.version)
    db.commit()
    return {"fixed": fixed, "count": len(fixed)}


@router.post("/generate-report/{version_id}")
async def generate_report(version_id: int, db: Session = Depends(get_db)):
    """Generate an LLM analysis report for a given version."""
    version_record = db.query(Version).filter(Version.id == version_id).first()
    if not version_record:
        raise HTTPException(status_code=404, detail="Version not found")

    # Collect extracted data from successful test runs
    completed_runs = (
        db.query(TestRun)
        .options(joinedload(TestRun.extracted_data))
        .filter(
            TestRun.version_id == version_id,
            TestRun.status == "success",
        )
        .all()
    )

    if not completed_runs:
        raise HTTPException(status_code=400, detail="No successful test runs to analyze")

    # Build extracted samples summary for prompt
    samples_info = []
    for run in completed_runs:
        ed = run.extracted_data
        if not ed:
            continue
        tool_names = json.loads(ed.tool_names) if ed.tool_names else []
        deferred = json.loads(ed.deferred_tools) if ed.deferred_tools else []
        api_calls = json.loads(ed.api_calls) if ed.api_calls else []
        cache = json.loads(ed.cache_strategy) if ed.cache_strategy else []
        sys_blocks = json.loads(ed.system_blocks) if ed.system_blocks else []
        reminders = json.loads(ed.system_reminders) if ed.system_reminders else []
        token_usage = json.loads(ed.token_usage) if ed.token_usage else {}

        samples_info.append({
            "scenario_key": run.scenario_key,
            "scenario_name": run.scenario_name,
            "model_used": ed.model_used,
            "system_prompt_length": len(ed.system_prompt) if ed.system_prompt else 0,
            "system_blocks_count": len(sys_blocks),
            "tool_names": tool_names,
            "deferred_tools_count": len(deferred),
            "api_calls_count": len(api_calls),
            "cache_strategy": cache,
            "system_reminders_count": len(reminders),
            "token_usage": token_usage,
        })

    # Build prompt
    from backend.services.llm_analyzer import call_llm

    samples_text = ""
    for s in samples_info:
        samples_text += f"\n### 场景: {s['scenario_key']} ({s['scenario_name']})\n"
        samples_text += f"- 模型: {s['model_used']}\n"
        samples_text += f"- System Prompt 长度: {s['system_prompt_length']} 字符\n"
        samples_text += f"- System Blocks 数量: {s['system_blocks_count']}\n"
        samples_text += f"- 核心工具: {', '.join(s['tool_names'])}\n"
        samples_text += f"- 延迟加载工具数: {s['deferred_tools_count']}\n"
        samples_text += f"- API 调用数: {s['api_calls_count']}\n"
        samples_text += f"- 缓存策略: {json.dumps(s['cache_strategy'], ensure_ascii=False)}\n"
        samples_text += f"- System Reminders 数: {s['system_reminders_count']}\n"
        samples_text += f"- Token 使用: {json.dumps(s['token_usage'], ensure_ascii=False)}\n"

    # Get system prompt text from first run for detailed analysis
    first_ed = completed_runs[0].extracted_data
    system_prompt_excerpt = ""
    if first_ed and first_ed.system_prompt:
        # Truncate to avoid token limit issues
        sp = first_ed.system_prompt
        if len(sp) > 8000:
            system_prompt_excerpt = sp[:4000] + "\n\n... [中间省略] ...\n\n" + sp[-4000:]
        else:
            system_prompt_excerpt = sp

    prompt = f"""你是 Claude Code 上下文工程分析专家。请对 Claude Code v{version_record.version} 版本进行全面的上下文工程分析。

## System Prompt 内容（节选）

```
{system_prompt_excerpt}
```

## 各场景测试数据摘要
{samples_text}

请从以下维度进行深入分析，使用 Markdown 格式输出：

### 1. 版本概述
简要总结该版本的 Claude Code 特征，包括其模型、核心能力等。

### 2. System Prompt 架构分析
详细分析 system prompt 的结构设计：
- 分层架构（有几个 block、各 block 的作用）
- 指令优先级和组织方式
- 安全约束的设计
- 工具使用指南的设计

### 3. 上下文工程策略
分析其上下文工程的核心策略：
- 缓存策略（ephemeral cache 的使用）
- 延迟加载机制（deferred tools 的设计）
- 消息链的增长模式
- System Reminders 的注入策略

### 4. 工具体系分析
分析工具体系的设计：
- 核心工具 vs 延迟加载工具的划分逻辑
- 各工具的协作模式
- Agent 子代理机制

### 5. 关键设计模式总结
提炼出该版本中值得关注的上下文工程设计模式和最佳实践。
"""

    result = await call_llm(prompt)

    # Save report
    report_record = AnalysisReport(
        version_id=version_id,
        report_type="version_summary",
        title=f"Version {version_record.version} 上下文工程分析报告",
        content=result.get("content", ""),
        model_used=result.get("model_used"),
        token_cost=json.dumps(result.get("token_cost")),
    )
    db.add(report_record)

    # Update version summary
    content = result.get("content", "")
    summary_lines = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("```"):
            summary_lines.append(line)
            if len(summary_lines) >= 2:
                break
    version_record.summary = " ".join(summary_lines)[:200] if summary_lines else f"v{version_record.version} analysis completed"

    db.commit()

    return {
        "message": "Report generated",
        "report_id": report_record.id,
        "model_used": result.get("model_used"),
        "content_length": len(result.get("content", "")),
        "token_cost": result.get("token_cost"),
    }
