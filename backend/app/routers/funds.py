from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log
from app.core.database import get_db
from app.deps import get_current_user, require_client_access, require_fund_access

router = APIRouter(tags=["funds"])


def _get_fund_or_404(fund_id: int, db: Session) -> models.Fund:
    fund = db.get(models.Fund, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    return fund


@router.post("/clients/{client_id}/funds", response_model=schemas.FundOut, status_code=201)
def create_fund(
    client_id: int,
    payload: schemas.FundCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    require_client_access(client_id, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot create funds")
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    fund = models.Fund(client_id=client_id, **payload.model_dump())
    db.add(fund)
    db.commit()
    db.refresh(fund)
    log(db, "fund", fund.id, user.id, "create", fund.legal_name)
    return fund


@router.get("/clients/{client_id}/funds", response_model=list[schemas.FundOut])
def list_funds(client_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    require_client_access(client_id, db, user)
    return db.query(models.Fund).filter(models.Fund.client_id == client_id).order_by(models.Fund.legal_name).all()


@router.get("/funds/{fund_id}", response_model=schemas.FundOut)
def get_fund(fund_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    fund = _get_fund_or_404(fund_id, db)
    require_fund_access(fund, db, user)
    return fund


@router.put("/funds/{fund_id}", response_model=schemas.FundOut)
def update_fund(
    fund_id: int,
    payload: schemas.FundUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fund = _get_fund_or_404(fund_id, db)
    require_fund_access(fund, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot edit funds")
    for key, value in payload.model_dump().items():
        setattr(fund, key, value)
    db.commit()
    db.refresh(fund)
    log(db, "fund", fund.id, user.id, "update")
    return fund


@router.delete("/funds/{fund_id}", status_code=204)
def delete_fund(fund_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    fund = _get_fund_or_404(fund_id, db)
    require_fund_access(fund, db, user)
    if user.role not in (models.Role.ADMIN,):
        raise HTTPException(status_code=403, detail="Only admins can delete funds")
    db.delete(fund)
    db.commit()
    log(db, "fund", fund_id, user.id, "delete")


# ---------- Periods ----------

@router.post("/funds/{fund_id}/periods", response_model=schemas.PeriodOut, status_code=201)
def create_period(
    fund_id: int,
    payload: schemas.PeriodCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fund = _get_fund_or_404(fund_id, db)
    require_fund_access(fund, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot create periods")
    existing = (
        db.query(models.Period)
        .filter(models.Period.fund_id == fund_id, models.Period.period_label == payload.period_label)
        .first()
    )
    if existing:
        return existing
    period = models.Period(fund_id=fund_id, **payload.model_dump())
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.get("/funds/{fund_id}/periods", response_model=list[schemas.PeriodOut])
def list_periods(fund_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    fund = _get_fund_or_404(fund_id, db)
    require_fund_access(fund, db, user)
    return db.query(models.Period).filter(models.Period.fund_id == fund_id).order_by(models.Period.id.desc()).all()
