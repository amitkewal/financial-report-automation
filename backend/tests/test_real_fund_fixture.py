"""Tests for the real-data-grounded BDC fixture (see
scripts/generate_real_fund_data.py). This fund uses a genuinely different
mapping structure from the two synthetic funds - single net-asset column
instead of GP/LP, current/prior-year instead of unadjusted/adjustments/
adjusted - proving the mapping config's `columns` field is truly per-fund,
not just a variation on one hardcoded layout.
"""

import json
from pathlib import Path

import pytest

from app.excel_engine.extractor import extract_workbook
from app.excel_engine.validator import run_validation

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"


@pytest.fixture(scope="module")
def config():
    return json.loads((SAMPLE_DIR / "mapping_configs" / "investcorp_credit_management_bdc_mapping.json").read_text())


@pytest.fixture(scope="module")
def workbook_path():
    return str(SAMPLE_DIR / "workbooks" / "Investcorp_Credit_Management_BDC_2025_NAV_Pack.xlsx")


@pytest.fixture(scope="module")
def data(workbook_path, config):
    return extract_workbook(workbook_path, config)


def test_total_assets_matches_real_reported_figure(data):
    # REAL: ICMB reported total assets of $188.8M as of 12/31/2025.
    assert data["balance_sheet"]["total_assets"]["current_year"] == 188_800_000


def test_net_assets_matches_real_reported_figure(data):
    # REAL: ICMB reported net assets of $61.3M as of 12/31/2025.
    assert data["balance_sheet"]["net_assets"]["current_year"] == 61_300_000


def test_credit_facility_matches_real_reported_figure(data):
    # REAL: Capital One facility, $58.9M drawn as of 12/31/2025.
    assert data["balance_sheet"]["credit_facility_payable"]["current_year"] == 58_900_000


def test_net_decrease_from_operations_matches_real_reported_figure(data):
    # REAL: ICMB reported a net decrease in net assets from operations of $8.848M for FY2025.
    assert data["income_statement"]["net_increase_from_operations"]["current_year"] == -8_848_000


def test_soi_includes_real_named_top_holdings(data):
    names = {row["security_name"] for row in data["schedule_of_investments"]["rows"]}
    for real_holding in ("Bioplan", "WorkGenius", "Klein Hersh", "Xenon Arc", "ArborWorks", "Crafty Apes", "Argano", "LaserAway"):
        assert real_holding in names


def test_soi_fair_value_total_matches_real_reported_portfolio_value(data):
    # REAL: ICMB reported a $172.7M investment portfolio at fair value as of 12/31/2025.
    assert data["schedule_of_investments"]["totals"]["fair_value"] == 172_700_000


def test_all_cross_checks_pass(data, config):
    results = run_validation(data, config)
    assert len(results) == 7
    assert all(r["status"] == "pass" for r in results)


def test_uses_single_column_net_assets_not_gp_lp_split(config):
    # A public BDC has common shareholders, not GP/LP partners - a different
    # capital-structure shape from both synthetic sample funds.
    scpc_columns = config["statements"]["statement_of_changes_in_partners_capital"]["columns"]
    assert set(scpc_columns.keys()) == {"amount"}


def test_uses_current_prior_year_columns_not_unadjusted_adjusted(config):
    bs_columns = config["statements"]["balance_sheet"]["columns"]
    assert set(bs_columns.keys()) == {"current_year", "prior_year"}
