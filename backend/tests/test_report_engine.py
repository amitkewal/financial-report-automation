import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.excel_engine.extractor import extract_workbook
from app.report_engine.formatting import fmt_currency, fmt_percent
from app.report_engine.pdf_converter import convert_to_pdf
from app.report_engine.template_renderer import build_context, render_report

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"


class FakeFund:
    legal_name = "Alpha PE Fund I"
    short_code = "ALPHA1"
    fund_type = "private_equity"
    currency = "USD"


class FakeClient:
    name = "Sample Capital Partners"


class FakePeriod:
    period_label = "2025-Q4"
    period_end_date = "2025-12-31"


def test_fmt_currency_negative_uses_parentheses():
    assert fmt_currency(-1234) == "(1,234)"
    assert fmt_currency(1234) == "1,234"
    assert fmt_currency(0) == "-"
    assert fmt_currency(None) == "-"


def test_fmt_percent():
    assert fmt_percent(12.345) == "12.35%"


def test_render_pe_fund_report_to_pdf(tmp_path):
    config = json.loads((SAMPLE_DIR / "mapping_configs" / "alpha_pe_fund_i_mapping.json").read_text())
    data = extract_workbook(str(SAMPLE_DIR / "workbooks" / "Alpha_PE_Fund_I_2025Q4_NAV_Pack.xlsx"), config)
    context = build_context(FakeFund(), FakeClient(), FakePeriod(), config, data)

    docx_out = tmp_path / "draft.docx"
    render_report(str(SAMPLE_DIR / "templates" / "pe_fund_report_template.docx"), context, str(docx_out))
    assert docx_out.exists()

    pdf_path = convert_to_pdf(str(docx_out), str(tmp_path))
    reader = PdfReader(pdf_path)
    text = "\n".join(p.extract_text() for p in reader.pages)

    assert "Alpha PE Fund I" in text
    assert "91,000,000" in text  # total assets, formatted with fmt_currency
    assert "TechCo" in text  # repeating SOI table row rendered
    assert "{{" not in text  # no leftover unrendered tags
