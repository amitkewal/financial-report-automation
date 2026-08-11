# Multi-Client Financial Report Automation Platform

A full-stack platform that ingests a client/fund's financial working Excel
file (NAV pack / leadsheets) plus a fund-specific Word report template,
validates the data with configurable cross-checks, and — after a mandatory
human review/approval step — generates a finalized financial statement
report in both Word (`.docx`) and PDF.

It supports **N clients**, each with **N funds**, where every fund can have
a **completely different internal structure**: which statements it has
(e.g. a debt fund with no Schedule of Investments), where each line item
lives in the workbook, and which cross-check formulas apply. Nothing about
a specific fund type is hardcoded — the mapping + validation + template
engines are all driven entirely by per-fund JSON configuration.

This is a POC, structured to scale to a hosted multi-user deployment (see
[Scaling beyond the POC](#scaling-beyond-the-poc-not-yet-done)).

## How it works

```
Excel workbook (NAV pack)         Fund's own Word template
        |                                    |
        v                                    v
 ┌─────────────────┐   mapping    ┌────────────────────┐
 │  Excel engine    │   config    │   Report engine      │
 │  (inspector,     │─────JSON───>│   (docxtpl render +  │
 │   extractor,     │             │    LibreOffice PDF)  │
 │   validator)     │             └────────────────────┘
 └─────────────────┘                        |
        |                                   v
        v                          Draft -> Review -> Approve -> Final
  PASS/FAIL/WARNING/SKIPPED           (.docx + .pdf, only after
     validation dashboard              an Approver signs off)
```

## Stack

| Layer | Choice |
|---|---|
| Backend | Python / FastAPI, SQLAlchemy, JWT auth (role-based: Admin / Preparer / Reviewer) |
| Excel parsing | openpyxl |
| Word generation | docxtpl (Jinja2-in-docx) |
| PDF conversion | LibreOffice headless (`soffice --convert-to pdf`) |
| Database | SQLite (POC) — swap `FRA_DATABASE_URL` for Postgres in production |
| File storage | Local filesystem via a small `StorageBackend` interface (POC) — swap for S3 in production |
| Frontend | Streamlit (fastest POC per the project brief; see notes below on swapping to React) |

## Setup

### 1. Prerequisites

- Python 3.11+
- LibreOffice with the **Writer** component (`soffice` binary), for PDF conversion:
  ```bash
  sudo apt-get install libreoffice-writer
  ```
  (`libreoffice-core` alone is *not* enough — it can't open any document
  without `libreoffice-writer`.)

### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

On first startup it seeds an admin user (`admin@example.com` /
`ChangeMe123!` by default — override with the `FRA_ADMIN_EMAIL` /
`FRA_ADMIN_PASSWORD` env vars) and creates the SQLite DB and storage
folders under `storage/`. API docs: `http://127.0.0.1:8000/docs`.

### 4. Run the frontend

```bash
cd frontend
streamlit run app.py
```

Open `http://localhost:8501`, log in as admin, and set the "API base URL"
in the sidebar if the backend isn't on the default `http://127.0.0.1:8000`.

### 5. Generate the sample fixtures and run the full demo

```bash
python scripts/generate_sample_data.py   # writes sample_data/{workbooks,templates,mapping_configs}
python scripts/run_sample_e2e.py         # drives the whole pipeline against a running backend
```

This creates one client with two contrasting funds — **Alpha PE Fund I**
(has a Schedule of Investments) and **Beta Debt Fund II** (does not) — and
carries each through upload → validate → draft → review → approve →
publish, producing `sample_data/output/{ALPHA1,BETA2}_FINAL.{docx,pdf}`.

### 6. Run tests

```bash
cd backend
pytest
```

## Onboarding a new client / fund / template

1. **Clients & Funds page** (Admin): create the client, then create the
   fund under it (legal name, short code, fund type, fiscal year end,
   currency). Grant Preparer/Reviewer users access to the client.
2. Upload the fund's **Word report template** (`.docx`, using `{{ }}`
   Jinja placeholders — see [Template placeholder syntax](#template-placeholder-syntax)
   below) on the same page.
3. **Upload & Mapping page**: upload a sample workbook to run
   auto-detection (sheet names, header columns, candidate line-item rows).
   Review the suggestion, then edit/complete the mapping JSON (which
   statements are present for this fund, the row/column for every line
   item, and which cross-checks apply) and click **Confirm mapping**. A
   fund cannot accept a real workbook upload until its mapping is
   confirmed.
4. Add a **period** for the fund (e.g. `2025-Q4`), then upload that
   period's real workbook.
5. **Validation Dashboard**: run cross-checks. All checks must PASS (or be
   explicitly overridden by a Reviewer with a documented justification)
   before a draft can be generated.
6. **Draft Review & Approval**: create the report run, generate the draft,
   submit for review, and — as a Reviewer — approve and publish the final
   `.docx`/`.pdf`.
7. **History & Downloads**: search past runs by client/fund/period/status
   and re-download any prior output.

## Mapping config format

Each fund's mapping is one JSON document (edited via the UI, not hand
written) stored as a versioned `MappingConfig` row. Full shape and
examples are documented in
[`backend/app/excel_engine/mapping_schema.py`](backend/app/excel_engine/mapping_schema.py)
and the two hand-authored sample configs in
[`sample_data/mapping_configs/`](sample_data/mapping_configs/). Summary:

```jsonc
{
  "statements": {
    "balance_sheet": {
      "present": true,
      "sheet_name": "BS Lead",
      "type": "line_items",
      "columns": {"unadjusted": "C", "adjustments": "D", "adjusted": "E", "prior_year": "F"},
      "line_items": [
        {"key": "total_assets", "label": "Total Assets", "row": 10, "is_total": true}
      ]
    },
    "schedule_of_investments": {
      "present": false   // <- simply mark absent statements false; every
                          //    downstream stage (extraction, validation,
                          //    template rendering) skips them cleanly
    }
  },
  "cross_checks": [
    {
      "name": "BS ties to PCAP",
      "left": "balance_sheet.total_partners_capital.adjusted",
      "right": "statement_of_changes_in_partners_capital.ending_capital.total",
      "tolerance": 0.01,
      "applies_if_present": ["balance_sheet", "statement_of_changes_in_partners_capital"]
    }
  ]
}
```

Two statement types beyond `line_items`:
- **`table`** — for repeating rows like a Schedule of Investments
  (`start_row`/`end_row`/`total_row` + a field→column map).
- **`notes`** — for individual disclosure values (numbers, text, or
  booleans) scattered across a Notes tab.

A cross-check whose `applies_if_present` statements aren't present for a
given fund is reported as `SKIPPED`, not `FAIL` — this is how two funds can
have entirely different sets of checks (see the PE fund's 6 checks vs. the
debt fund's 5, with no SOI check defined at all for the debt fund).

## Template placeholder syntax

Templates use [docxtpl](https://docxtpl.readthedocs.io/) (Jinja2 inside
`.docx`):

- `{{ fund_name }}` — simple placeholder
- `{{ balance_sheet.total_assets.adjusted }}` — nested statement / line
  item / column access
- `{{ fmt_currency(balance_sheet.total_assets.adjusted) }}` — standard
  audited-FS formatting (thousands separators, negatives in parentheses)
- `{% if statements_present.schedule_of_investments %} ... {% endif %}` —
  conditionally omit an entire section for funds that don't have it
- `{%tr for row in schedule_of_investments_rows %}` / `{%tr endfor %}` on
  their own table rows, surrounding a data row — repeats that row once per
  investment (docxtpl's table-row tag; see the two sample templates in
  `sample_data/templates/` for a working example)

## Approval workflow

```
Uploaded -> Validated -> Draft Generated -> In Review -> Approved -> Final Published
                \-> Validation Failed          \-> Changes Requested (back to Preparer)
```

- Draft generation is blocked while any check is `FAIL` and not overridden.
- Only a Reviewer/Admin can approve or publish the final report.
- Every transition is written to `ApprovalLog` (who, when, what, optional
  comment) and mirrored into `AuditLog` for uploads, mapping changes, and
  overrides — the full audit trail requested in the spec.

## Data model

`User` (role: admin/preparer/reviewer) · `Client` · `UserClientAccess`
(per-client permissions) · `Fund` · `MappingConfig` (versioned) ·
`Template` (versioned) · `Period` · `UploadedWorkbook` (stores extracted
data as JSON) · `ValidationCheck` · `ReportRun` (the pipeline/status
entity) · `ApprovalLog` · `AuditLog`. See
[`backend/app/models.py`](backend/app/models.py).

## Project layout

```
backend/app/
  core/            config, db session, JWT/password hashing
  excel_engine/    mapping schema, auto-detect inspector, extractor, validator
  report_engine/   financial formatting, docxtpl renderer, PDF conversion
  routers/         auth, clients, funds, templates, mapping, uploads, validation, reports
  models.py        SQLAlchemy models
  schemas.py       Pydantic request/response models
  storage.py       local-filesystem storage backend (Client > Fund > Period layout)
frontend/          Streamlit UI (one file per workflow screen, under pages/)
sample_data/       generated sample workbooks, templates, and mapping configs
scripts/           generate_sample_data.py, run_sample_e2e.py
backend/tests/     pytest suite for the excel/report engines
```

## Scaling beyond the POC (not yet done)

- **Frontend**: swap Streamlit for a React + TypeScript SPA once
  multi-user auth and richer role-based workflows are needed — the
  backend is already a pure REST API with no server-rendered HTML, so this
  doesn't touch business logic.
- **Database**: point `FRA_DATABASE_URL` at Postgres.
- **Storage**: implement an `S3Storage` class against the same
  `StorageBackend` interface used by `LocalStorage` (`backend/app/storage.py`).
- **Auth**: JWT is already in place; add an SSO/OIDC provider in front of
  `/auth/login`.
- **Scale-out**: PDF conversion shells out to `soffice` per report with an
  isolated user profile per call, so it's safe to run several in parallel
  or move it to a worker queue for a hosted deployment.
