from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas, storage
from app.audit import log
from app.core.database import get_db
from app.deps import get_current_user, require_fund_access

router = APIRouter(tags=["templates"])


@router.post("/funds/{fund_id}/templates", response_model=schemas.TemplateOut, status_code=201)
async def upload_template(
    fund_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Template must be a .docx file")

    latest = (
        db.query(models.Template)
        .filter(models.Template.fund_id == fund_id)
        .order_by(models.Template.version.desc())
        .first()
    )
    version = (latest.version + 1) if latest else 1
    if latest:
        latest.is_active = False

    content = await file.read()
    rel_path = storage.template_path(fund.client_id, fund.id, file.filename, version)
    storage.storage.save(rel_path, content)

    template = models.Template(
        fund_id=fund_id,
        version=version,
        filename=file.filename,
        storage_path=rel_path,
        is_active=True,
        uploaded_by_id=user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    log(db, "template", template.id, user.id, "upload", file.filename)
    return template


@router.get("/funds/{fund_id}/templates", response_model=list[schemas.TemplateOut])
def list_templates(fund_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    require_fund_access(fund, db, user)
    return (
        db.query(models.Template)
        .filter(models.Template.fund_id == fund_id)
        .order_by(models.Template.version.desc())
        .all()
    )
