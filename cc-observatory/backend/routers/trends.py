import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import TestRun, Version

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("")
def get_trends(
    metric: str = "system_prompt_length",
    scenario_key: str = "basic_chat",
    db: Session = Depends(get_db),
):
    versions = (
        db.query(Version)
        .filter(Version.status.in_(["analyzed", "testing"]))
        .order_by(Version.detected_at.asc())
        .all()
    )

    data = []
    for v in versions:
        run = (
            db.query(TestRun)
            .options(joinedload(TestRun.extracted_data))
            .filter(
                TestRun.version_id == v.id,
                TestRun.scenario_key == scenario_key,
                TestRun.status == "success",
            )
            .first()
        )
        if not run or not run.extracted_data:
            continue

        ed = run.extracted_data
        value = _extract_metric(ed, metric)
        if value is not None:
            data.append({
                "version": v.version,
                "detected_at": v.detected_at.isoformat() if v.detected_at else None,
                "value": value,
            })

    return {
        "metric": metric,
        "scenario_key": scenario_key,
        "data": data,
    }


def _extract_metric(ed, metric: str):
    if metric == "system_prompt_length":
        return len(ed.system_prompt) if ed.system_prompt else 0
    elif metric == "tool_count":
        tool_names = _safe_json(ed.tool_names)
        return len(tool_names) if isinstance(tool_names, list) else 0
    elif metric == "token_usage":
        usage = _safe_json(ed.token_usage)
        if isinstance(usage, dict):
            return usage.get("total", usage.get("input", 0))
        return 0
    return None


def _safe_json(val):
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val
