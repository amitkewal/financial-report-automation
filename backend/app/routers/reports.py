from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models, schemas, storage
from app.audit import log
from app.core.config import settings
from app.core.database import get_db
from app.deps import get_current_user, require_client_access, require_fund_access, require_role
from app.report_engine.pdf_converter import convert_to_pdf
from app.report_engine.template_renderer import build_context, render_report
from app.status_utils import compute_status_from_checks

router = APIRouter(tags=["reports"])


def _get_run_or_404(run_id: int, db: Session) -> models.ReportRun:
    run = db.get(models.ReportRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Report run not found")
    return run


@router.post("/report-runs", response_model=schemas.ReportRunOut, status_code=201)
def create_report_run(
    payload: schemas.ReportRunCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    workbook = db.get(models.UploadedWorkbook, payload.workbook_id)
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found")
    template = db.get(models.Template, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.fund_id != workbook.fund_id:
        raise HTTPException(status_code=400, detail="Template and workbook belong to different funds")

    fund = db.get(models.Fund, workbook.fund_id)
    require_fund_access(fund, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot create report runs")

    run = models.ReportRun(
        fund_id=workbook.fund_id,
        period_id=workbook.period_id,
        workbook_id=workbook.id,
        template_id=template.id,
        status=compute_status_from_checks(db, workbook.id),
        created_by_id=user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    log(db, "report_run", run.id, user.id, "create")
    return run


@router.get("/report-runs", response_model=list[schemas.ReportRunOut])
def list_report_runs(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    client_id: int | None = Query(default=None),
    fund_id: int | None = Query(default=None),
    period_id: int | None = Query(default=None),
    status: models.ReportStatus | None = Query(default=None),
):
    query = db.query(models.ReportRun).join(models.Fund, models.ReportRun.fund_id == models.Fund.id)
    if user.role != models.Role.ADMIN:
        allowed_ids = [a.client_id for a in user.client_access]
        query = query.filter(models.Fund.client_id.in_(allowed_ids)) if allowed_ids else query.filter(False)
    if client_id:
        require_client_access(client_id, db, user)
        query = query.filter(models.Fund.client_id == client_id)
    if fund_id:
        query = query.filter(models.ReportRun.fund_id == fund_id)
    if period_id:
        query = query.filter(models.ReportRun.period_id == period_id)
    if status:
        query = query.filter(models.ReportRun.status == status)
    return query.order_by(models.ReportRun.id.desc()).all()


@router.get("/report-runs/{run_id}", response_model=schemas.ReportRunOut)
def get_report_run(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    return run


@router.get("/report-runs/{run_id}/approval-log", response_model=list[schemas.ApprovalLogOut])
def get_approval_log(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    return (
        db.query(models.ApprovalLog)
        .filter(models.ApprovalLog.report_run_id == run_id)
        .order_by(models.ApprovalLog.id)
        .all()
    )


def _load_render_inputs(run: models.ReportRun, db: Session):
    workbook = db.get(models.UploadedWorkbook, run.workbook_id)
    template = db.get(models.Template, run.template_id)
    fund = db.get(models.Fund, run.fund_id)
    client = db.get(models.Client, fund.client_id)
    period = db.get(models.Period, run.period_id)
    mapping_config = db.get(models.MappingConfig, workbook.mapping_config_id)
    return workbook, template, fund, client, period, mapping_config


@router.post("/report-runs/{run_id}/generate-draft", response_model=schemas.ReportRunOut)
def generate_draft(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    if user.role == models.Role.REVIEWER:
        raise HTTPException(status_code=403, detail="Reviewers cannot generate drafts")

    if run.status not in (models.ReportStatus.VALIDATED, models.ReportStatus.CHANGES_REQUESTED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate a draft from status '{run.status.value}'. Workbook must be VALIDATED first.",
        )

    checks = db.query(models.ValidationCheck).filter(models.ValidationCheck.workbook_id == run.workbook_id).all()
    blocking = [c for c in checks if c.status == models.CheckStatus.FAIL and not c.is_overridden]
    if blocking:
        names = ", ".join(c.name for c in blocking)
        raise HTTPException(
            status_code=400,
            detail=f"Blocked by failing checks without a documented override: {names}",
        )

    workbook, template, fund, client, period, mapping_config = _load_render_inputs(run, db)
    context = build_context(fund, client, period, mapping_config.config_json, workbook.extracted_data_json or {})
    template_abspath = storage.storage.abspath(template.storage_path)
    draft_filename = f"{fund.short_code}_{period.period_label}_DRAFT_v{run.id}.docx"
    draft_rel_path = storage.draft_path(fund.client_id, fund.id, period.id, draft_filename)
    draft_abspath = storage.storage.abspath(draft_rel_path)

    render_report(str(template_abspath), context, str(draft_abspath))

    run.draft_docx_path = draft_rel_path
    run.status = models.ReportStatus.DRAFT_GENERATED
    db.add(models.ApprovalLog(report_run_id=run.id, actor_id=user.id, action="generate_draft"))
    db.commit()
    db.refresh(run)
    return run


@router.post("/report-runs/{run_id}/submit-review", response_model=schemas.ReportRunOut)
def submit_review(
    run_id: int,
    payload: schemas.ApprovalActionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    if run.status != models.ReportStatus.DRAFT_GENERATED:
        raise HTTPException(status_code=400, detail="Only a generated draft can be submitted for review")
    run.status = models.ReportStatus.IN_REVIEW
    db.add(models.ApprovalLog(report_run_id=run.id, actor_id=user.id, action="submit_review", comment=payload.comment))
    db.commit()
    db.refresh(run)
    return run


@router.post("/report-runs/{run_id}/request-changes", response_model=schemas.ReportRunOut)
def request_changes(
    run_id: int,
    payload: schemas.ApprovalActionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.Role.REVIEWER)),
):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    if run.status != models.ReportStatus.IN_REVIEW:
        raise HTTPException(status_code=400, detail="Only a report in review can have changes requested")
    if not payload.comment:
        raise HTTPException(status_code=400, detail="A comment explaining the requested changes is required")
    run.status = models.ReportStatus.CHANGES_REQUESTED
    db.add(
        models.ApprovalLog(report_run_id=run.id, actor_id=user.id, action="request_changes", comment=payload.comment)
    )
    db.commit()
    db.refresh(run)
    return run


@router.post("/report-runs/{run_id}/approve", response_model=schemas.ReportRunOut)
def approve_run(
    run_id: int,
    payload: schemas.ApprovalActionRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.Role.REVIEWER)),
):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    if run.status != models.ReportStatus.IN_REVIEW:
        raise HTTPException(status_code=400, detail="Only a report in review can be approved")
    run.status = models.ReportStatus.APPROVED
    run.approved_by_id = user.id
    db.add(models.ApprovalLog(report_run_id=run.id, actor_id=user.id, action="approve", comment=payload.comment))
    db.commit()
    db.refresh(run)
    return run


@router.post("/report-runs/{run_id}/publish-final", response_model=schemas.ReportRunOut)
def publish_final(
    run_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.Role.REVIEWER)),
):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    if run.status != models.ReportStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only an approved report can be published")

    workbook, template, fund, client, period, mapping_config = _load_render_inputs(run, db)
    context = build_context(fund, client, period, mapping_config.config_json, workbook.extracted_data_json or {})
    template_abspath = storage.storage.abspath(template.storage_path)

    final_filename = f"{fund.short_code}_{period.period_label}_FINAL.docx"
    final_rel_path = storage.final_path(fund.client_id, fund.id, period.id, final_filename)
    final_abspath = storage.storage.abspath(final_rel_path)
    render_report(str(template_abspath), context, str(final_abspath))

    pdf_output_dir = final_abspath.parent
    pdf_abspath = Path(convert_to_pdf(str(final_abspath), str(pdf_output_dir)))
    final_pdf_rel_path = str(pdf_abspath.relative_to(settings.storage_root))

    run.final_docx_path = final_rel_path
    run.final_pdf_path = final_pdf_rel_path
    run.status = models.ReportStatus.FINAL_PUBLISHED
    db.add(models.ApprovalLog(report_run_id=run.id, actor_id=user.id, action="publish_final"))
    db.commit()
    db.refresh(run)
    return run


def _download(rel_path: str | None, filename: str):
    if not rel_path:
        raise HTTPException(status_code=404, detail="File not available yet")
    abspath = storage.storage.abspath(rel_path)
    if not abspath.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path=str(abspath), filename=filename)


@router.get("/report-runs/{run_id}/download/draft")
def download_draft(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    return _download(run.draft_docx_path, Path(run.draft_docx_path or "draft.docx").name)


@router.get("/report-runs/{run_id}/download/final-docx")
def download_final_docx(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    return _download(run.final_docx_path, Path(run.final_docx_path or "final.docx").name)


@router.get("/report-runs/{run_id}/download/final-pdf")
def download_final_pdf(run_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    run = _get_run_or_404(run_id, db)
    fund = db.get(models.Fund, run.fund_id)
    require_fund_access(fund, db, user)
    return _download(run.final_pdf_path, Path(run.final_pdf_path or "final.pdf").name)
