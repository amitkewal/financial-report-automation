"""Drives the real-data-grounded BDC fixture (see generate_real_fund_data.py)
through the full platform pipeline via the live REST API - upload, mapping
confirmation, validation, draft, review, approval, and final publication -
exactly like scripts/run_sample_e2e.py does for the two synthetic funds,
but as a standalone script so it doesn't disturb that already-verified flow.

Usage:
    uvicorn app.main:app &
    python scripts/generate_real_fund_data.py
    python scripts/run_real_fund_e2e.py [--base-url http://127.0.0.1:8000]
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_real_fund_data import mapping_config  # noqa: E402

    admin = ApiClient(args.base_url)
    for _ in range(10):
        try:
            admin.login(ADMIN_EMAIL, ADMIN_PASSWORD)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        print("Could not reach backend. Is uvicorn running?", file=sys.stderr)
        sys.exit(1)
    print("Logged in as admin")

    preparer_email, reviewer_email, password = "preparer@example.com", "reviewer@example.com", "SamplePass123!"
    for email, role in ((preparer_email, "preparer"), (reviewer_email, "reviewer")):
        try:
            admin.post("/auth/users", json={"email": email, "full_name": email.split("@")[0].title(), "password": password, "role": role})
        except requests.exceptions.HTTPError:
            pass  # already exists

    preparer = ApiClient(args.base_url)
    preparer.login(preparer_email, password)
    reviewer = ApiClient(args.base_url)
    reviewer.login(reviewer_email, password)

    client = admin.post(
        "/clients",
        json={
            "name": "Public BDC Test Cases (real-data-grounded)",
            "notes": "Funds here use figures sourced from real public filings for platform testing - see scripts/generate_real_fund_data.py for provenance.",
        },
    ).json()
    client_id = client["id"]
    print(f"Created client #{client_id}: {client['name']}")

    users = admin.get("/auth/users").json()
    for u in users:
        if u["email"] in (preparer_email, reviewer_email):
            admin.post("/auth/grant-client-access", json={"user_id": u["id"], "client_id": client_id})

    fund = preparer.post(
        f"/clients/{client_id}/funds",
        json={
            "legal_name": "Investcorp Credit Management BDC, Inc.",
            "short_code": "ICMB",
            "fund_type": "debt",
            "fiscal_year_end": "12-31",
            "currency": "USD",
        },
    ).json()
    fund_id = fund["id"]
    print(f"Created fund #{fund_id}: {fund['legal_name']}")

    template_path = SAMPLE_DIR / "templates" / "real_bdc_report_template.docx"
    with open(template_path, "rb") as f:
        template = preparer.post(f"/funds/{fund_id}/templates", files={"file": (template_path.name, f)}).json()
    print(f"Uploaded template v{template['version']}")

    workbook_path = SAMPLE_DIR / "workbooks" / "Investcorp_Credit_Management_BDC_2025_NAV_Pack.xlsx"
    with open(workbook_path, "rb") as f:
        infer_result = preparer.post(f"/funds/{fund_id}/mapping/infer", files={"file": (workbook_path.name, f)}).json()
    print(f"Auto-detected {len(infer_result['sheet_names'])} sheets, {len(infer_result['warnings'])} warnings")

    mapping = preparer.post(f"/funds/{fund_id}/mapping", json={"config_json": mapping_config(), "status": "confirmed"}).json()
    print(f"Confirmed mapping config v{mapping['version']}")

    period = preparer.post(f"/funds/{fund_id}/periods", json={"period_label": "2025-FY", "period_end_date": "2025-12-31"}).json()
    period_id = period["id"]

    with open(workbook_path, "rb") as f:
        workbook = preparer.post(
            f"/funds/{fund_id}/periods/{period_id}/workbooks", files={"file": (workbook_path.name, f)}
        ).json()
    workbook_id = workbook["id"]
    print(f"Uploaded workbook #{workbook_id}")

    checks = preparer.post(f"/workbooks/{workbook_id}/validate").json()
    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = [c for c in checks if c["status"] == "fail"]
    print(f"Validation: {passed} passed, {len(failed)} failed (of {len(checks)} checks)")
    for c in checks:
        print(f"  [{c['status'].upper():8}] {c['name']}")
    if failed:
        print("Aborting: failing checks present.", file=sys.stderr)
        sys.exit(1)

    run = preparer.post("/report-runs", json={"workbook_id": workbook_id, "template_id": template["id"]}).json()
    run_id = run["id"]

    run = preparer.post(f"/report-runs/{run_id}/generate-draft").json()
    print(f"Draft generated -> status={run['status']}")
    run = preparer.post(f"/report-runs/{run_id}/submit-review", json={"comment": "Ready for review"}).json()
    print(f"Submitted for review -> status={run['status']}")
    run = reviewer.post(f"/report-runs/{run_id}/approve", json={"comment": "Approved - real-data test fixture."}).json()
    print(f"Approved by reviewer -> status={run['status']}")
    run = reviewer.post(f"/report-runs/{run_id}/publish-final").json()
    print(f"Published final -> status={run['status']}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    docx_out = OUTPUT_DIR / "ICMB_FINAL.docx"
    docx_out.write_bytes(preparer.get(f"/report-runs/{run_id}/download/final-docx").content)
    pdf_out = OUTPUT_DIR / "ICMB_FINAL.pdf"
    pdf_out.write_bytes(preparer.get(f"/report-runs/{run_id}/download/final-pdf").content)
    print(f"Saved {docx_out.relative_to(ROOT)} and {pdf_out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
