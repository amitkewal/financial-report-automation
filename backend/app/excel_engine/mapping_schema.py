"""Shape of a per-fund mapping config, plus the path resolver shared by the
extractor and validator.

A mapping config is a plain JSON-serializable dict (stored as-is in
MappingConfig.config_json) shaped like:

{
  "statements": {
    "<canonical_statement_key>": {
      "present": true,
      "sheet_name": "BS Lead",
      "type": "line_items" | "table" | "notes",

      # type == "line_items"
      "columns": {"unadjusted": "C", "adjustments": "D", "adjusted": "E", "prior_year": "F"},
      "line_items": [
        {"key": "total_assets", "label": "Total Assets", "row": 25,
         "is_subtotal": false, "is_total": true}
      ],

      # type == "table" (e.g. Schedule of Investments)
      "table": {
        "start_row": 10, "end_row": 40,
        "columns": {"security_name": "B", "region": "C", "cost": "D",
                    "fair_value": "E", "pct_of_total": "F"},
        "total_row": 41
      },

      # type == "notes"
      "notes_items": [
        {"key": "due_to_affiliates", "label": "Due to affiliates", "row": 12,
         "column": "D", "value_type": "number"}
      ]
    },
    ...
  },
  "cross_checks": [
    {
      "name": "Balance Sheet ties to Statement of Changes in Partners' Capital",
      "left": "balance_sheet.total_partners_capital.adjusted",
      "right": "statement_of_changes_in_partners_capital.ending_capital.total",
      "tolerance": 0.01,
      "applies_if_present": ["balance_sheet", "statement_of_changes_in_partners_capital"]
    }
  ]
}

Statements not applicable to a fund are simply marked `"present": false`
(or omitted) — every downstream stage (extraction, validation, template
rendering) skips them instead of assuming a fixed set exists.
"""

CANONICAL_STATEMENTS = [
    "balance_sheet",
    "income_statement",
    "schedule_of_investments",
    "statement_of_changes_in_partners_capital",
    "statement_of_cash_flows",
    "notes",
]

STATEMENT_LABELS = {
    "balance_sheet": "Statement of Assets, Liabilities & Partners' Capital",
    "income_statement": "Statement of Operations",
    "schedule_of_investments": "Schedule of Investments",
    "statement_of_changes_in_partners_capital": "Statement of Changes in Partners' Capital",
    "statement_of_cash_flows": "Statement of Cash Flows",
    "notes": "Notes to Financial Statements",
}


def resolve_path(extracted_data: dict, path: str):
    """Resolve a dotted path against extracted data.

    Supports a `sum:` prefix to total a table field across rows, e.g.
    `sum:schedule_of_investments.rows.fair_value`.
    Returns None if any segment along the path is missing (a statement not
    present for this fund, a key not extracted, etc.) so callers can treat
    that as "not applicable" rather than crashing.
    """
    if path.startswith("sum:"):
        stmt_key, _, field = path[4:].partition(".rows.")
        stmt = extracted_data.get(stmt_key)
        if not stmt or "rows" not in stmt:
            return None
        values = [r.get(field) for r in stmt["rows"] if isinstance(r.get(field), (int, float))]
        return sum(values) if values else None

    node = extracted_data
    for segment in path.split("."):
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    if isinstance(node, (int, float)):
        return float(node)
    return node
