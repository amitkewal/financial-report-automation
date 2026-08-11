import json
from pathlib import Path

import pytest

from app.excel_engine.extractor import extract_workbook
from app.excel_engine.inspector import infer_mapping, list_sheets
from app.excel_engine.mapping_schema import resolve_path
from app.excel_engine.validator import run_validation

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"


@pytest.fixture(scope="module")
def pe_config():
    return json.loads((SAMPLE_DIR / "mapping_configs" / "alpha_pe_fund_i_mapping.json").read_text())


@pytest.fixture(scope="module")
def debt_config():
    return json.loads((SAMPLE_DIR / "mapping_configs" / "beta_debt_fund_ii_mapping.json").read_text())


@pytest.fixture(scope="module")
def pe_workbook_path():
    return str(SAMPLE_DIR / "workbooks" / "Alpha_PE_Fund_I_2025Q4_NAV_Pack.xlsx")


@pytest.fixture(scope="module")
def debt_workbook_path():
    return str(SAMPLE_DIR / "workbooks" / "Beta_Debt_Fund_II_2025Q4_NAV_Pack.xlsx")


def test_debt_fund_has_no_soi_sheet(debt_workbook_path):
    sheets = list_sheets(debt_workbook_path)
    assert "SOI Lead" not in sheets
    assert "BS Lead" in sheets


def test_pe_fund_has_soi_sheet(pe_workbook_path):
    sheets = list_sheets(pe_workbook_path)
    assert "SOI Lead" in sheets


def test_extract_pe_fund_balance_sheet(pe_workbook_path, pe_config):
    data = extract_workbook(pe_workbook_path, pe_config)
    assert data["balance_sheet"]["total_assets"]["adjusted"] == 91_000_000
    assert data["balance_sheet"]["total_partners_capital"]["adjusted"] == 90_000_000


def test_extract_pe_fund_soi_table(pe_workbook_path, pe_config):
    data = extract_workbook(pe_workbook_path, pe_config)
    soi = data["schedule_of_investments"]
    assert len(soi["rows"]) == 5
    assert soi["totals"]["fair_value"] == 85_000_000


def test_extract_debt_fund_skips_absent_soi(debt_workbook_path, debt_config):
    data = extract_workbook(debt_workbook_path, debt_config)
    assert "schedule_of_investments" not in data
    assert data["balance_sheet"]["total_assets"]["adjusted"] == 48_500_000


def test_pe_fund_all_checks_pass(pe_workbook_path, pe_config):
    data = extract_workbook(pe_workbook_path, pe_config)
    results = run_validation(data, pe_config)
    assert len(results) == 6
    assert all(r["status"] == "pass" for r in results)


def test_debt_fund_has_no_soi_check_at_all(debt_workbook_path, debt_config):
    data = extract_workbook(debt_workbook_path, debt_config)
    results = run_validation(data, debt_config)
    assert len(results) == 5
    assert all(r["status"] == "pass" for r in results)
    assert not any("Schedule of Investments" in r["name"] for r in results)


def test_validation_skips_check_when_statement_not_present(pe_workbook_path, pe_config):
    data = extract_workbook(pe_workbook_path, pe_config)
    config = json.loads(json.dumps(pe_config))
    config["statements"]["schedule_of_investments"]["present"] = False
    results = run_validation(data, config)
    soi_check = next(r for r in results if "Schedule of Investments" in r["name"])
    assert soi_check["status"] == "skipped"


def test_validation_fails_on_broken_tie_out(pe_workbook_path, pe_config):
    data = extract_workbook(pe_workbook_path, pe_config)
    data["balance_sheet"]["total_assets"]["adjusted"] = 999_999_999
    results = run_validation(data, pe_config)
    bs_check = next(r for r in results if r["name"].startswith("Balance Sheet self-balances"))
    assert bs_check["status"] == "fail"


def test_resolve_path_sum_prefix():
    data = {"schedule_of_investments": {"rows": [{"fair_value": 10}, {"fair_value": 20}]}}
    assert resolve_path(data, "sum:schedule_of_investments.rows.fair_value") == 30


def test_resolve_path_missing_segment_returns_none():
    assert resolve_path({}, "balance_sheet.total_assets.adjusted") is None


def test_infer_mapping_flags_missing_soi_for_debt_fund(debt_workbook_path):
    result = infer_mapping(debt_workbook_path)
    assert result["suggested_config"]["statements"]["schedule_of_investments"]["present"] is False
    assert any("schedule_of_investments" in w for w in result["warnings"])
