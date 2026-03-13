import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import TestRun

router = APIRouter(prefix="/api/test-runs", tags=["test_runs"])


@router.get("")
def list_test_runs(
    version_id: Optional[int] = None,
    scenario_key: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(TestRun)
    if version_id is not None:
        query = query.filter(TestRun.version_id == version_id)
    if scenario_key is not None:
        query = query.filter(TestRun.scenario_key == scenario_key)
    runs = query.all()
    return [
        {
            "id": r.id,
            "version_id": r.version_id,
            "scenario_key": r.scenario_key,
            "scenario_name": r.scenario_name,
            "scenario_group": r.scenario_group,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "error_message": r.error_message,
        }
        for r in runs
    ]


@router.get("/{run_id}")
def test_run_detail(run_id: int, db: Session = Depends(get_db)):
    run = (
        db.query(TestRun)
        .options(joinedload(TestRun.extracted_data))
        .filter(TestRun.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")

    extracted = None
    if run.extracted_data:
        ed = run.extracted_data
        extracted = {
            "id": ed.id,
            "system_prompt": ed.system_prompt,
            "system_blocks": _safe_json(ed.system_blocks),
            "tools": _safe_json(ed.tools),
            "tool_names": _safe_json(ed.tool_names),
            "deferred_tools": _safe_json(ed.deferred_tools),
            "messages_chain": _safe_json(ed.messages_chain),
            "api_calls": _safe_json(ed.api_calls),
            "system_reminders": _safe_json(ed.system_reminders),
            "cache_strategy": _safe_json(ed.cache_strategy),
            "token_usage": _safe_json(ed.token_usage),
            "model_used": ed.model_used,
        }

    # 查找同场景前一版本的数据
    prev_run = (
        db.query(TestRun)
        .options(joinedload(TestRun.extracted_data))
        .filter(
            TestRun.scenario_key == run.scenario_key,
            TestRun.version_id < run.version_id,
            TestRun.status == "success",
        )
        .order_by(TestRun.version_id.desc())
        .first()
    )

    result = {
        "id": run.id,
        "version_id": run.version_id,
        "scenario_key": run.scenario_key,
        "scenario_name": run.scenario_name,
        "scenario_group": run.scenario_group,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error_message": run.error_message,
        "extracted_data": extracted,
        "diff_data": {
            "original": prev_run.extracted_data.system_prompt if prev_run and prev_run.extracted_data else None,
            "modified": run.extracted_data.system_prompt if run.extracted_data else None,
            "prev_version_id": prev_run.version_id if prev_run else None,
        },
    }

    return result


@router.get("/{run_id}/raw")
def test_run_raw(run_id: int, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    return {"raw_jsonl": run.raw_jsonl}


def _safe_json(val):
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val
