# Architecture & Product Decisions

A running log of the significant decisions made building this platform — what we chose, why,
and what we gave up. Git history shows *what* changed; this file exists to preserve *why*,
so future work (including future Claude Code sessions) doesn't have to re-derive it or
accidentally re-litigate a decision that was already made deliberately.

**How to use this file**: append a new entry whenever a decision would be expensive to get
wrong or non-obvious to a newcomer — new architecture, a rejected alternative, a scaling
tradeoff. Skip routine implementation choices; those belong in code/commit messages. Keep
entries in chronological order (newest at the bottom) and give each a date and status.

Status legend: `Accepted` (built and in use) · `Proposed` (discussed, not yet built) ·
`Superseded` (replaced by a later decision — leave the old entry, link to the new one).

---

## 2026-08-11 — Mapping is data, not code (per-fund JSON config drives everything)

**Status**: Accepted

**Context**: The platform must support N clients × N funds, where every fund can have a
completely different internal workbook structure (which statements exist, where each line
item lives, which cross-checks apply).

**Decision**: Nothing fund-specific is hardcoded anywhere in the engine. Each fund has a
versioned `MappingConfig` (JSON) describing its statements, line-item row/column locations,
and cross-check formulas. The Excel engine (`inspector` → `extractor` → `validator`) and the
report engine (`template_renderer`) are all generic and driven entirely by this config.

**Consequences**: Onboarding a new fund is a data operation (create a mapping), not a code
change. The cost is that mapping quality is only as good as whoever fills it in — see the
2026-08-12 entries below on how we're addressing that as fund count grows.

## 2026-08-11 — Absent statements are `present: false`, not omitted

**Status**: Accepted

**Context**: A debt fund has no Schedule of Investments; other fund types might lack other
statements. Every stage (extraction, validation, template rendering) needs to handle this
uniformly.

**Decision**: A statement a fund doesn't have is explicitly marked `"present": false` in its
mapping config, rather than left out of the JSON. Every downstream consumer checks this flag
and skips cleanly.

**Consequences**: One explicit, testable state instead of three code paths (present / absent /
key-missing) guessing at each other's intent.

## 2026-08-11 — Cross-checks report SKIPPED, not FAIL, when inapplicable

**Status**: Accepted

**Context**: If a fund doesn't have a Schedule of Investments, it also doesn't have an
SOI-ties-to-Balance-Sheet check. That check must not show up as a false failure.

**Decision**: Each `cross_check` declares `applies_if_present`; if any referenced statement is
absent for this fund, the validator reports `SKIPPED` for that check instead of running it.

**Consequences**: The PE fund runs 6 checks, the debt fund runs 5, with no SOI check defined
for it at all — both dashboards read as "all clear" without any fund-type-specific logic in
the validator.

## 2026-08-11 — Mandatory human approval gate before any final report ships

**Status**: Accepted

**Context**: This produces audited-style financial statements; a wrong number in an unreviewed
report is a real-world liability, not a UI bug.

**Decision**: Every report run passes through
`Uploaded → Validated → Draft Generated → In Review → Approved → Final Published`. Draft
generation is blocked while any validation check is `FAIL` and not explicitly overridden
(Reviewer-only, requires a documented comment). Only a Reviewer or Admin can approve or
publish. Every transition is written to `ApprovalLog`; uploads, mapping changes, and overrides
are also mirrored into `AuditLog`.

**Consequences**: No path exists from "workbook uploaded" to "final PDF" without a human
sign-off. Slower than full automation by design — this was treated as non-negotiable for a
financial-reporting product, not a POC shortcut to remove later.

## 2026-08-11 — Mapping configs and templates are versioned, never mutated in place

**Status**: Accepted

**Context**: A fund's workbook layout or report template can change between periods. Past
report runs must remain reproducible against the config that was actually confirmed at the
time.

**Decision**: `MappingConfig` and `Template` both carry a `version` and are append-only —
editing creates a new version rather than overwriting the old one. `UploadedWorkbook` and
`ReportRun` reference the specific config/template version used.

**Consequences**: Full history is reconstructable. Slight extra storage cost, judged worth it
for an audit-sensitive domain.

## 2026-08-11 — Storage is an interface, not a filesystem assumption

**Status**: Accepted

**Context**: POC needs to run locally with zero infra, but must move to hosted/multi-user
without a rewrite.

**Decision**: `StorageBackend` ABC (`save` / `read` / `abspath`) with `LocalStorage` as the only
implementation today, laid out as `clients/{id}/funds/{id}/periods/{id}/...`. No caller touches
the filesystem directly.

**Consequences**: Moving to S3 means writing one `S3Storage` class against the same 3-method
interface — no changes anywhere else in the codebase. Same reasoning applied to the database
(SQLite now, swap `FRA_DATABASE_URL` for Postgres later — no ORM-level lock-in).

## 2026-08-11 — Streamlit frontend, pure REST client, no business logic in the UI

**Status**: Accepted

**Context**: Fastest path to a working POC per the project brief, but multi-user auth and
richer role-based workflows will eventually need a real SPA.

**Decision**: Streamlit UI, one file per workflow screen (`pages/1_...` through `5_...`),
talking to the FastAPI backend purely over REST via `api_client.py`. Zero business logic lives
in the frontend.

**Consequences**: The backend is already a standalone API server; swapping Streamlit for a
React + TypeScript SPA later touches only the frontend, never the engines or routers.

## 2026-08-11 — docxtpl + headless LibreOffice for report generation

**Status**: Accepted

**Context**: Need Word-native output (clients expect `.docx` they can edit) plus a PDF, from a
template a fund owner controls.

**Decision**: `docxtpl` (Jinja2 templating inside `.docx`) for the draft/final Word document;
`soffice --convert-to pdf` (LibreOffice headless) for the PDF, with an isolated user profile
per invocation so conversions are safe to run in parallel or move to a worker queue later.

**Consequences**: Fund owners edit templates in Word, using ordinary `{{ }}` placeholders and
`{% if %}` / `{%tr for %}` tags — no code changes to add a new fund's report layout. Adds a
LibreOffice binary dependency on the host.

## 2026-08-11 — Auto-detection is a suggestion, never auto-applied

**Status**: Accepted

**Context**: The first time a new fund's workbook is uploaded, someone has to figure out which
sheet is the balance sheet, which column is "Adjusted," etc.

**Decision**: `inspector.infer_mapping()` scans the workbook (sheet-name synonyms, header
keyword detection, candidate label rows) and returns a `suggested_config` — never a confirmed
one. A human (Preparer) always reviews and edits it before clicking **Confirm mapping**; a fund
cannot accept a real workbook upload until then.

**Consequences**: This is the seam the two proposals below plug into — replacing *how* the
suggestion is generated doesn't require touching the trust boundary around it.

---

## 2026-08-12 — Numbers in the report must always come from deterministic extraction, never from a model

**Status**: Accepted (design constraint for all future AI-assisted work)

**Context**: Discussed adding an LLM to help with fund onboarding (see below). Needed to draw a
hard line before building anything AI-assisted in a financial-reporting product.

**Decision**: Any AI/LLM component in this system may only ever *propose a mapping* (which
cell holds `total_assets`) for a human to confirm. It must never generate, estimate, or touch
the numeric values that end up in a report — those are always read verbatim by `extractor.py`
from the exact cell a *confirmed* mapping points to, and substituted as-is by the `docxtpl`
renderer.

**Consequences**: Report accuracy is bounded by mapping accuracy, not by model reliability —
the LLM (if added) sits entirely outside the live extraction/render path, in the same
suggestion-only seam `inspector.py` already occupies.

## 2026-08-12 — Proposed: verify the line-item label at every extraction, not just at initial mapping

**Status**: Proposed — not yet implemented

**Context**: A confirmed mapping stores a fixed row/column (e.g. `total_assets` → `BS Lead!E10`).
If a fund's workbook layout shifts between periods (a row inserted or deleted upstream), the
extractor keeps reading row 10 — now silently the *wrong* line item — with no error. This is a
bigger real-world threat to report accuracy than how the initial mapping was produced, and
today's cross-checks only catch it if the mismapped line item happens to participate in a
tie-out formula.

**Decision (proposed)**: Every mapped line item already carries a `label` field
(e.g. `"Total assets"`) that is stored but currently unused at extraction time. Add a check in
`extractor.py`: before trusting the value at the mapped cell, read the label cell in the same
row and fuzzy-match it against the stored `label`. On mismatch, hard-fail that line item
(blocking draft generation) with a message identifying the expected vs. actual label and cell,
rather than silently extracting a wrong number.

**Consequences if built**: Catches workbook layout drift automatically, every period, for
every fund — independent of whether the mapping was originally produced by hand, by regex
heuristics, or by an LLM.

## 2026-08-12 — Proposed: LLM-assisted mapping suggestions for new-fund onboarding

**Status**: Proposed — not yet implemented

**Context**: `inspector.py`'s current auto-detection is keyword/regex heuristics (sheet-name
synonym lists, header-keyword scanning, "most-text column" guessing). It works well on
workbooks shaped like the two sample funds, but degrades on genuinely different NAV pack
layouts — and as client/fund count grows, every new fund with an unconventional layout pushes
more manual row-by-row mapping work onto the Preparer.

**Decision (proposed)**: Feed a new fund's sheet grid plus the canonical statement/line-item
schema to an LLM and have it propose the full `line_items` array (key, label, row) and
candidate `cross_checks`, replacing/augmenting `infer_mapping`'s heuristics. It plugs into the
exact same suggestion-only seam that exists today — output is still a `suggested_config` a
Preparer must review and confirm before it's usable. See the 2026-08-12 "numbers must come from
deterministic extraction" entry above for the hard boundary this must respect.

**Consequences if built**: Less manual mapping effort per new fund, at the cost of added
latency/API cost on first-time onboarding only (never on recurring period uploads, which stay
fully deterministic). Should ship only after or alongside the label-verification check above,
since a better initial guess doesn't protect against layout drift in later periods.
