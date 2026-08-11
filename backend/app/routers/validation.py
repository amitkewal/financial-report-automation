from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import log
from app.core.database import get_db
from app.deps import get_current_user, require_fund_access, require_role
from app.excel_engine.validator import run_validation

router = APIRouter(tags=["validation"])


@router.post("/workbooks/{workbook_id}/validate", response_model=list[schemas.ValidationCheckOut])
def validate_workbook(
    workbook_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    workbook = db.get(models.UploadedWorkbook, workbook_id)
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found")
    fund = db.get(models.Fund, workbook.fund_id)
    require_fund_access(fund, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot trigger validation runs")

    mapping_config = db.get(models.MappingConfig, workbook.mapping_config_id)
    if not mapping_config:
        raise HTTPException(status_code=400, detail="Workbook has no associated mapping config")

    results = run_validation(workbook.extracted_data_json or {}, mapping_config.config_json)

    db.query(models.ValidationCheck).filter(models.ValidationCheck.workbook_id == workbook_id).delete()
    checks = []
    for r in results:
        check = models.ValidationCheck(
            workbook_id=workbook_id,
            name=r["name"],
            statement=r["statement"],
            status=r["status"],
            expected_value=r["expected_value"],
            actual_value=r["actual_value"],
            difference=r["difference"],
            message=r["message"],
        )
        db.add(check)
        checks.append(check)
    db.commit()
    for c in checks:
        db.refresh(c)

    # Roll the status forward on any report runs tied to this workbook.
    all_ok = all(c.status in (models.CheckStatus.PASS, models.CheckStatus.SKIPPED) for c in checks)
    new_status = models.ReportStatus.VALIDATED if all_ok else models.ReportStatus.VALIDATION_FAILED
    for run in db.query(models.ReportRun).filter(models.ReportRun.workbook_id == workbook_id).all():
        run.status = new_status
    db.commit()

    log(db, "workbook", workbook_id, user.id, "validate", f"{len(checks)} checks, all_ok={all_ok}")
    return checks


@router.get("/workbooks/{workbook_id}/validation", response_model=list[schemas.ValidationCheckOut])
def get_validation_results(
    workbook_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    workbook = db.get(models.UploadedWorkbook, workbook_id)
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found")
    fund = db.get(models.Fund, workbook.fund_id)
    require_fund_access(fund, db, user)
    return (
        db.query(models.ValidationCheck)
        .filter(models.ValidationCheck.workbook_id == workbook_id)
        .order_by(models.ValidationCheck.id)
        .all()
    )


@router.post("/validation-checks/{check_id}/override", response_model=schemas.ValidationCheckOut)
def override_check(
    check_id: int,
    payload: schemas.OverrideCheckRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.Role.REVIEWER)),
):
    check = db.get(models.ValidationCheck, check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Validation check not found")
    workbook = db.get(models.UploadedWorkbook, check.workbook_id)
    fund = db.get(models.Fund, workbook.fund_id)
    require_fund_access(fund, db, user)

    check.is_overridden = True
    check.override_comment = payload.comment
    check.override_by_id = user.id
    db.commit()
    db.refresh(check)
    log(db, "validation_check", check.id, user.id, "override", payload.comment)
    return check
