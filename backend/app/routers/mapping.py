import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas, storage
from app.audit import log
from app.core.database import get_db
from app.deps import get_current_user, require_fund_access
from app.excel_engine.inspector import infer_mapping

router = APIRouter(tags=["mapping"])


@router.post("/funds/{fund_id}/mapping/infer", response_model=schemas.InferMappingResponse)
async def infer_fund_mapping(
    fund_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Auto-detection helper: upload a sample workbook and get back a
    best-guess mapping config (sheets found, columns detected, candidate
    line-item rows) for a Preparer to confirm/adjust — nothing is saved yet.
    """
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            result = infer_mapping(tmp.name)
        except Exception as exc:  # noqa: BLE001 - surface parse errors to the UI
            raise HTTPException(status_code=400, detail=f"Could not read workbook: {exc}")
    return result


@router.post("/funds/{fund_id}/mapping", response_model=schemas.MappingConfigOut, status_code=201)
def save_mapping_config(
    fund_id: int,
    payload: schemas.MappingConfigCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot edit mapping configs")

    latest = (
        db.query(models.MappingConfig)
        .filter(models.MappingConfig.fund_id == fund_id)
        .order_by(models.MappingConfig.version.desc())
        .first()
    )
    version = (latest.version + 1) if latest else 1

    mapping = models.MappingConfig(
        fund_id=fund_id,
        version=version,
        status=payload.status,
        config_json=payload.config_json,
        created_by_id=user.id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    rel_path = storage.mapping_config_path(fund.client_id, fund.id, version)
    storage.storage.save(rel_path, json.dumps(payload.config_json, indent=2).encode())

    log(db, "mapping_config", mapping.id, user.id, "create", f"v{version} status={payload.status}")
    return mapping


@router.get("/funds/{fund_id}/mapping", response_model=list[schemas.MappingConfigOut])
def list_mapping_configs(fund_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)
    return (
        db.query(models.MappingConfig)
        .filter(models.MappingConfig.fund_id == fund_id)
        .order_by(models.MappingConfig.version.desc())
        .all()
    )


@router.get("/funds/{fund_id}/mapping/latest", response_model=schemas.MappingConfigOut)
def get_latest_mapping_config(
    fund_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)
    latest = (
        db.query(models.MappingConfig)
        .filter(models.MappingConfig.fund_id == fund_id)
        .order_by(models.MappingConfig.version.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No mapping config exists for this fund yet")
    return latest
