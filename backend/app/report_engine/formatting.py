"""Standard audited-financial-statement style formatting helpers, exposed
into the docxtpl Jinja context so templates can call them directly, e.g.
`{{ fmt_currency(total_assets) }}`.
"""


def fmt_currency(value, decimals: int = 0) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == 0:
        return "-"
    formatted = f"{abs(number):,.{decimals}f}"
    return f"({formatted})" if number < 0 else formatted


def fmt_number(value, decimals: int = 0) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    formatted = f"{abs(number):,.{decimals}f}"
    return f"({formatted})" if number < 0 else formatted


def fmt_percent(value, decimals: int = 2) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.{decimals}f}%"


def fmt_date(value, fmt: str = "%B %d, %Y") -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime(fmt)
    return str(value)
