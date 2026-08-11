"""Merges validated, extracted fund data into that fund's own Word template
using docxtpl (Jinja2-in-docx). Templates use standard Jinja syntax:

  {{ fund_name }}                              simple placeholder
  {{ balance_sheet.total_assets.adjusted }}    nested statement/line-item/column
  {% if statements_present.schedule_of_investments %} ... {% endif %}   conditional section
  {%tr for row in schedule_of_investments_rows %} ... {%tr endfor %}   repeating table row (docxtpl table-row tag)
  {{ fmt_currency(balance_sheet.total_assets.adjusted) }}              financial formatting

Statements not present for a fund are simply absent from the context, so a
template can safely gate an entire section behind `statements_present.X`.
"""

from datetime import datetime, timezone
from pathlib import Path

from docxtpl import DocxTemplate
from jinja2 import Environment

from app.report_engine.formatting import fmt_currency, fmt_date, fmt_number, fmt_percent


def build_context(fund, client, period, config: dict, extracted_data: dict) -> dict:
    statements_present = {
        key: bool(cfg.get("present")) for key, cfg in config.get("statements", {}).items()
    }

    context: dict = {
        "client_name": client.name,
        "fund_name": fund.legal_name,
        "fund_short_code": fund.short_code,
        "fund_type": getattr(fund.fund_type, "value", fund.fund_type),
        "currency": fund.currency,
        "period_label": period.period_label,
        "period_end_date": period.period_end_date,
        "statements_present": statements_present,
        "generated_date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
    }

    for statement_key, data in extracted_data.items():
        if not isinstance(data, dict) or "error" in data:
            continue
        statement_cfg = config.get("statements", {}).get(statement_key, {})
        if statement_cfg.get("type") == "table":
            context[f"{statement_key}_rows"] = data.get("rows", [])
            context[f"{statement_key}_totals"] = data.get("totals", {})
        else:
            context[statement_key] = data

    return context


def render_report(template_path: str, context: dict, output_path: str) -> str:
    doc = DocxTemplate(template_path)
    jinja_env = Environment(autoescape=False)
    jinja_env.filters["fmt_currency"] = fmt_currency
    jinja_env.filters["fmt_number"] = fmt_number
    jinja_env.filters["fmt_percent"] = fmt_percent
    jinja_env.filters["fmt_date"] = fmt_date

    render_context = dict(context)
    render_context.update(
        fmt_currency=fmt_currency,
        fmt_number=fmt_number,
        fmt_percent=fmt_percent,
        fmt_date=fmt_date,
    )

    doc.render(render_context, jinja_env)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path
