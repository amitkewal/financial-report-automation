"""Generates a THIRD sample fund fixture grounded in real, publicly reported
figures for Investcorp Credit Management BDC, Inc. (NASDAQ: ICMB), a
real, currently SEC-registered business development company.

WHY THIS EXISTS
----------------
The other two sample funds (Alpha PE Fund I / Beta Debt Fund II) are fully
synthetic. This one is anchored to a real fund's actual reported FY2025
figures (sourced via web search, since this sandbox's network policy blocks
direct fetches to sec.gov and mirror sites) to prove the platform against
numbers, holdings, and a capital structure that came from an actual filing
rather than something we made up end to end.

DATA PROVENANCE - READ BEFORE TRUSTING ANY NUMBER BELOW
----------------------------------------------------------
Every figure below is tagged REAL or EST in an inline comment.

  REAL = sourced from ICMB's actual FY2025 public disclosures (10-K /
         8-K / earnings press releases), found via web search snippets.
         This sandbox could not fetch the full financial statements
         directly (sec.gov and mirrors are blocked by network policy), so
         these are the figures that surfaced in search results, not a
         verified read of the complete filing.
  EST  = a reasonable estimate used to complete this test fixture (e.g.
         splitting a real aggregate into line items, or filling in a
         prior-year comparative) so the workbook is internally consistent
         and exercises every part of the pipeline. These are NOT ICMB's
         officially reported figures.

This fixture is for exercising this codebase only. It is not, and must
not be represented as, ICMB's actual financial statements.

Real anchors used (see script comments for exact placement):
  - Total assets: $188.8M | Investments at fair value: $172.7M
  - Net assets: $61.3M (NAV/share $4.25, prior year $5.39)
  - Net investment income (after tax): $1.905M
  - Net decrease in net assets from operations: $8.848M
  - Capital One credit facility: $58.9M drawn of a $100M facility,
    SOFR + 2.50%, maturing 2029
  - Portfolio: 37 companies / 18 industries / 67 positions; 81% first-lien
    senior secured debt; ~9.1% weighted-average coupon; ~70% sponsor-backed
  - Top holdings (named in public disclosures): Bioplan, WorkGenius,
    Klein Hersh, Xenon Arc, ArborWorks, Crafty Apes, Argano, LaserAway;
    combined top-10 fair value ~$85.3M

Run: python scripts/generate_real_fund_data.py
"""

import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Font
from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "sample_data"
WORKBOOKS_DIR = SAMPLE_DIR / "workbooks"
TEMPLATES_DIR = SAMPLE_DIR / "templates"
MAPPING_DIR = SAMPLE_DIR / "mapping_configs"

NUM_FMT = "#,##0;(#,##0)"
PROVENANCE_NOTE = (
    "TEST FIXTURE - NOT AN OFFICIAL FILING. Figures grounded in Investcorp Credit "
    "Management BDC, Inc. (NASDAQ: ICMB) FY2025 public disclosures where sourced via "
    "web search; remaining line-item detail is estimated to complete this fixture. "
    "See scripts/generate_real_fund_data.py for the REAL vs EST provenance of every figure."
)


def set_cell(ws, ref, value, bold=False, number=False, italic=False):
    cell = ws[ref]
    cell.value = value
    if bold or italic:
        cell.font = Font(bold=bold, italic=italic)
    if number:
        cell.number_format = NUM_FMT
    return cell


def build_workbook() -> Path:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # --- Contacts and links ---------------------------------------------
    ws = wb.create_sheet("Contacts and links")
    set_cell(ws, "A1", "Client / Fund Metadata", bold=True)
    set_cell(ws, "A3", "Fund Legal Name", bold=True)
    set_cell(ws, "B3", "Investcorp Credit Management BDC, Inc.")
    set_cell(ws, "A4", "Fund Type", bold=True)
    set_cell(ws, "B4", "Business Development Company (publicly traded, NASDAQ: ICMB)")
    set_cell(ws, "A5", "Data provenance", bold=True)
    set_cell(ws, "B5", PROVENANCE_NOTE)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 90

    # --- Process -----------------------------------------------------------
    ws = wb.create_sheet("Process")
    set_cell(ws, "A1", "Preparation Checklist (informational only, not extracted)", bold=True)
    set_cell(ws, "A3", "1. Reconcile to publicly filed 10-K where sourced")
    set_cell(ws, "A4", "2. Flag estimated line items for follow-up with fund accounting")
    set_cell(ws, "A5", "3. Run cross-checks")
    ws.column_dimensions["A"].width = 60

    # --- BS Lead: Consolidated Statement of Assets and Liabilities --------
    # Real BDCs report a single "current period" / "prior period" column pair,
    # not Unadjusted/Adjustments/Adjusted - a genuinely different column
    # layout from the other two sample funds, proving the mapping config's
    # `columns` field is truly per-fund.
    ws = wb.create_sheet("BS Lead")
    set_cell(ws, "B1", "Investcorp Credit Management BDC, Inc. - Consolidated Statement of Assets and Liabilities", bold=True)
    set_cell(ws, "B2", PROVENANCE_NOTE, italic=True)
    set_cell(ws, "B4", "Line Item", bold=True)
    set_cell(ws, "C4", "12/31/2025", bold=True)
    set_cell(ws, "D4", "12/31/2024", bold=True)

    def bs_row(r, label, cur, pri, bold=False):
        set_cell(ws, f"B{r}", label, bold=bold)
        set_cell(ws, f"C{r}", cur, number=True, bold=bold)
        set_cell(ws, f"D{r}", pri, number=True, bold=bold)

    set_cell(ws, "B6", "ASSETS", bold=True)
    bs_row(7, "Investments, at fair value", 172_700_000, 194_000_000)          # REAL (current) / EST (prior)
    bs_row(8, "Cash and cash equivalents", 9_500_000, 10_647_000)              # EST (current split) / EST (prior, ties to SOCF)
    bs_row(9, "Interest receivable", 5_000_000, 4_500_000)                     # EST
    bs_row(10, "Other assets", 1_600_000, 1_353_000)                          # EST
    bs_row(11, "Total assets", 188_800_000, 210_500_000, bold=True)            # REAL (current) / EST (prior)

    set_cell(ws, "B13", "LIABILITIES", bold=True)
    bs_row(14, "Credit facility payable", 58_900_000, 62_000_000)              # REAL (current) / EST (prior)
    bs_row(15, "Accrued expenses and other liabilities", 4_600_000, 4_200_000)  # EST
    bs_row(16, "Other borrowings (unverified breakdown - see provenance note)", 64_000_000, 66_700_000)  # EST plug
    bs_row(17, "Total liabilities", 127_500_000, 132_900_000, bold=True)       # REAL-derived (current) / EST (prior)

    set_cell(ws, "B19", "NET ASSETS", bold=True)
    bs_row(20, "Net assets", 61_300_000, 77_600_000, bold=True)                # REAL (current) / EST (prior)
    bs_row(21, "Total liabilities and net assets", 188_800_000, 210_500_000, bold=True)  # REAL / EST

    ws.column_dimensions["B"].width = 55
    for col in "CD":
        ws.column_dimensions[col].width = 16

    # --- IS Lead: Consolidated Statement of Operations ---------------------
    ws = wb.create_sheet("IS Lead")
    set_cell(ws, "B1", "Investcorp Credit Management BDC, Inc. - Consolidated Statement of Operations (Year Ended 12/31/2025)", bold=True)
    set_cell(ws, "B2", PROVENANCE_NOTE, italic=True)
    set_cell(ws, "B4", "Line Item", bold=True)
    set_cell(ws, "C4", "FY2025", bold=True)
    set_cell(ws, "D4", "FY2024", bold=True)

    def is_row(r, label, cur, pri, bold=False):
        set_cell(ws, f"B{r}", label, bold=bold)
        set_cell(ws, f"C{r}", cur, number=True, bold=bold)
        set_cell(ws, f"D{r}", pri, number=True, bold=bold)

    set_cell(ws, "B6", "INVESTMENT INCOME", bold=True)
    is_row(7, "Interest income", 15_800_000, 17_100_000)                       # EST
    is_row(8, "Fee income and other", 3_700_000, 3_400_000)                    # EST
    is_row(9, "Total investment income", 19_500_000, 20_500_000, bold=True)    # EST (backed into with real NII below)

    set_cell(ws, "B11", "EXPENSES", bold=True)
    is_row(12, "Management fees", 3_200_000, 3_500_000)                        # EST
    is_row(13, "Interest and financing expenses", 9_600_000, 9_100_000)        # EST
    is_row(14, "General and administrative expenses", 4_347_000, 4_050_000)    # EST plug (current ties NII before tax)
    is_row(15, "Total expenses", 17_147_000, 16_650_000, bold=True)            # EST-derived (current) / EST (prior)

    is_row(17, "Net investment income before taxes", 2_353_000, 3_850_000, bold=True)  # REAL (current) / EST (prior)
    is_row(18, "Income tax expense", 448_000, 390_000)                         # EST-derived (current)
    is_row(19, "Net investment income", 1_905_000, 3_460_000, bold=True)       # REAL (current) / EST (prior)

    is_row(21, "Net realized gain (loss) on investments", -4_200_000, 1_100_000)      # EST
    is_row(22, "Net change in unrealized gain (loss) on investments", -6_553_000, -2_900_000)  # EST-derived (current)
    is_row(23, "Net realized and unrealized gain (loss)", -10_753_000, -1_800_000, bold=True)  # EST-derived (current)

    is_row(25, "Net increase (decrease) in net assets resulting from operations", -8_848_000, 1_660_000, bold=True)  # REAL (current) / EST (prior)

    ws.column_dimensions["B"].width = 60
    for col in "CD":
        ws.column_dimensions[col].width = 16

    # --- SOI Lead: Schedule of Investments ----------------------------------
    # Real named top holdings (public disclosure) with estimated individual
    # fair values (exact per-company marks aren't in the public snippets we
    # could retrieve), plus two aggregate rows so the REAL reported totals
    # (top-10 ~$85.3M, portfolio total $172.7M) tie exactly - the same
    # "top holdings + remainder" presentation real leadsheets often use.
    ws = wb.create_sheet("SOI Lead")
    set_cell(ws, "B1", "Investcorp Credit Management BDC, Inc. - Consolidated Schedule of Investments (12/31/2025)", bold=True)
    set_cell(ws, "B2", PROVENANCE_NOTE, italic=True)
    headers = ["Portfolio Company", "Industry", "Investment Type", "Cost", "Fair Value", "% of Portfolio"]
    for col, label in zip("BCDEFG", headers):
        set_cell(ws, f"{col}4", label, bold=True)

    # (name, industry, investment_type, fair_value) - all REAL except fair_value (EST split of a REAL aggregate)
    holdings = [
        ("Bioplan", "Professional Services", "First Lien Senior Secured Debt", 12_500_000),
        ("WorkGenius", "IT Services", "First Lien Senior Secured Debt", 11_200_000),
        ("Klein Hersh", "Professional Services", "First Lien Senior Secured Debt", 9_800_000),
        ("Xenon Arc", "Commercial Services & Supplies", "First Lien Senior Secured Debt", 8_900_000),
        ("ArborWorks", "Commercial Services & Supplies", "First Lien Senior Secured Debt", 8_100_000),
        ("Crafty Apes", "Media & Entertainment Services", "First Lien Senior Secured Debt", 7_400_000),
        ("Argano", "IT Services", "First Lien Senior Secured Debt", 7_000_000),
        ("LaserAway", "Diversified Consumer Services", "Preferred Equity", 6_600_000),
    ]
    r = 5
    cost_total = 0
    for name, industry, inv_type, fv in holdings:
        cost = round(fv * 1.038 / 1000) * 1000  # EST - consistent with the year's net unrealized depreciation
        cost_total += cost
        set_cell(ws, f"B{r}", name)
        set_cell(ws, f"C{r}", industry)
        set_cell(ws, f"D{r}", inv_type)
        set_cell(ws, f"E{r}", cost, number=True)
        set_cell(ws, f"F{r}", fv, number=True)
        set_cell(ws, f"G{r}", round(fv / 172_700_000, 4))
        r += 1

    named_total = sum(h[3] for h in holdings)
    remaining_top10 = 85_300_000 - named_total  # REAL top-10 aggregate minus EST named total
    remaining_top10_cost = round(remaining_top10 * 1.038 / 1000) * 1000
    cost_total += remaining_top10_cost
    set_cell(ws, f"B{r}", "Other top-10 portfolio companies (2 positions, not individually named in available public disclosures)")
    set_cell(ws, f"C{r}", "Various")
    set_cell(ws, f"D{r}", "First Lien Senior Secured Debt")
    set_cell(ws, f"E{r}", remaining_top10_cost, number=True)
    set_cell(ws, f"F{r}", remaining_top10, number=True)
    set_cell(ws, f"G{r}", round(remaining_top10 / 172_700_000, 4))
    r += 1

    remaining_total = 172_700_000 - 85_300_000  # REAL: portfolio total minus REAL top-10 aggregate
    remaining_total_cost = round(remaining_total * 1.02 / 1000) * 1000
    cost_total += remaining_total_cost
    set_cell(ws, f"B{r}", "Remaining 27 portfolio companies, individually less than 5% of the portfolio")
    set_cell(ws, f"C{r}", "Various (18 industries total)")
    set_cell(ws, f"D{r}", "Mixed - primarily First Lien Senior Secured Debt")
    set_cell(ws, f"E{r}", remaining_total_cost, number=True)
    set_cell(ws, f"F{r}", remaining_total, number=True)
    set_cell(ws, f"G{r}", round(remaining_total / 172_700_000, 4))
    r += 1

    total_row = r
    set_cell(ws, f"B{total_row}", "Total portfolio investments", bold=True)
    set_cell(ws, f"E{total_row}", cost_total, bold=True, number=True)
    set_cell(ws, f"F{total_row}", 172_700_000, bold=True, number=True)  # REAL
    set_cell(ws, f"G{total_row}", 1.0, bold=True)

    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 26
    ws.column_dimensions["D"].width = 30
    for col in "EFG":
        ws.column_dimensions[col].width = 14

    # --- SCPC Lead: Statement of Changes in Net Assets ----------------------
    # A public BDC has common shareholders, not GP/LP partners - a genuinely
    # different capital structure (single "amount" column) from both
    # synthetic sample funds.
    ws = wb.create_sheet("SCPC Lead")
    set_cell(ws, "B1", "Investcorp Credit Management BDC, Inc. - Consolidated Statement of Changes in Net Assets", bold=True)
    set_cell(ws, "B2", PROVENANCE_NOTE, italic=True)
    set_cell(ws, "B4", "Line Item", bold=True)
    set_cell(ws, "C4", "Amount", bold=True)

    scpc_rows = [
        ("Net assets, beginning of period", 77_600_000, False),   # EST (from real NAV/share x est. share count)
        ("Net decrease in net assets resulting from operations", -8_848_000, False),  # REAL
        ("Distributions to shareholders", -7_452_000, False),     # EST-derived plug
        ("Net assets, end of period", 61_300_000, True),          # REAL
    ]
    r = 5
    for label, amount, bold in scpc_rows:
        set_cell(ws, f"B{r}", label, bold=bold)
        set_cell(ws, f"C{r}", amount, number=True, bold=bold)
        r += 1
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 16

    # --- SOCF Lead: Statement of Cash Flows ---------------------------------
    ws = wb.create_sheet("SOCF Lead")
    set_cell(ws, "B1", "Investcorp Credit Management BDC, Inc. - Consolidated Statement of Cash Flows", bold=True)
    set_cell(ws, "B2", PROVENANCE_NOTE, italic=True)
    set_cell(ws, "B4", "Line Item", bold=True)
    set_cell(ws, "C4", "Amount", bold=True)

    socf_rows = [
        ("OPERATING ACTIVITIES", None, True, True),
        ("Net decrease in net assets resulting from operations", -8_848_000, False, False),  # REAL
        ("Net change in unrealized loss on investments (add back)", 6_553_000, False, False),  # EST-derived
        ("Net realized loss on investments (add back)", 4_200_000, False, False),              # EST-derived
        ("New investments funded", -45_000_000, False, False),                                 # EST
        ("Proceeds from repayments/sales of investments", 52_300_000, False, False),           # EST
        ("Net accretion of discount", -600_000, False, False),                                 # EST
        ("Changes in interest receivable", 400_000, False, False),                             # EST
        ("Changes in accrued expenses and other liabilities", 400_000, False, False),          # EST plug
        ("Net cash provided by operating activities", 9_405_000, True, False),                 # EST-derived sum
        ("FINANCING ACTIVITIES", None, True, True),
        ("Borrowings under credit facility", 12_000_000, False, False),                        # EST
        ("Repayments under credit facility", -15_100_000, False, False),                       # EST-derived (ties facility roll-forward)
        ("Distributions paid to shareholders", -7_452_000, False, False),                      # EST-derived (ties SCPC)
        ("Net cash used in financing activities", -10_552_000, True, False),                   # EST-derived sum
        ("Net increase (decrease) in cash", -1_147_000, True, False),                          # EST-derived
        ("Cash, beginning of period", 10_647_000, False, False),                               # EST-derived
        ("Cash, end of period", 9_500_000, True, False),                                       # EST (ties BS current cash)
    ]
    r = 5
    for label, amount, bold, is_header in socf_rows:
        set_cell(ws, f"B{r}", label, bold=bold)
        if not is_header:
            set_cell(ws, f"C{r}", amount, number=True, bold=bold)
        r += 1
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["C"].width = 16

    # --- Notes ---------------------------------------------------------------
    ws = wb.create_sheet("Notes")
    set_cell(ws, "B1", "Investcorp Credit Management BDC, Inc. - Notes to Financial Statements", bold=True)
    set_cell(ws, "B2", PROVENANCE_NOTE, italic=True)
    notes_rows = [
        ("Debt and Borrowings", None, True),
        ("Credit facility outstanding balance", 58_900_000, False),  # REAL
        ("Credit facility terms", "$100.0M Capital One senior secured revolving credit facility, SOFR + 2.50%, maturing 2029", False),  # REAL
        ("Portfolio Composition", None, True),
        ("Portfolio summary", "37 portfolio companies, 18 industries, 67 positions; 81% first-lien senior secured debt; ~9.1% weighted-average coupon; ~70% sponsor-backed", False),  # REAL
        ("Fair Value Measurement", None, True),
        ("Fair value measurement level", "Level 3", False),  # EST (standard for a BDC's private debt portfolio)
    ]
    r = 5
    for label, value, is_header in notes_rows:
        set_cell(ws, f"B{r}", label, bold=is_header)
        if not is_header:
            set_cell(ws, f"C{r}", value)
        r += 1
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 90

    out_path = WORKBOOKS_DIR / "Investcorp_Credit_Management_BDC_2025_NAV_Pack.xlsx"
    wb.save(out_path)
    return out_path


def mapping_config() -> dict:
    bs_cols = {"current_year": "C", "prior_year": "D"}
    bs_items = [
        {"key": "investments_at_fair_value", "label": "Investments, at fair value", "row": 7},
        {"key": "cash_and_equivalents", "label": "Cash and cash equivalents", "row": 8},
        {"key": "interest_receivable", "label": "Interest receivable", "row": 9},
        {"key": "other_assets", "label": "Other assets", "row": 10},
        {"key": "total_assets", "label": "Total assets", "row": 11, "is_total": True},
        {"key": "credit_facility_payable", "label": "Credit facility payable", "row": 14},
        {"key": "accrued_expenses", "label": "Accrued expenses and other liabilities", "row": 15},
        {"key": "other_borrowings", "label": "Other borrowings", "row": 16},
        {"key": "total_liabilities", "label": "Total liabilities", "row": 17, "is_total": True},
        {"key": "net_assets", "label": "Net assets", "row": 20, "is_total": True},
        {"key": "total_liabilities_and_net_assets", "label": "Total liabilities and net assets", "row": 21, "is_total": True},
    ]
    is_cols = {"current_year": "C", "prior_year": "D"}
    is_items = [
        {"key": "interest_income", "label": "Interest income", "row": 7},
        {"key": "fee_income", "label": "Fee income and other", "row": 8},
        {"key": "total_investment_income", "label": "Total investment income", "row": 9, "is_total": True},
        {"key": "management_fees", "label": "Management fees", "row": 12},
        {"key": "interest_and_financing_expenses", "label": "Interest and financing expenses", "row": 13},
        {"key": "general_and_administrative", "label": "General and administrative expenses", "row": 14},
        {"key": "total_expenses", "label": "Total expenses", "row": 15, "is_total": True},
        {"key": "net_investment_income_before_taxes", "label": "Net investment income before taxes", "row": 17, "is_total": True},
        {"key": "income_tax_expense", "label": "Income tax expense", "row": 18},
        {"key": "net_investment_income", "label": "Net investment income", "row": 19, "is_total": True},
        {"key": "net_realized_gain", "label": "Net realized gain (loss) on investments", "row": 21},
        {"key": "net_unrealized_gain", "label": "Net change in unrealized gain (loss) on investments", "row": 22},
        {"key": "net_realized_and_unrealized", "label": "Net realized and unrealized gain (loss)", "row": 23, "is_total": True},
        {"key": "net_increase_from_operations", "label": "Net increase (decrease) in net assets resulting from operations", "row": 25, "is_total": True},
    ]
    scpc_cols = {"amount": "C"}
    scpc_items = [
        {"key": "beginning_net_assets", "label": "Net assets, beginning of period", "row": 5},
        {"key": "net_increase_from_operations", "label": "Net decrease in net assets resulting from operations", "row": 6},
        {"key": "distributions", "label": "Distributions to shareholders", "row": 7},
        {"key": "ending_net_assets", "label": "Net assets, end of period", "row": 8, "is_total": True},
    ]
    socf_cols = {"amount": "C"}
    socf_items = [
        {"key": "net_increase_from_operations", "label": "Net decrease in net assets resulting from operations", "row": 6},
        {"key": "net_unrealized_adj", "label": "Net change in unrealized loss on investments (add back)", "row": 7},
        {"key": "net_realized_adj", "label": "Net realized loss on investments (add back)", "row": 8},
        {"key": "new_investments_funded", "label": "New investments funded", "row": 9},
        {"key": "proceeds_from_repayments", "label": "Proceeds from repayments/sales of investments", "row": 10},
        {"key": "net_accretion", "label": "Net accretion of discount", "row": 11},
        {"key": "changes_interest_receivable", "label": "Changes in interest receivable", "row": 12},
        {"key": "changes_accrued_expenses", "label": "Changes in accrued expenses and other liabilities", "row": 13},
        {"key": "net_cash_operating", "label": "Net cash provided by operating activities", "row": 14, "is_total": True},
        {"key": "borrowings_under_facility", "label": "Borrowings under credit facility", "row": 16},
        {"key": "repayments_under_facility", "label": "Repayments under credit facility", "row": 17},
        {"key": "distributions_paid", "label": "Distributions paid to shareholders", "row": 18},
        {"key": "net_cash_financing", "label": "Net cash used in financing activities", "row": 19, "is_total": True},
        {"key": "net_change_in_cash", "label": "Net increase (decrease) in cash", "row": 20, "is_total": True},
        {"key": "cash_beginning_of_period", "label": "Cash, beginning of period", "row": 21},
        {"key": "cash_end_of_period", "label": "Cash, end of period", "row": 22, "is_total": True},
    ]
    notes_items = [
        {"key": "credit_facility_outstanding", "label": "Credit facility outstanding balance", "row": 6, "column": "C", "value_type": "number"},
        {"key": "credit_facility_terms", "label": "Credit facility terms", "row": 7, "column": "C", "value_type": "text"},
        {"key": "portfolio_summary", "label": "Portfolio summary", "row": 9, "column": "C", "value_type": "text"},
        {"key": "fair_value_measurement_level", "label": "Fair value measurement level", "row": 11, "column": "C", "value_type": "text"},
    ]

    return {
        "statements": {
            "balance_sheet": {"present": True, "sheet_name": "BS Lead", "type": "line_items", "columns": bs_cols, "line_items": bs_items},
            "income_statement": {"present": True, "sheet_name": "IS Lead", "type": "line_items", "columns": is_cols, "line_items": is_items},
            "schedule_of_investments": {
                "present": True,
                "sheet_name": "SOI Lead",
                "type": "table",
                "table": {
                    "start_row": 5,
                    "end_row": 14,
                    "columns": {
                        "security_name": "B",
                        "industry": "C",
                        "investment_type": "D",
                        "cost": "E",
                        "fair_value": "F",
                        "pct_of_total": "G",
                    },
                    "total_row": 15,
                },
            },
            "statement_of_changes_in_partners_capital": {"present": True, "sheet_name": "SCPC Lead", "type": "line_items", "columns": scpc_cols, "line_items": scpc_items},
            "statement_of_cash_flows": {"present": True, "sheet_name": "SOCF Lead", "type": "line_items", "columns": socf_cols, "line_items": socf_items},
            "notes": {"present": True, "sheet_name": "Notes", "type": "notes", "notes_items": notes_items},
        },
        "cross_checks": [
            {
                "name": "Balance Sheet self-balances (Assets = Liabilities + Net Assets)",
                "left": "balance_sheet.total_assets.current_year",
                "right": "balance_sheet.total_liabilities_and_net_assets.current_year",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet"],
            },
            {
                "name": "Net decrease in net assets ties from Statement of Operations to Statement of Changes in Net Assets",
                "left": "income_statement.net_increase_from_operations.current_year",
                "right": "statement_of_changes_in_partners_capital.net_increase_from_operations.amount",
                "tolerance": 0.01,
                "applies_if_present": ["income_statement", "statement_of_changes_in_partners_capital"],
            },
            {
                "name": "Ending Net Assets ties from Statement of Changes in Net Assets to Balance Sheet",
                "left": "balance_sheet.net_assets.current_year",
                "right": "statement_of_changes_in_partners_capital.ending_net_assets.amount",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "statement_of_changes_in_partners_capital"],
            },
            {
                "name": "Schedule of Investments fair value ties to Balance Sheet investments",
                "left": "balance_sheet.investments_at_fair_value.current_year",
                "right": "schedule_of_investments.totals.fair_value",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "schedule_of_investments"],
            },
            {
                "name": "Ending cash ties from Statement of Cash Flows to Balance Sheet",
                "left": "balance_sheet.cash_and_equivalents.current_year",
                "right": "statement_of_cash_flows.cash_end_of_period.amount",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "statement_of_cash_flows"],
            },
            {
                # This check has no equivalent on either synthetic sample fund -
                # a real, extra tie-out fund accounting teams commonly run.
                "name": "Beginning-of-period cash ties from Statement of Cash Flows to prior-year Balance Sheet",
                "left": "balance_sheet.cash_and_equivalents.prior_year",
                "right": "statement_of_cash_flows.cash_beginning_of_period.amount",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "statement_of_cash_flows"],
            },
            {
                "name": "Credit facility balance ties from Notes to Balance Sheet",
                "left": "balance_sheet.credit_facility_payable.current_year",
                "right": "notes.credit_facility_outstanding",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "notes"],
            },
        ],
    }


def _add_heading(doc, text, size=16, bold=True, space_after=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(space_after)
    return p


def _add_tag_paragraph(doc, text, size=10, bold=False, italic=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    return p


def build_template() -> Path:
    doc = Document()
    _add_heading(doc, "{{ fund_name }}", size=18)
    _add_tag_paragraph(
        doc,
        "{{ client_name }} | Period Ended {{ period_end_date }} | Currency: {{ currency }} | "
        "TEST FIXTURE - grounded in real public figures where sourced, not an official filing",
        italic=True,
    )
    doc.add_paragraph()

    _add_heading(doc, "Consolidated Statement of Assets and Liabilities", size=13)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Line Item"
    hdr[1].text = "12/31/2025"
    bs_rows = [
        ("Investments, at fair value", "{{ fmt_currency(balance_sheet.investments_at_fair_value.current_year) }}"),
        ("Cash and cash equivalents", "{{ fmt_currency(balance_sheet.cash_and_equivalents.current_year) }}"),
        ("Total assets", "{{ fmt_currency(balance_sheet.total_assets.current_year) }}"),
        ("Credit facility payable", "{{ fmt_currency(balance_sheet.credit_facility_payable.current_year) }}"),
        ("Total liabilities", "{{ fmt_currency(balance_sheet.total_liabilities.current_year) }}"),
        ("Net assets", "{{ fmt_currency(balance_sheet.net_assets.current_year) }}"),
    ]
    for label, tag in bs_rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = tag
    doc.add_paragraph()

    _add_heading(doc, "Consolidated Statement of Operations", size=13)
    _add_tag_paragraph(
        doc,
        "Net increase (decrease) in net assets resulting from operations: "
        "{{ fmt_currency(income_statement.net_increase_from_operations.current_year) }}",
    )
    doc.add_paragraph()

    _add_heading(doc, "Schedule of Investments (top holdings)", size=13)
    soi_table = doc.add_table(rows=1, cols=4)
    soi_table.style = "Light Grid Accent 1"
    hdr = soi_table.rows[0].cells
    hdr[0].text = "Portfolio Company"
    hdr[1].text = "Industry"
    hdr[2].text = "Cost"
    hdr[3].text = "Fair Value"
    for_row = soi_table.add_row().cells
    for_row[0].text = "{%tr for row in schedule_of_investments_rows %}"
    data_row = soi_table.add_row().cells
    data_row[0].text = "{{ row.security_name }}"
    data_row[1].text = "{{ row.industry }}"
    data_row[2].text = "{{ fmt_currency(row.cost) }}"
    data_row[3].text = "{{ fmt_currency(row.fair_value) }}"
    endfor_row = soi_table.add_row().cells
    endfor_row[0].text = "{%tr endfor %}"
    total_row = soi_table.add_row().cells
    total_row[0].text = "Total"
    total_row[2].text = "{{ fmt_currency(schedule_of_investments_totals.cost) }}"
    total_row[3].text = "{{ fmt_currency(schedule_of_investments_totals.fair_value) }}"
    doc.add_paragraph()

    _add_heading(doc, "Notes to Financial Statements", size=13)
    _add_tag_paragraph(doc, "Credit facility terms: {{ notes.credit_facility_terms }}")
    _add_tag_paragraph(doc, "Portfolio summary: {{ notes.portfolio_summary }}")

    doc.add_paragraph()
    _add_tag_paragraph(doc, "Report generated {{ generated_date }}", size=8, italic=True)

    out_path = TEMPLATES_DIR / "real_bdc_report_template.docx"
    doc.save(out_path)
    return out_path


def main():
    WORKBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    MAPPING_DIR.mkdir(parents=True, exist_ok=True)

    wb_path = build_workbook()
    print(f"Wrote {wb_path}")
    template_path = build_template()
    print(f"Wrote {template_path}")
    mapping_path = MAPPING_DIR / "investcorp_credit_management_bdc_mapping.json"
    mapping_path.write_text(json.dumps(mapping_config(), indent=2))
    print(f"Wrote {mapping_path}")


if __name__ == "__main__":
    main()
