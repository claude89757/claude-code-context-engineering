import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import TestRun
from backend.scenarios import SCENARIOS

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios():
    return SCENARIOS


@router.get("/{key}/history")
def scenario_history(key: str, db: Session = Depends(get_db)):
    runs = (
        db.query(TestRun)
        .options(joinedload(TestRun.extracted_data))
        .filter(TestRun.scenario_key == key, TestRun.status == "success")
        .order_by(TestRun.started_at.asc())
        .all()
    )
    result = []
    for run in runs:
        ed = run.extracted_data
        if not ed:
            continue
        system_prompt_length = len(ed.system_prompt) if ed.system_prompt else 0
        tool_names = _safe_json(ed.tool_names)
        tool_count = len(tool_names) if isinstance(tool_names, list) else 0
        result.append({
            "test_run_id": run.id,
            "version_id": run.version_id,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "system_prompt_length": system_prompt_length,
            "tool_count": tool_count,
            "model_used": ed.model_used,
            "token_usage": _safe_json(ed.token_usage),
        })
    return result


def _safe_json(val):
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val
