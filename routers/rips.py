import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from database import get_db
from models.rips import RIPSReport, RIPSStatus
from models.user import User, UserRole
from schemas.rips import RIPSReportCreate, RIPSReportResponse
from services.rips_service import create_rips_report
from core.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/rips", tags=["RIPS"])


@router.post("/generate", response_model=RIPSReportResponse, status_code=201,
             summary="Generar reporte RIPS 2.0")
def generate_rips(
    body: RIPSReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera el reporte RIPS 2.0 para el período indicado.
    Disponible para: ADMIN y AUDITOR.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.AUDITOR):
        raise HTTPException(status_code=403, detail="Solo ADMIN o AUDITOR pueden generar RIPS")

    if body.period_end < body.period_start:
        raise HTTPException(status_code=400, detail="La fecha de fin debe ser posterior a la de inicio")

    report = create_rips_report(
        db=db,
        period_start=body.period_start,
        period_end=body.period_end,
        generated_by_id=current_user.id,
        notes=body.notes,
    )
    return report


@router.get("/", response_model=List[RIPSReportResponse], summary="Listar reportes RIPS")
def list_rips_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.AUDITOR):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return db.query(RIPSReport).order_by(RIPSReport.generated_at.desc()).all()


@router.get("/{report_id}/download", summary="Descargar JSON del reporte RIPS")
def download_rips(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el JSON RIPS 2.0 listo para enviar a la ADRES."""
    if current_user.role not in (UserRole.ADMIN, UserRole.AUDITOR):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    report = db.query(RIPSReport).filter(RIPSReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    if not report.report_json:
        raise HTTPException(status_code=404, detail="El reporte no tiene contenido JSON")

    filename = f"RIPS_{report.period_start}_{report.period_end}.json"
    return JSONResponse(
        content=json.loads(report.report_json),
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.patch("/{report_id}/submit", response_model=RIPSReportResponse,
              summary="Marcar RIPS como enviado")
def mark_rips_submitted(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Marca el reporte como enviado a la ADRES."""
    from datetime import datetime, timezone
    report = db.query(RIPSReport).filter(RIPSReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    report.status = RIPSStatus.SUBMITTED
    report.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report
