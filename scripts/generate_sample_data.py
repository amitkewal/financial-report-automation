"""Generates the two contrasting sample fund workbooks (a PE fund WITH a
Schedule of Investments, and a debt fund WITHOUT one), plus their Word
report templates and hand-authored mapping configs.

These are the fixtures used by scripts/run_sample_e2e.py to prove the
mapping + validation + report engine works end-to-end for two structurally
different funds without any fund-specific code.

Run: python scripts/generate_sample_data.py
"""

import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.worksheet import Worksheet
from docx import Document
from docx.shared import Pt, Inches

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "sample_data"
WORKBOOKS_DIR = SAMPLE_DIR / "workbooks"
TEMPLATES_DIR = SAMPLE_DIR / "templates"
MAPPING_DIR = SAMPLE_DIR / "mapping_configs"

NUM_FMT = "#,##0;(#,##0)"
BOLD = Font(bold=True)
TITLE_FONT = Font(bold=True, size=13)


def set_cell(ws: Worksheet, ref: str, value, bold=False, number=False, italic=False):
    cell = ws[ref]
    cell.value = value
    if bold or italic:
        cell.font = Font(bold=bold, italic=italic)
    if number:
        cell.number_format = NUM_FMT
    return cell


def add_contacts_sheet(wb, fund_name: str, fund_type: str):
    ws = wb.create_sheet("Contacts and links")
    set_cell(ws, "A1", "Client / Fund Metadata", bold=True)
    rows = [
        ("Fund Legal Name", fund_name),
        ("Fund Type", fund_type),
        ("Onshore Team", "NY Fund Admin Team"),
        ("Offshore Team", "Bangalore Fund Admin Team"),
        ("Storage Link", "https://example-storage.internal/funds/" + fund_name.replace(" ", "-")),
    ]
    for i, (label, value) in enumerate(rows, start=3):
        set_cell(ws, f"A{i}", label, bold=True)
        set_cell(ws, f"B{i}", value)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 50


def add_process_sheet(wb):
    ws = wb.create_sheet("Process")
    set_cell(ws, "A1", "Preparation Checklist (informational only, not extracted)", bold=True)
    steps = [
        "1. Confirm trial balance tie-out",
        "2. Roll forward SOI from prior period",
        "3. Prepare BS / IS / SCPC / SOCF leads",
        "4. Run cross-checks",
        "5. Route for review and sign-off",
    ]
    for i, step in enumerate(steps, start=3):
        set_cell(ws, f"A{i}", step)
    ws.column_dimensions["A"].width = 50


def add_bs_lead(wb, title: str, values: dict, has_due_to_affiliates: bool, investments_label: str):
    ws = wb.create_sheet("BS Lead")
    set_cell(ws, "B1", title, bold=True)
    set_cell(ws, "B3", "Line Item", bold=True)
    for col, label in zip("CDEF", ["Unadjusted", "Adjustments", "Adjusted", "Prior Year"]):
        set_cell(ws, f"{col}3", label, bold=True)

    def row(r, label, key, bold=False):
        v = values[key]
        set_cell(ws, f"B{r}", label, bold=bold)
        set_cell(ws, f"C{r}", v["unadjusted"], number=True, bold=bold)
        set_cell(ws, f"D{r}", v["adjustments"], number=True, bold=bold)
        set_cell(ws, f"E{r}", v["adjusted"], number=True, bold=bold)
        set_cell(ws, f"F{r}", v["prior_year"], number=True, bold=bold)

    set_cell(ws, "B5", "ASSETS", bold=True)
    row(6, investments_label, "investments_at_fair_value")
    row(7, "Cash and cash equivalents", "cash_and_equivalents")
    row(8, "Interest / dividends receivable" if not has_due_to_affiliates else "Due from affiliates", "receivable_or_due_from")
    row(9, "Other assets", "other_assets")
    row(10, "Total assets", "total_assets", bold=True)

    set_cell(ws, "B12", "LIABILITIES", bold=True)
    row(13, "Accrued expenses", "accrued_expenses")
    row(14, "Due to affiliates" if has_due_to_affiliates else "Credit facility payable", "second_liability")
    row(15, "Total liabilities", "total_liabilities", bold=True)

    set_cell(ws, "B17", "PARTNERS' CAPITAL", bold=True)
    row(18, "General Partner", "gp_capital")
    row(19, "Limited Partners", "lp_capital")
    row(20, "Total partners' capital", "total_partners_capital", bold=True)

    row(22, "Total liabilities and partners' capital", "total_liabilities_and_capital", bold=True)

    ws.column_dimensions["B"].width = 42
    for col in "CDEF":
        ws.column_dimensions[col].width = 16
    return ws


def add_is_lead(wb, title: str, values: dict, income_labels: dict, expense_labels: dict):
    ws = wb.create_sheet("IS Lead")
    set_cell(ws, "B1", title, bold=True)
    set_cell(ws, "B3", "Line Item", bold=True)
    for col, label in zip("CDEF", ["Unadjusted", "Adjustments", "Adjusted", "Prior Year"]):
        set_cell(ws, f"{col}3", label, bold=True)

    def row(r, label, key, bold=False):
        v = values[key]
        set_cell(ws, f"B{r}", label, bold=bold)
        set_cell(ws, f"C{r}", v["unadjusted"], number=True, bold=bold)
        set_cell(ws, f"D{r}", v["adjustments"], number=True, bold=bold)
        set_cell(ws, f"E{r}", v["adjusted"], number=True, bold=bold)
        set_cell(ws, f"F{r}", v["prior_year"], number=True, bold=bold)

    set_cell(ws, "B5", "INVESTMENT INCOME", bold=True)
    row(6, income_labels["line1"], "income_line1")
    row(7, income_labels["line2"], "income_line2")
    row(8, "Total investment income", "total_investment_income", bold=True)

    set_cell(ws, "B10", "EXPENSES", bold=True)
    row(11, expense_labels["line1"], "expense_line1")
    row(12, expense_labels["line2"], "expense_line2")
    row(13, "Total expenses", "total_expenses", bold=True)

    row(15, "Net investment income", "net_investment_income", bold=True)
    row(17, "Net realized gain (loss) on investments", "net_realized_gain")
    row(18, "Net change in unrealized gain (loss) on investments", "net_unrealized_gain")
    row(19, "Net realized and unrealized gain (loss)", "net_realized_and_unrealized", bold=True)
    row(21, "Net increase in partners' capital resulting from operations", "net_increase_from_operations", bold=True)

    ws.column_dimensions["B"].width = 50
    for col in "CDEF":
        ws.column_dimensions[col].width = 16
    return ws


def add_scpc_lead(wb, title: str, rows_data: list):
    ws = wb.create_sheet("SCPC Lead")
    set_cell(ws, "B1", title, bold=True)
    set_cell(ws, "B3", "Line Item", bold=True)
    for col, label in zip("CDE", ["GP", "LP", "Total"]):
        set_cell(ws, f"{col}3", label, bold=True)
    r = 5
    for label, gp, lp, total, bold in rows_data:
        set_cell(ws, f"B{r}", label, bold=bold)
        set_cell(ws, f"C{r}", gp, number=True, bold=bold)
        set_cell(ws, f"D{r}", lp, number=True, bold=bold)
        set_cell(ws, f"E{r}", total, number=True, bold=bold)
        r += 1
    ws.column_dimensions["B"].width = 55
    for col in "CDE":
        ws.column_dimensions[col].width = 16
    return ws, {label: idx for idx, (label, *_rest) in enumerate(rows_data, start=5)}


def add_socf_lead(wb, title: str, rows_data: list):
    ws = wb.create_sheet("SOCF Lead")
    set_cell(ws, "B1", title, bold=True)
    set_cell(ws, "B3", "Line Item", bold=True)
    set_cell(ws, "C3", "Amount", bold=True)
    set_cell(ws, "D3", "Prior Year", bold=True)
    r = 5
    row_map = {}
    for label, amount, prior_year, bold, is_header in rows_data:
        set_cell(ws, f"B{r}", label, bold=bold)
        if not is_header:
            set_cell(ws, f"C{r}", amount, number=True, bold=bold)
            set_cell(ws, f"D{r}", prior_year, number=True, bold=bold)
        row_map[label] = r
        r += 1
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    return ws, row_map


def add_soi_lead(wb, title: str, investments: list):
    ws = wb.create_sheet("SOI Lead")
    set_cell(ws, "B1", title, bold=True)
    headers = ["Security", "Region", "Industry", "Cost", "Fair Value", "% of Total"]
    for col, label in zip("BCDEFG", headers):
        set_cell(ws, f"{col}5", label, bold=True)
    r = 6
    for inv in investments:
        set_cell(ws, f"B{r}", inv["security_name"])
        set_cell(ws, f"C{r}", inv["region"])
        set_cell(ws, f"D{r}", inv["industry"])
        set_cell(ws, f"E{r}", inv["cost"], number=True)
        set_cell(ws, f"F{r}", inv["fair_value"], number=True)
        set_cell(ws, f"G{r}", inv["pct_of_total"])
        r += 1
    total_row = r
    total_cost = sum(i["cost"] for i in investments)
    total_fv = sum(i["fair_value"] for i in investments)
    set_cell(ws, f"B{total_row}", "Total", bold=True)
    set_cell(ws, f"E{total_row}", total_cost, number=True, bold=True)
    set_cell(ws, f"F{total_row}", total_fv, number=True, bold=True)
    set_cell(ws, f"G{total_row}", 1.0, bold=True)
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    for col in "EFG":
        ws.column_dimensions[col].width = 14
    return ws, total_row


def add_notes_sheet(wb, title: str, items: list):
    ws = wb.create_sheet("Notes")
    set_cell(ws, "B1", title, bold=True)
    r = 4
    row_map = {}
    for label, value, is_header in items:
        set_cell(ws, f"B{r}", label, bold=is_header)
        if not is_header:
            set_cell(ws, f"C{r}", value)
        row_map[label] = r
        r += 1
    ws.column_dimensions["B"].width = 45
    ws.column_dimensions["C"].width = 20
    return ws, row_map


def col_set(unadjusted, adjustments, prior_year):
    return {
        "unadjusted": unadjusted,
        "adjustments": adjustments,
        "adjusted": round(unadjusted + adjustments, 2),
        "prior_year": prior_year,
    }


def build_pe_fund_workbook() -> Path:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    add_contacts_sheet(wb, "Alpha PE Fund I", "Private Equity")
    add_process_sheet(wb)

    bs_values = {
        "investments_at_fair_value": col_set(84_500_000, 500_000, 78_000_000),
        "cash_and_equivalents": col_set(5_200_000, 0, 4_900_000),
        "receivable_or_due_from": col_set(300_000, 0, 250_000),
        "other_assets": col_set(500_000, 0, 450_000),
        "total_assets": col_set(90_500_000, 500_000, 83_600_000),
        "accrued_expenses": col_set(800_000, 0, 700_000),
        "second_liability": col_set(200_000, 0, 150_000),
        "total_liabilities": col_set(1_000_000, 0, 850_000),
        "gp_capital": col_set(895_000, 5_000, 830_000),
        "lp_capital": col_set(88_605_000, 495_000, 81_920_000),
        "total_partners_capital": col_set(89_500_000, 500_000, 82_750_000),
        "total_liabilities_and_capital": col_set(90_500_000, 500_000, 83_600_000),
    }
    add_bs_lead(wb, "Alpha PE Fund I - Statement of Assets, Liabilities and Partners' Capital", bs_values, True, "Investments, at fair value")

    is_values = {
        "income_line1": col_set(1_200_000, 0, 1_050_000),
        "income_line2": col_set(300_000, 0, 260_000),
        "total_investment_income": col_set(1_500_000, 0, 1_310_000),
        "expense_line1": col_set(900_000, 0, 820_000),
        "expense_line2": col_set(200_000, 0, 180_000),
        "total_expenses": col_set(1_100_000, 0, 1_000_000),
        "net_investment_income": col_set(400_000, 0, 310_000),
        "net_realized_gain": col_set(600_000, 0, 400_000),
        "net_unrealized_gain": col_set(0, 500_000, 350_000),
        "net_realized_and_unrealized": col_set(600_000, 500_000, 750_000),
        "net_increase_from_operations": col_set(1_000_000, 500_000, 1_060_000),
    }
    add_is_lead(
        wb,
        "Alpha PE Fund I - Statement of Operations",
        is_values,
        {"line1": "Interest income", "line2": "Dividend income"},
        {"line1": "Management fees", "line2": "Fund expenses"},
    )

    scpc_rows = [
        ("Partners' capital, beginning of period", 850_000, 87_650_000, 88_500_000, False),
        ("Net increase in partners' capital resulting from operations", 15_000, 1_485_000, 1_500_000, False),
        ("Partners' capital, end of period", 865_000, 89_135_000, 90_000_000, True),
    ]
    # Note: SCPC totals intentionally reconcile to BS total_partners_capital (90,000,000 = 89,500,000 + 500,000 adjustment)
    add_scpc_lead(wb, "Alpha PE Fund I - Statement of Changes in Partners' Capital", scpc_rows)

    investments = [
        {"security_name": "TechCo Holdings", "region": "North America", "industry": "Technology", "cost": 20_000_000, "fair_value": 25_000_000, "pct_of_total": 0.294},
        {"security_name": "MedDevice Corp", "region": "North America", "industry": "Healthcare", "cost": 15_000_000, "fair_value": 18_000_000, "pct_of_total": 0.212},
        {"security_name": "EuroLogistics Ltd", "region": "Europe", "industry": "Industrials", "cost": 12_000_000, "fair_value": 14_000_000, "pct_of_total": 0.165},
        {"security_name": "AsiaRetail Group", "region": "Asia", "industry": "Consumer", "cost": 10_000_000, "fair_value": 13_000_000, "pct_of_total": 0.153},
        {"security_name": "GreenEnergy Partners", "region": "North America", "industry": "Energy", "cost": 13_000_000, "fair_value": 15_000_000, "pct_of_total": 0.176},
    ]
    add_soi_lead(wb, "Alpha PE Fund I - Schedule of Investments", investments)

    socf_rows = [
        ("OPERATING ACTIVITIES", None, None, True, True),
        ("Net increase in partners' capital resulting from operations", 1_500_000, 1_060_000, False, False),
        ("Net change in unrealized gain on investments", -500_000, -350_000, False, False),
        ("Net realized gain on investments", -600_000, -400_000, False, False),
        ("Purchases of investments", -10_000_000, -8_500_000, False, False),
        ("Proceeds from sale of investments", 9_000_000, 7_800_000, False, False),
        ("Changes in due from affiliates", -100_000, -50_000, False, False),
        ("Changes in accrued expenses", 300_000, 200_000, False, False),
        ("Net cash used in operating activities", -400_000, -240_000, True, False),
        ("FINANCING ACTIVITIES", None, None, True, True),
        ("Distributions to partners", 0, -100_000, False, False),
        ("Net cash used in financing activities", 0, -100_000, True, False),
        ("Net increase (decrease) in cash", -400_000, -340_000, True, False),
        ("Cash, beginning of period", 5_600_000, 5_240_000, False, False),
        ("Cash, end of period", 5_200_000, 4_900_000, True, False),
    ]
    add_socf_lead(wb, "Alpha PE Fund I - Statement of Cash Flows", socf_rows)

    notes_items = [
        ("Fair Value Measurement", None, True),
        ("Fair value measurement level", "Level 3", False),
        ("Partners' Capital", None, True),
        ("Related party management fee rate", "2.0%", False),
        ("Related Party Transactions", None, True),
        ("Due to affiliates balance", 200_000, False),
    ]
    add_notes_sheet(wb, "Alpha PE Fund I - Notes to Financial Statements", notes_items)

    out_path = WORKBOOKS_DIR / "Alpha_PE_Fund_I_2025Q4_NAV_Pack.xlsx"
    wb.save(out_path)
    return out_path


def build_debt_fund_workbook() -> Path:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    add_contacts_sheet(wb, "Beta Debt Fund II", "Debt")
    add_process_sheet(wb)

    bs_values = {
        "investments_at_fair_value": col_set(45_000_000, 0, 41_000_000),
        "cash_and_equivalents": col_set(3_000_000, 0, 1_200_000),
        "receivable_or_due_from": col_set(400_000, 0, 380_000),
        "other_assets": col_set(100_000, 0, 90_000),
        "total_assets": col_set(48_500_000, 0, 42_670_000),
        "accrued_expenses": col_set(500_000, 0, 450_000),
        "second_liability": col_set(10_000_000, 0, 9_500_000),
        "total_liabilities": col_set(10_500_000, 0, 9_950_000),
        "gp_capital": col_set(380_000, 0, 327_000),
        "lp_capital": col_set(37_620_000, 0, 32_393_000),
        "total_partners_capital": col_set(38_000_000, 0, 32_720_000),
        "total_liabilities_and_capital": col_set(48_500_000, 0, 42_670_000),
    }
    add_bs_lead(
        wb,
        "Beta Debt Fund II - Statement of Assets, Liabilities and Partners' Capital",
        bs_values,
        False,
        "Loans and debt investments, at fair value",
    )

    is_values = {
        "income_line1": col_set(3_800_000, 0, 3_400_000),
        "income_line2": col_set(200_000, 0, 180_000),
        "total_investment_income": col_set(4_000_000, 0, 3_580_000),
        "expense_line1": col_set(700_000, 0, 640_000),
        "expense_line2": col_set(600_000, 0, 520_000),
        "total_expenses": col_set(1_300_000, 0, 1_160_000),
        "net_investment_income": col_set(2_700_000, 0, 2_420_000),
        "net_realized_gain": col_set(100_000, 0, 60_000),
        "net_unrealized_gain": col_set(-300_000, 0, -120_000),
        "net_realized_and_unrealized": col_set(-200_000, 0, -60_000),
        "net_increase_from_operations": col_set(2_500_000, 0, 2_360_000),
    }
    add_is_lead(
        wb,
        "Beta Debt Fund II - Statement of Operations",
        is_values,
        {"line1": "Interest income", "line2": "Fee income"},
        {"line1": "Management fees", "line2": "Interest expense (credit facility)"},
    )

    scpc_rows = [
        ("Partners' capital, beginning of period", 350_000, 34_650_000, 35_000_000, False),
        ("Contributions", 5_000, 495_000, 500_000, False),
        ("Net increase in partners' capital resulting from operations", 25_000, 2_475_000, 2_500_000, False),
        ("Distributions", 0, 0, 0, False),
        ("Partners' capital, end of period", 380_000, 37_620_000, 38_000_000, True),
    ]
    add_scpc_lead(wb, "Beta Debt Fund II - Statement of Changes in Partners' Capital", scpc_rows)

    socf_rows = [
        ("OPERATING ACTIVITIES", None, None, True, True),
        ("Net increase in partners' capital resulting from operations", 2_500_000, 2_360_000, False, False),
        ("Net unrealized loss on investments", 300_000, 120_000, False, False),
        ("Net realized gain on investments", -100_000, -60_000, False, False),
        ("Fundings of loans", -8_000_000, -6_500_000, False, False),
        ("Repayments of loans received", 6_000_000, 5_200_000, False, False),
        ("Changes in interest receivable", -100_000, -60_000, False, False),
        ("Changes in accrued expenses", 200_000, 150_000, False, False),
        ("Net cash provided by operating activities", 800_000, 1_210_000, True, False),
        ("FINANCING ACTIVITIES", None, None, True, True),
        ("Capital contributions received", 500_000, 400_000, False, False),
        ("Draws on credit facility", 2_000_000, 1_500_000, False, False),
        ("Repayments of credit facility", -1_500_000, -1_000_000, False, False),
        ("Net cash provided by financing activities", 1_000_000, 900_000, True, False),
        ("Net increase in cash", 1_800_000, 2_110_000, True, False),
        ("Cash, beginning of period", 1_200_000, -910_000, False, False),
        ("Cash, end of period", 3_000_000, 1_200_000, True, False),
    ]
    add_socf_lead(wb, "Beta Debt Fund II - Statement of Cash Flows", socf_rows)

    notes_items = [
        ("Debt and Borrowings", None, True),
        ("Credit facility outstanding balance", 10_000_000, False),
        ("Interest rate on credit facility", "SOFR + 3.5%", False),
        ("Fair Value Measurement", None, True),
        ("Fair value measurement level", "Level 3", False),
    ]
    add_notes_sheet(wb, "Beta Debt Fund II - Notes to Financial Statements", notes_items)

    # Deliberately NO "SOI Lead" sheet - this fund has no schedule of investments.
    out_path = WORKBOOKS_DIR / "Beta_Debt_Fund_II_2025Q4_NAV_Pack.xlsx"
    wb.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Mapping configs (hand-authored to match the workbooks above exactly - in
# the real product a Preparer would build these via the UI's confirm-mapping
# screen, seeded by the auto-detection helper).
# ---------------------------------------------------------------------------

def pe_fund_mapping_config() -> dict:
    bs_cols = {"unadjusted": "C", "adjustments": "D", "adjusted": "E", "prior_year": "F"}
    bs_items = [
        {"key": "investments_at_fair_value", "label": "Investments, at fair value", "row": 6},
        {"key": "cash_and_equivalents", "label": "Cash and cash equivalents", "row": 7},
        {"key": "due_from_affiliates", "label": "Due from affiliates", "row": 8},
        {"key": "other_assets", "label": "Other assets", "row": 9},
        {"key": "total_assets", "label": "Total assets", "row": 10, "is_total": True},
        {"key": "accrued_expenses", "label": "Accrued expenses", "row": 13},
        {"key": "due_to_affiliates", "label": "Due to affiliates", "row": 14},
        {"key": "total_liabilities", "label": "Total liabilities", "row": 15, "is_total": True},
        {"key": "gp_capital", "label": "General Partner", "row": 18},
        {"key": "lp_capital", "label": "Limited Partners", "row": 19},
        {"key": "total_partners_capital", "label": "Total partners' capital", "row": 20, "is_total": True},
        {"key": "total_liabilities_and_capital", "label": "Total liabilities and partners' capital", "row": 22, "is_total": True},
    ]
    is_items = [
        {"key": "interest_income", "label": "Interest income", "row": 6},
        {"key": "dividend_income", "label": "Dividend income", "row": 7},
        {"key": "total_investment_income", "label": "Total investment income", "row": 8, "is_total": True},
        {"key": "management_fees", "label": "Management fees", "row": 11},
        {"key": "fund_expenses", "label": "Fund expenses", "row": 12},
        {"key": "total_expenses", "label": "Total expenses", "row": 13, "is_total": True},
        {"key": "net_investment_income", "label": "Net investment income", "row": 15, "is_total": True},
        {"key": "net_realized_gain", "label": "Net realized gain on investments", "row": 17},
        {"key": "net_unrealized_gain", "label": "Net change in unrealized gain on investments", "row": 18},
        {"key": "net_realized_and_unrealized", "label": "Net realized and unrealized gain", "row": 19, "is_total": True},
        {"key": "net_increase_from_operations", "label": "Net increase in partners' capital resulting from operations", "row": 21, "is_total": True},
    ]
    scpc_cols = {"gp": "C", "lp": "D", "total": "E"}
    scpc_items = [
        {"key": "beginning_capital", "label": "Partners' capital, beginning of period", "row": 5},
        {"key": "net_increase_from_operations", "label": "Net increase in partners' capital resulting from operations", "row": 6},
        {"key": "ending_capital", "label": "Partners' capital, end of period", "row": 7, "is_total": True},
    ]
    socf_cols = {"amount": "C", "prior_year": "D"}
    socf_items = [
        {"key": "net_increase_from_operations", "label": "Net increase in partners' capital resulting from operations", "row": 6},
        {"key": "net_unrealized_gain_adj", "label": "Net change in unrealized gain on investments", "row": 7},
        {"key": "net_realized_gain_adj", "label": "Net realized gain on investments", "row": 8},
        {"key": "purchases_of_investments", "label": "Purchases of investments", "row": 9},
        {"key": "proceeds_from_sale", "label": "Proceeds from sale of investments", "row": 10},
        {"key": "changes_due_from_affiliates", "label": "Changes in due from affiliates", "row": 11},
        {"key": "changes_accrued_expenses", "label": "Changes in accrued expenses", "row": 12},
        {"key": "net_cash_operating", "label": "Net cash used in operating activities", "row": 13, "is_total": True},
        {"key": "distributions_to_partners", "label": "Distributions to partners", "row": 15},
        {"key": "net_cash_financing", "label": "Net cash used in financing activities", "row": 16, "is_total": True},
        {"key": "net_change_in_cash", "label": "Net increase (decrease) in cash", "row": 17, "is_total": True},
        {"key": "cash_beginning_of_period", "label": "Cash, beginning of period", "row": 18},
        {"key": "cash_end_of_period", "label": "Cash, end of period", "row": 19, "is_total": True},
    ]
    notes_items = [
        {"key": "fair_value_measurement_level", "label": "Fair value measurement level", "row": 5, "column": "C", "value_type": "text"},
        {"key": "related_party_fee_rate", "label": "Related party management fee rate", "row": 7, "column": "C", "value_type": "text"},
        {"key": "due_to_affiliates_balance", "label": "Due to affiliates balance", "row": 9, "column": "C", "value_type": "number"},
    ]

    return {
        "statements": {
            "balance_sheet": {"present": True, "sheet_name": "BS Lead", "type": "line_items", "columns": bs_cols, "line_items": bs_items},
            "income_statement": {"present": True, "sheet_name": "IS Lead", "type": "line_items", "columns": {"unadjusted": "C", "adjustments": "D", "adjusted": "E", "prior_year": "F"}, "line_items": is_items},
            "schedule_of_investments": {
                "present": True,
                "sheet_name": "SOI Lead",
                "type": "table",
                "table": {
                    "start_row": 6,
                    "end_row": 10,
                    "columns": {"security_name": "B", "region": "C", "industry": "D", "cost": "E", "fair_value": "F", "pct_of_total": "G"},
                    "total_row": 11,
                },
            },
            "statement_of_changes_in_partners_capital": {"present": True, "sheet_name": "SCPC Lead", "type": "line_items", "columns": scpc_cols, "line_items": scpc_items},
            "statement_of_cash_flows": {"present": True, "sheet_name": "SOCF Lead", "type": "line_items", "columns": socf_cols, "line_items": socf_items},
            "notes": {"present": True, "sheet_name": "Notes", "type": "notes", "notes_items": notes_items},
        },
        "cross_checks": [
            {
                "name": "Balance Sheet self-balances (Assets = Liabilities + Partners' Capital)",
                "left": "balance_sheet.total_assets.adjusted",
                "right": "balance_sheet.total_liabilities_and_capital.adjusted",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet"],
            },
            {
                "name": "Net income ties from Income Statement to Statement of Changes in Partners' Capital",
                "left": "income_statement.net_increase_from_operations.adjusted",
                "right": "statement_of_changes_in_partners_capital.net_increase_from_operations.total",
                "tolerance": 0.01,
                "applies_if_present": ["income_statement", "statement_of_changes_in_partners_capital"],
            },
            {
                "name": "Ending Partners' Capital ties from SCPC to Balance Sheet",
                "left": "balance_sheet.total_partners_capital.adjusted",
                "right": "statement_of_changes_in_partners_capital.ending_capital.total",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "statement_of_changes_in_partners_capital"],
            },
            {
                "name": "Schedule of Investments fair value ties to Balance Sheet investments",
                "left": "balance_sheet.investments_at_fair_value.adjusted",
                "right": "schedule_of_investments.totals.fair_value",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "schedule_of_investments"],
            },
            {
                "name": "Ending cash ties from Statement of Cash Flows to Balance Sheet",
                "left": "balance_sheet.cash_and_equivalents.adjusted",
                "right": "statement_of_cash_flows.cash_end_of_period.amount",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "statement_of_cash_flows"],
            },
            {
                "name": "Due to affiliates ties from Notes to Balance Sheet",
                "left": "balance_sheet.due_to_affiliates.adjusted",
                "right": "notes.due_to_affiliates_balance",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "notes"],
            },
        ],
    }


def debt_fund_mapping_config() -> dict:
    bs_cols = {"unadjusted": "C", "adjustments": "D", "adjusted": "E", "prior_year": "F"}
    bs_items = [
        {"key": "investments_at_fair_value", "label": "Loans and debt investments, at fair value", "row": 6},
        {"key": "cash_and_equivalents", "label": "Cash and cash equivalents", "row": 7},
        {"key": "interest_receivable", "label": "Interest receivable", "row": 8},
        {"key": "other_assets", "label": "Other assets", "row": 9},
        {"key": "total_assets", "label": "Total assets", "row": 10, "is_total": True},
        {"key": "accrued_expenses", "label": "Accrued expenses", "row": 13},
        {"key": "credit_facility_payable", "label": "Credit facility payable", "row": 14},
        {"key": "total_liabilities", "label": "Total liabilities", "row": 15, "is_total": True},
        {"key": "gp_capital", "label": "General Partner", "row": 18},
        {"key": "lp_capital", "label": "Limited Partners", "row": 19},
        {"key": "total_partners_capital", "label": "Total partners' capital", "row": 20, "is_total": True},
        {"key": "total_liabilities_and_capital", "label": "Total liabilities and partners' capital", "row": 22, "is_total": True},
    ]
    is_items = [
        {"key": "interest_income", "label": "Interest income", "row": 6},
        {"key": "fee_income", "label": "Fee income", "row": 7},
        {"key": "total_investment_income", "label": "Total investment income", "row": 8, "is_total": True},
        {"key": "management_fees", "label": "Management fees", "row": 11},
        {"key": "interest_expense", "label": "Interest expense (credit facility)", "row": 12},
        {"key": "total_expenses", "label": "Total expenses", "row": 13, "is_total": True},
        {"key": "net_investment_income", "label": "Net investment income", "row": 15, "is_total": True},
        {"key": "net_realized_gain", "label": "Net realized gain on investments", "row": 17},
        {"key": "net_unrealized_gain", "label": "Net change in unrealized gain (loss) on investments", "row": 18},
        {"key": "net_realized_and_unrealized", "label": "Net realized and unrealized gain (loss)", "row": 19, "is_total": True},
        {"key": "net_increase_from_operations", "label": "Net increase in partners' capital resulting from operations", "row": 21, "is_total": True},
    ]
    scpc_cols = {"gp": "C", "lp": "D", "total": "E"}
    scpc_items = [
        {"key": "beginning_capital", "label": "Partners' capital, beginning of period", "row": 5},
        {"key": "contributions", "label": "Contributions", "row": 6},
        {"key": "net_increase_from_operations", "label": "Net increase in partners' capital resulting from operations", "row": 7},
        {"key": "distributions", "label": "Distributions", "row": 8},
        {"key": "ending_capital", "label": "Partners' capital, end of period", "row": 9, "is_total": True},
    ]
    socf_cols = {"amount": "C", "prior_year": "D"}
    socf_items = [
        {"key": "net_increase_from_operations", "label": "Net increase in partners' capital resulting from operations", "row": 6},
        {"key": "net_unrealized_loss_adj", "label": "Net unrealized loss on investments", "row": 7},
        {"key": "net_realized_gain_adj", "label": "Net realized gain on investments", "row": 8},
        {"key": "fundings_of_loans", "label": "Fundings of loans", "row": 9},
        {"key": "repayments_of_loans", "label": "Repayments of loans received", "row": 10},
        {"key": "changes_interest_receivable", "label": "Changes in interest receivable", "row": 11},
        {"key": "changes_accrued_expenses", "label": "Changes in accrued expenses", "row": 12},
        {"key": "net_cash_operating", "label": "Net cash provided by operating activities", "row": 13, "is_total": True},
        {"key": "capital_contributions_received", "label": "Capital contributions received", "row": 15},
        {"key": "draws_on_credit_facility", "label": "Draws on credit facility", "row": 16},
        {"key": "repayments_of_credit_facility", "label": "Repayments of credit facility", "row": 17},
        {"key": "net_cash_financing", "label": "Net cash provided by financing activities", "row": 18, "is_total": True},
        {"key": "net_change_in_cash", "label": "Net increase in cash", "row": 19, "is_total": True},
        {"key": "cash_beginning_of_period", "label": "Cash, beginning of period", "row": 20},
        {"key": "cash_end_of_period", "label": "Cash, end of period", "row": 21, "is_total": True},
    ]
    notes_items = [
        {"key": "credit_facility_outstanding", "label": "Credit facility outstanding balance", "row": 5, "column": "C", "value_type": "number"},
        {"key": "credit_facility_rate", "label": "Interest rate on credit facility", "row": 6, "column": "C", "value_type": "text"},
        {"key": "fair_value_measurement_level", "label": "Fair value measurement level", "row": 8, "column": "C", "value_type": "text"},
    ]

    return {
        "statements": {
            "balance_sheet": {"present": True, "sheet_name": "BS Lead", "type": "line_items", "columns": bs_cols, "line_items": bs_items},
            "income_statement": {"present": True, "sheet_name": "IS Lead", "type": "line_items", "columns": {"unadjusted": "C", "adjustments": "D", "adjusted": "E", "prior_year": "F"}, "line_items": is_items},
            "schedule_of_investments": {"present": False},
            "statement_of_changes_in_partners_capital": {"present": True, "sheet_name": "SCPC Lead", "type": "line_items", "columns": scpc_cols, "line_items": scpc_items},
            "statement_of_cash_flows": {"present": True, "sheet_name": "SOCF Lead", "type": "line_items", "columns": socf_cols, "line_items": socf_items},
            "notes": {"present": True, "sheet_name": "Notes", "type": "notes", "notes_items": notes_items},
        },
        # No SOI-related check here at all: this fund type never has one, unlike
        # the PE fund, whose SOI check is instead SKIPPED at runtime if absent.
        "cross_checks": [
            {
                "name": "Balance Sheet self-balances (Assets = Liabilities + Partners' Capital)",
                "left": "balance_sheet.total_assets.adjusted",
                "right": "balance_sheet.total_liabilities_and_capital.adjusted",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet"],
            },
            {
                "name": "Net income ties from Income Statement to Statement of Changes in Partners' Capital",
                "left": "income_statement.net_increase_from_operations.adjusted",
                "right": "statement_of_changes_in_partners_capital.net_increase_from_operations.total",
                "tolerance": 0.01,
                "applies_if_present": ["income_statement", "statement_of_changes_in_partners_capital"],
            },
            {
                "name": "Ending Partners' Capital ties from SCPC to Balance Sheet",
                "left": "balance_sheet.total_partners_capital.adjusted",
                "right": "statement_of_changes_in_partners_capital.ending_capital.total",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "statement_of_changes_in_partners_capital"],
            },
            {
                "name": "Ending cash ties from Statement of Cash Flows to Balance Sheet",
                "left": "balance_sheet.cash_and_equivalents.adjusted",
                "right": "statement_of_cash_flows.cash_end_of_period.amount",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "statement_of_cash_flows"],
            },
            {
                "name": "Credit facility balance ties from Notes to Balance Sheet",
                "left": "balance_sheet.credit_facility_payable.adjusted",
                "right": "notes.credit_facility_outstanding",
                "tolerance": 0.01,
                "applies_if_present": ["balance_sheet", "notes"],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Word templates (docxtpl / Jinja2 syntax)
# ---------------------------------------------------------------------------

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


def build_pe_fund_template() -> Path:
    doc = Document()
    _add_heading(doc, "{{ fund_name }}", size=18)
    _add_tag_paragraph(doc, "{{ client_name }} | Period Ended {{ period_end_date }} | Currency: {{ currency }}", italic=True)
    doc.add_paragraph()

    _add_heading(doc, "Statement of Assets, Liabilities and Partners' Capital", size=13)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Line Item"
    hdr[1].text = "Adjusted"
    bs_rows = [
        ("Investments, at fair value", "{{ fmt_currency(balance_sheet.investments_at_fair_value.adjusted) }}"),
        ("Cash and cash equivalents", "{{ fmt_currency(balance_sheet.cash_and_equivalents.adjusted) }}"),
        ("Total assets", "{{ fmt_currency(balance_sheet.total_assets.adjusted) }}"),
        ("Total liabilities", "{{ fmt_currency(balance_sheet.total_liabilities.adjusted) }}"),
        ("Total partners' capital", "{{ fmt_currency(balance_sheet.total_partners_capital.adjusted) }}"),
    ]
    for label, tag in bs_rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = tag
    doc.add_paragraph()

    _add_heading(doc, "Statement of Operations", size=13)
    _add_tag_paragraph(doc, "Net increase in partners' capital resulting from operations: {{ fmt_currency(income_statement.net_increase_from_operations.adjusted) }}")
    doc.add_paragraph()

    _add_heading(doc, "Schedule of Investments", size=13)
    _add_tag_paragraph(doc, "{% if statements_present.schedule_of_investments %}")
    soi_table = doc.add_table(rows=1, cols=4)
    soi_table.style = "Light Grid Accent 1"
    hdr = soi_table.rows[0].cells
    hdr[0].text = "Security"
    hdr[1].text = "Region"
    hdr[2].text = "Cost"
    hdr[3].text = "Fair Value"
    for_row = soi_table.add_row().cells
    for_row[0].text = "{%tr for row in schedule_of_investments_rows %}"
    data_row = soi_table.add_row().cells
    data_row[0].text = "{{ row.security_name }}"
    data_row[1].text = "{{ row.region }}"
    data_row[2].text = "{{ fmt_currency(row.cost) }}"
    data_row[3].text = "{{ fmt_currency(row.fair_value) }}"
    endfor_row = soi_table.add_row().cells
    endfor_row[0].text = "{%tr endfor %}"
    total_row = soi_table.add_row().cells
    total_row[0].text = "Total"
    total_row[2].text = "{{ fmt_currency(schedule_of_investments_totals.cost) }}"
    total_row[3].text = "{{ fmt_currency(schedule_of_investments_totals.fair_value) }}"
    _add_tag_paragraph(doc, "{% endif %}")
    doc.add_paragraph()

    _add_heading(doc, "Notes to Financial Statements", size=13)
    _add_tag_paragraph(doc, "{% if notes.due_to_affiliates_balance %}Due to affiliates: {{ fmt_currency(notes.due_to_affiliates_balance) }}{% endif %}")
    _add_tag_paragraph(doc, "Fair value measurement level: {{ notes.fair_value_measurement_level }}")

    doc.add_paragraph()
    _add_tag_paragraph(doc, "Report generated {{ generated_date }}", size=8, italic=True)

    out_path = TEMPLATES_DIR / "pe_fund_report_template.docx"
    doc.save(out_path)
    return out_path


def build_debt_fund_template() -> Path:
    doc = Document()
    _add_heading(doc, "{{ fund_name }}", size=18)
    _add_tag_paragraph(doc, "{{ client_name }} | Period Ended {{ period_end_date }} | Currency: {{ currency }}", italic=True)
    doc.add_paragraph()

    _add_heading(doc, "Statement of Assets, Liabilities and Partners' Capital", size=13)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Line Item"
    hdr[1].text = "Adjusted"
    bs_rows = [
        ("Loans and debt investments, at fair value", "{{ fmt_currency(balance_sheet.investments_at_fair_value.adjusted) }}"),
        ("Cash and cash equivalents", "{{ fmt_currency(balance_sheet.cash_and_equivalents.adjusted) }}"),
        ("Total assets", "{{ fmt_currency(balance_sheet.total_assets.adjusted) }}"),
        ("Credit facility payable", "{{ fmt_currency(balance_sheet.credit_facility_payable.adjusted) }}"),
        ("Total liabilities", "{{ fmt_currency(balance_sheet.total_liabilities.adjusted) }}"),
        ("Total partners' capital", "{{ fmt_currency(balance_sheet.total_partners_capital.adjusted) }}"),
    ]
    for label, tag in bs_rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = tag
    doc.add_paragraph()

    _add_heading(doc, "Statement of Operations", size=13)
    _add_tag_paragraph(doc, "Net increase in partners' capital resulting from operations: {{ fmt_currency(income_statement.net_increase_from_operations.adjusted) }}")
    doc.add_paragraph()

    _add_heading(doc, "Schedule of Investments", size=13)
    _add_tag_paragraph(
        doc,
        "{% if statements_present.schedule_of_investments %}(schedule omitted for brevity){% else %}"
        "This fund does not maintain a security-level Schedule of Investments.{% endif %}",
    )
    doc.add_paragraph()

    _add_heading(doc, "Notes to Financial Statements", size=13)
    _add_tag_paragraph(doc, "Credit facility outstanding balance: {{ fmt_currency(notes.credit_facility_outstanding) }}")
    _add_tag_paragraph(doc, "Interest rate on credit facility: {{ notes.credit_facility_rate }}")

    doc.add_paragraph()
    _add_tag_paragraph(doc, "Report generated {{ generated_date }}", size=8, italic=True)

    out_path = TEMPLATES_DIR / "debt_fund_report_template.docx"
    doc.save(out_path)
    return out_path


def main():
    WORKBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    MAPPING_DIR.mkdir(parents=True, exist_ok=True)

    pe_wb = build_pe_fund_workbook()
    debt_wb = build_debt_fund_workbook()
    print(f"Wrote {pe_wb}")
    print(f"Wrote {debt_wb}")

    pe_template = build_pe_fund_template()
    debt_template = build_debt_fund_template()
    print(f"Wrote {pe_template}")
    print(f"Wrote {debt_template}")

    pe_mapping_path = MAPPING_DIR / "alpha_pe_fund_i_mapping.json"
    debt_mapping_path = MAPPING_DIR / "beta_debt_fund_ii_mapping.json"
    pe_mapping_path.write_text(json.dumps(pe_fund_mapping_config(), indent=2))
    debt_mapping_path.write_text(json.dumps(debt_fund_mapping_config(), indent=2))
    print(f"Wrote {pe_mapping_path}")
    print(f"Wrote {debt_mapping_path}")


if __name__ == "__main__":
    main()
