# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See [DECISIONS.md](DECISIONS.md) for the log of major architecture/product decisions and why
they were made — check it before proposing a significant change, and append to it after making
one.

## What this is

A full-stack POC that ingests a client/fund's financial working Excel file (NAV pack) plus a
fund-specific Word template, validates the data with configurable cross-checks, and — after a
mandatory human review/approval step — generates a finalized financial statement report in
Word (`.docx`) and PDF. It supports N clients × N funds where every fund can have a completely
different internal structure (which statements exist, where line items live, which cross-checks
apply) — **nothing fund-specific is hardcoded**; it's all driven by per-fund JSON mapping config.

Pipeline: `Excel workbook + mapping JSON → Excel engine (inspect/extract/validate) → Report engine
(docxtpl render + LibreOffice→PDF) → Draft → Review → Approve → Final`.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# PDF conversion also requires the LibreOffice Writer component (`soffice` binary) on PATH.

# Run backend (from backend/)
cd backend && uvicorn app.main:app --reload --port 8000   # API docs at /docs
# Seeds an admin user on first startup: admin@example.com / ChangeMe123!
# (override via FRA_ADMIN_EMAIL / FRA_ADMIN_PASSWORD)

# Run frontend (from frontend/, backend must be running)
cd frontend && streamlit run app.py   # http://localhost:8501

# Tests (from backend/)
cd backend && pytest
pytest tests/test_excel_engine.py::test_pe_fund_all_checks_pass   # single test
pytest -k "validation"                                            # by keyword

# Full sample E2E (needs backend running)
python scripts/generate_sample_data.py   # (re)writes sample_data/{workbooks,templates,mapping_configs}
python scripts/run_sample_e2e.py         # drives upload -> validate -> draft -> review -> approve -> publish
```

There is no lint/format/build tooling configured (no ruff/black/eslint config present) — match
existing style when editing.

## Architecture

**`backend/app/`** — FastAPI backend, the only place with business logic.
- `excel_engine/` — `inspector.py` (auto-detects sheets/headers/candidate rows from an unfamiliar
  workbook to seed a mapping suggestion), `extractor.py` (pulls values out of a workbook per a
  confirmed `MappingConfig`), `validator.py` (re-runs `cross_checks` against extracted data),
  `mapping_schema.py` (the mapping JSON shape + `resolve_path`, the dotted-path / `sum:` prefix
  resolver used by both validator and template context).
- `report_engine/` — `template_renderer.py` (docxtpl/Jinja2 render of a `.docx` template against
  extracted data), `formatting.py` (audited-FS number formatting, e.g. `fmt_currency`),
  `pdf_converter.py` (shells out to `soffice --convert-to pdf`, one isolated user profile per call
  so parallel conversions are safe).
- `routers/` — one file per resource (`auth`, `clients`, `funds`, `templates`, `mapping`,
  `uploads`, `validation`, `reports`), all registered in `main.py`.
- `models.py` — SQLAlchemy models: `User`(role) → `UserClientAccess` → `Client` → `Fund` →
  {`MappingConfig` (versioned), `Template` (versioned), `Period` → `UploadedWorkbook` (extracted
  data stored as JSON) → `ValidationCheck`} → `ReportRun` (the pipeline/status entity) →
  `ApprovalLog`; plus a global `AuditLog`.
- `deps.py` — auth dependencies: `get_current_user`, `require_role(*roles)`,
  `require_client_access`/`require_fund_access` (per-client ACL via `UserClientAccess`; `ADMIN`
  bypasses all checks).
- `storage.py` — `StorageBackend` ABC with a `LocalStorage` impl (POC); path layout is
  `clients/{id}/funds/{id}/{templates,periods/{id}/{workbooks,drafts,final},mapping_configs}`. To
  add S3, implement the same 3-method interface (`save`/`read`/`abspath`) — no caller changes.
- `core/config.py` — `Settings` (env-prefixed `FRA_*`, e.g. `FRA_DATABASE_URL`,
  `FRA_ADMIN_EMAIL/PASSWORD`, `FRA_ADMIN_PASSWORD`), SQLite by default.

**`frontend/`** — Streamlit POC UI, one file per workflow screen under `pages/`, numbered in
pipeline order (Clients & Funds → Upload & Mapping → Validation Dashboard → Draft Review &
Approval → History & Downloads). Pure REST client (`api_client.py`) against the FastAPI backend —
no business logic lives here. The brief flags this as the piece most likely to be swapped for a
React SPA later.

**`sample_data/`** — generated fixtures: two contrasting funds, **Alpha PE Fund I** (has a
Schedule of Investments) and **Beta Debt Fund II** (does not) — used to exercise the "nothing
fund-specific is hardcoded" claim end to end.

### Key design points worth knowing before editing

- **Mapping config is the source of truth per fund.** `config_json` on `MappingConfig` declares
  `statements` (each `line_items` / `table` / `notes` type, with `present: true/false`) and
  `cross_checks` (each with `left`/`right` dotted paths, `tolerance`, `applies_if_present`). A
  fund cannot accept a real workbook upload until its mapping is `confirmed`. See
  `backend/app/excel_engine/mapping_schema.py` and the two sample configs in
  `sample_data/mapping_configs/` for the full shape.
- **Absent statements are `present: false`, not omitted** — every downstream stage (extraction,
  validation, template rendering) skips them cleanly rather than erroring.
- **Cross-checks whose `applies_if_present` statements aren't present report `SKIPPED`, not
  `FAIL`** — this is how two funds can have entirely different check sets (PE fund: 6 checks,
  debt fund: 5, no SOI check defined at all) without false failures.
- **Approval workflow is a hard gate:** `Uploaded → Validated → Draft Generated → In Review →
  Approved → Final Published` (or `Validation Failed` / `Changes Requested` off-ramps). Draft
  generation is blocked while any check is `FAIL` and not explicitly overridden by a Reviewer
  (with a documented justification). Only Reviewer/Admin can approve or publish. Every transition
  writes to `ApprovalLog`; uploads/mapping changes/overrides also mirror into `AuditLog`.
- **Templates use docxtpl** (Jinja2 inside `.docx`): `{{ balance_sheet.total_assets.adjusted }}`
  for nested access, `{{ fmt_currency(...) }}` for audited-FS formatting, `{% if
  statements_present.x %}` to conditionally omit whole sections, and the `{%tr for ... %}` /
  `{%tr endfor %}` table-row tags to repeat a row per investment (see
  `sample_data/templates/*.docx` for working examples).
