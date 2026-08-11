"""Cross-check validation: re-runs each fund's applicable tie-out checks
(e.g. "BS ties to PCAP") against freshly extracted data. Checks whose
`applies_if_present` statements aren't present for this fund are reported
as SKIPPED rather than FAIL, so a debt fund without an SOI check doesn't
show a false failure.
"""

from app.excel_engine.mapping_schema import resolve_path

DEFAULT_TOLERANCE = 0.01


def run_validation(extracted_data: dict, config: dict) -> list[dict]:
    present_statements = {
        key for key, cfg in config.get("statements", {}).items() if cfg.get("present")
    }
    results = []
    for check in config.get("cross_checks", []):
        name = check["name"]
        applies_if_present = check.get("applies_if_present", [])
        if applies_if_present and not set(applies_if_present).issubset(present_statements):
            results.append(
                {
                    "name": name,
                    "statement": check.get("statement") or (applies_if_present[0] if applies_if_present else None),
                    "status": "skipped",
                    "expected_value": None,
                    "actual_value": None,
                    "difference": None,
                    "message": "Not applicable: one or more referenced statements are not present for this fund.",
                }
            )
            continue

        left = resolve_path(extracted_data, check["left"])
        right = resolve_path(extracted_data, check["right"])
        tolerance = check.get("tolerance", DEFAULT_TOLERANCE)
        statement = check.get("statement") or check["left"].split(".")[0]

        if left is None or right is None:
            results.append(
                {
                    "name": name,
                    "statement": statement,
                    "status": "warning",
                    "expected_value": right,
                    "actual_value": left,
                    "difference": None,
                    "message": "One or both values could not be resolved from the workbook.",
                }
            )
            continue

        difference = round(left - right, 6)
        status = "pass" if abs(difference) <= tolerance else "fail"
        results.append(
            {
                "name": name,
                "statement": statement,
                "status": status,
                "expected_value": right,
                "actual_value": left,
                "difference": difference,
                "message": None if status == "pass" else f"Difference of {difference:,.2f} exceeds tolerance {tolerance}.",
            }
        )
    return results
