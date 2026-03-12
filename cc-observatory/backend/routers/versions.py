import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Version, VersionDiff

router = APIRouter(prefix="/api/versions", tags=["versions"])


@router.get("")
def list_versions(db: Session = Depends(get_db)):
    versions = db.query(Version).order_by(Version.detected_at.desc()).all()
    return [
        {
            "id": v.id,
            "version": v.version,
            "detected_at": v.detected_at.isoformat() if v.detected_at else None,
            "status": v.status,
            "summary": v.summary,
            "test_run_count": len(v.test_runs),
            "report_count": len(v.reports),
        }
        for v in versions
    ]


@router.get("/latest")
def latest_version(db: Session = Depends(get_db)):
    version = db.query(Version).order_by(Version.detected_at.desc()).first()
    if not version:
        raise HTTPException(status_code=404, detail="No versions found")
    return {
        "id": version.id,
        "version": version.version,
        "detected_at": version.detected_at.isoformat() if version.detected_at else None,
        "status": version.status,
        "summary": version.summary,
    }


@router.get("/{version_id}")
def version_detail(version_id: int, db: Session = Depends(get_db)):
    version = (
        db.query(Version)
        .options(joinedload(Version.test_runs), joinedload(Version.reports))
        .filter(Version.id == version_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "id": version.id,
        "version": version.version,
        "detected_at": version.detected_at.isoformat() if version.detected_at else None,
        "status": version.status,
        "summary": version.summary,
        "npm_metadata": json.loads(version.npm_metadata) if version.npm_metadata else None,
        "test_runs": [
            {
                "id": tr.id,
                "scenario_key": tr.scenario_key,
                "scenario_name": tr.scenario_name,
                "status": tr.status,
                "started_at": tr.started_at.isoformat() if tr.started_at else None,
                "finished_at": tr.finished_at.isoformat() if tr.finished_at else None,
                "error_message": tr.error_message,
            }
            for tr in version.test_runs
        ],
        "reports": [
            {
                "id": r.id,
                "report_type": r.report_type,
                "title": r.title,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            }
            for r in version.reports
        ],
    }


@router.get("/{version_id}/diff")
def version_diff(version_id: int, db: Session = Depends(get_db)):
    diffs = db.query(VersionDiff).filter(VersionDiff.version_id == version_id).all()
    return [
        {
            "id": d.id,
            "version_id": d.version_id,
            "prev_version_id": d.prev_version_id,
            "scenario_key": d.scenario_key,
            "diff_type": d.diff_type,
            "diff_content": d.diff_content,
            "change_summary": d.change_summary,
            "significance": d.significance,
        }
        for d in diffs
    ]
