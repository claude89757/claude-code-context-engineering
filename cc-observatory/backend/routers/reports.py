from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AnalysisReport

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
def list_reports(
    version_id: Optional[int] = None,
    report_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisReport)
    if version_id is not None:
        query = query.filter(AnalysisReport.version_id == version_id)
    if report_type is not None:
        query = query.filter(AnalysisReport.report_type == report_type)
    reports = query.all()
    return [
        {
            "id": r.id,
            "version_id": r.version_id,
            "report_type": r.report_type,
            "title": r.title,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "model_used": r.model_used,
        }
        for r in reports
    ]


@router.get("/{report_id}")
def report_detail(report_id: int, db: Session = Depends(get_db)):
    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": report.id,
        "version_id": report.version_id,
        "report_type": report.report_type,
        "title": report.title,
        "content": report.content,
        "model_used": report.model_used,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "token_cost": report.token_cost,
    }
