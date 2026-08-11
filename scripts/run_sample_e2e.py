"""End-to-end demo run against a live backend: drives the full pipeline for
both sample funds (Alpha PE Fund I -> WITH an SOI, Beta Debt Fund II ->
WITHOUT one) through the real REST API, exactly as a Preparer/Reviewer would
via the UI. Produces a FINAL .docx and .pdf for each fund.

Usage:
    uvicorn app.main:app &          # from backend/, with FRA_ADMIN_* env vars set if desired
    python scripts/run_sample_e2e.py [--base-url http://127.0.0.1:8000]
"""

import argparse
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "sample_data"
OUTPUT_DIR = ROOT / "sample_data" / "output"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "ChangeMe123!"


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def login(self, email: str, password: str):
        resp = self.session.post(f"{self.base_url}/auth/login", json={"email": email, "password": password})
        resp.raise_for_status()
        token = resp.json()["access_token"]
        self.session.headers["Authorization"] = f"Bearer {token}"
        return resp.json()["user"]

    def post(self, path: str, **kwargs):
        resp = self.session.post(f"{self.base_url}{path}", **kwargs)
        if not resp.ok:
            print("ERROR", path, resp.status_code, resp.text, file=sys.stderr)
        resp.raise_for_status()
        return resp

    def get(self, path: str, **kwargs):
        resp = self.session.get(f"{self.base_url}{path}", **kwargs)
        resp.raise_for_status()
        return resp


def run_fund_pipeline(
    admin: ApiClient,
    preparer: ApiClient,
    reviewer: ApiClient,
    client_id: int,
    fund_name: str,
    fund_short_code: str,
    fund_type: str,
    workbook_path: Path,
    template_path: Path,
    mapping_config: dict,
    period_label: str,
):
    print(f"\n=== {fund_name} ===")

    fund = preparer.post(
        f"/clients/{client_id}/funds",
        json={
            "legal_name": fund_name,
            "short_code": fund_short_code,
            "fund_type": fund_type,
            "fiscal_year_end": "12-31",
            "currency": "USD",
        },
    ).json()
    fund_id = fund["id"]
    print(f"Created fund #{fund_id}")

    with open(template_path, "rb") as f:
        template = preparer.post(
            f"/funds/{fund_id}/templates", files={"file": (template_path.name, f, "application/octet-stream")}
        ).json()
    print(f"Uploaded template v{template['version']}")

    infer_result = None
    with open(workbook_path, "rb") as f:
        infer_result = preparer.post(
            f"/funds/{fund_id}/mapping/infer", files={"file": (workbook_path.name, f, "application/octet-stream")}
        ).json()
    print(f"Auto-detected {len(infer_result['sheet_names'])} sheets, {len(infer_result['warnings'])} warnings")

    mapping = preparer.post(
        f"/funds/{fund_id}/mapping", json={"config_json": mapping_config, "status": "confirmed"}
    ).json()
    print(f"Confirmed mapping config v{mapping['version']}")

    period = preparer.post(f"/funds/{fund_id}/periods", json={"period_label": period_label}).json()
    period_id = period["id"]

    with open(workbook_path, "rb") as f:
        workbook = preparer.post(
            f"/funds/{fund_id}/periods/{period_id}/workbooks",
            files={"file": (workbook_path.name, f, "application/octet-stream")},
        ).json()
    workbook_id = workbook["id"]
    print(f"Uploaded workbook #{workbook_id}")

    checks = preparer.post(f"/workbooks/{workbook_id}/validate").json()
    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = [c for c in checks if c["status"] == "fail"]
    skipped = sum(1 for c in checks if c["status"] == "skipped")
    print(f"Validation: {passed} passed, {len(failed)} failed, {skipped} skipped (of {len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status'].upper():8}] {c['name']}")

    run = preparer.post("/report-runs", json={"workbook_id": workbook_id, "template_id": template["id"]}).json()
    run_id = run["id"]

    run = preparer.post(f"/report-runs/{run_id}/generate-draft").json()
    print(f"Draft generated -> status={run['status']}")

    run = preparer.post(f"/report-runs/{run_id}/submit-review", json={"comment": "Ready for review"}).json()
    print(f"Submitted for review -> status={run['status']}")

    run = reviewer.post(f"/report-runs/{run_id}/approve", json={"comment": "Looks good, approved."}).json()
    print(f"Approved by reviewer -> status={run['status']}")

    run = reviewer.post(f"/report-runs/{run_id}/publish-final").json()
    print(f"Published final -> status={run['status']}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    docx_resp = preparer.get(f"/report-runs/{run_id}/download/final-docx")
    docx_out = OUTPUT_DIR / f"{fund_short_code}_FINAL.docx"
    docx_out.write_bytes(docx_resp.content)

    pdf_resp = preparer.get(f"/report-runs/{run_id}/download/final-pdf")
    pdf_out = OUTPUT_DIR / f"{fund_short_code}_FINAL.pdf"
    pdf_out.write_bytes(pdf_resp.content)

    print(f"Saved {docx_out.relative_to(ROOT)} and {pdf_out.relative_to(ROOT)}")
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_sample_data import pe_fund_mapping_config, debt_fund_mapping_config  # noqa: E402

    admin = ApiClient(args.base_url)
    for attempt in range(10):
        try:
            admin.login(ADMIN_EMAIL, ADMIN_PASSWORD)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        print("Could not reach backend. Is uvicorn running?", file=sys.stderr)
        sys.exit(1)
    print("Logged in as admin")

    preparer_email = "preparer@example.com"
    reviewer_email = "reviewer@example.com"
    password = "SamplePass123!"
    try:
        admin.post("/auth/users", json={"email": preparer_email, "full_name": "Priya Preparer", "password": password, "role": "preparer"})
    except requests.exceptions.HTTPError:
        pass
    try:
        admin.post("/auth/users", json={"email": reviewer_email, "full_name": "Raj Reviewer", "password": password, "role": "reviewer"})
    except requests.exceptions.HTTPError:
        pass
    print("Ensured preparer/reviewer users exist")

    preparer = ApiClient(args.base_url)
    preparer.login(preparer_email, password)
    reviewer = ApiClient(args.base_url)
    reviewer.login(reviewer_email, password)

    client = admin.post("/clients", json={"name": "Sample Capital Partners", "onshore_team": "NY Team", "offshore_team": "Bangalore Team"}).json()
    client_id = client["id"]
    print(f"Created client #{client_id}: {client['name']}")

    users = admin.get("/auth/users").json()
    for u in users:
        if u["email"] in (preparer_email, reviewer_email):
            admin.post("/auth/grant-client-access", json={"user_id": u["id"], "client_id": client_id})
    print("Granted client access to preparer and reviewer")

    run_fund_pipeline(
        admin,
        preparer,
        reviewer,
        client_id,
        fund_name="Alpha PE Fund I",
        fund_short_code="ALPHA1",
        fund_type="private_equity",
        workbook_path=SAMPLE_DIR / "workbooks" / "Alpha_PE_Fund_I_2025Q4_NAV_Pack.xlsx",
        template_path=SAMPLE_DIR / "templates" / "pe_fund_report_template.docx",
        mapping_config=pe_fund_mapping_config(),
        period_label="2025-Q4",
    )

    run_fund_pipeline(
        admin,
        preparer,
        reviewer,
        client_id,
        fund_name="Beta Debt Fund II",
        fund_short_code="BETA2",
        fund_type="debt",
        workbook_path=SAMPLE_DIR / "workbooks" / "Beta_Debt_Fund_II_2025Q4_NAV_Pack.xlsx",
        template_path=SAMPLE_DIR / "templates" / "debt_fund_report_template.docx",
        mapping_config=debt_fund_mapping_config(),
        period_label="2025-Q4",
    )

    print("\nEnd-to-end run complete for both funds.")


if __name__ == "__main__":
    main()
