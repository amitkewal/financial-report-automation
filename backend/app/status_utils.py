from sqlalchemy.orm import Session

from app import models


def compute_status_from_checks(db: Session, workbook_id: int) -> models.ReportStatus:
    """VALIDATED if every check for this workbook is PASS/SKIPPED, VALIDATION_FAILED
    if any FAIL, or UPLOADED if validation hasn't run yet."""
    checks = db.query(models.ValidationCheck).filter(models.ValidationCheck.workbook_id == workbook_id).all()
    if not checks:
        return models.ReportStatus.UPLOADED
    all_ok = all(c.status in (models.CheckStatus.PASS, models.CheckStatus.SKIPPED) for c in checks)
    return models.ReportStatus.VALIDATED if all_ok else models.ReportStatus.VALIDATION_FAILED
