from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas, storage
from app.audit import log
from app.core.database import get_db
from app.deps import get_current_user, require_fund_access
from app.excel_engine.extractor import extract_workbook

router = APIRouter(tags=["uploads"])


@router.post(
    "/funds/{fund_id}/periods/{period_id}/workbooks",
    response_model=schemas.WorkbookOut,
    status_code=201,
)
async def upload_workbook(
    fund_id: int,
    period_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot upload workbooks")

    period = db.get(models.Period, period_id)
    if not period or period.fund_id != fund_id:
        raise HTTPException(status_code=404, detail="Period not found for this fund")

    mapping_config = (
        db.query(models.MappingConfig)
        .filter(models.MappingConfig.fund_id == fund_id, models.MappingConfig.status == "confirmed")
        .order_by(models.MappingConfig.version.desc())
        .first()
    )
    if not mapping_config:
        raise HTTPException(
            status_code=400,
            detail="No confirmed mapping config exists for this fund yet. Confirm a mapping before uploading data.",
        )

    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Workbook must be an .xlsx or .xlsm file")

    content = await file.read()
    rel_path = storage.workbook_path(fund.client_id, fund.id, period.id, file.filename)
    storage.storage.save(rel_path, content)
    abs_path = storage.storage.abspath(rel_path)

    try:
        extracted = extract_workbook(str(abs_path), mapping_config.config_json)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to extract workbook: {exc}")

    workbook = models.UploadedWorkbook(
        fund_id=fund_id,
        period_id=period_id,
        mapping_config_id=mapping_config.id,
        filename=file.filename,
        storage_path=rel_path,
        extracted_data_json=extracted,
        uploaded_by_id=user.id,
    )
    db.add(workbook)
    db.commit()
    db.refresh(workbook)
    log(db, "workbook", workbook.id, user.id, "upload", file.filename)
    return workbook


@router.get("/funds/{fund_id}/periods/{period_id}/workbooks", response_model=list[schemas.WorkbookOut])
def list_workbooks(
    fund_id: int, period_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)
    return (
        db.query(models.UploadedWorkbook)
        .filter(models.UploadedWorkbook.fund_id == fund_id, models.UploadedWorkbook.period_id == period_id)
        .order_by(models.UploadedWorkbook.uploaded_at.desc())
        .all()
    )


@router.get("/workbooks/{workbook_id}")
def get_workbook(workbook_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    workbook = db.get(models.UploadedWorkbook, workbook_id)
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found")
    fund = db.get(models.Fund, workbook.fund_id)
    require_fund_access(fund, db, user)
    return {
        "id": workbook.id,
        "fund_id": workbook.fund_id,
        "period_id": workbook.period_id,
        "filename": workbook.filename,
        "mapping_config_id": workbook.mapping_config_id,
        "extracted_data": workbook.extracted_data_json,
        "uploaded_at": workbook.uploaded_at,
    }
