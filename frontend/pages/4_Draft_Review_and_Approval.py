import streamlit as st

from api_client import api_get, api_post, current_user, require_login

st.set_page_config(page_title="Draft Review & Approval", layout="wide")
require_login()
user = current_user()

st.title("Draft Review & Approval")
st.caption(
    "Pipeline: Uploaded -> Validated -> Draft Generated -> In Review -> Approved -> Final Published. "
    "Only an Approver (Reviewer/Admin role) can publish the final .docx/.pdf."
)

clients = api_get("/clients") or []
if not clients:
    st.stop()
client = st.selectbox("Client", clients, format_func=lambda x: x["name"])
funds = api_get(f"/clients/{client['id']}/funds") or []
if not funds:
    st.stop()
fund = st.selectbox("Fund", funds, format_func=lambda x: f"{x['legal_name']} ({x['short_code']})")
periods = api_get(f"/funds/{fund['id']}/periods") or []
if not periods:
    st.stop()
period = st.selectbox("Period", periods, format_func=lambda x: x["period_label"])
workbooks = api_get(f"/funds/{fund['id']}/periods/{period['id']}/workbooks") or []
if not workbooks:
    st.info("No workbook uploaded for this period yet.")
    st.stop()
workbook = st.selectbox("Workbook", workbooks, format_func=lambda x: f"#{x['id']} - {x['filename']}")

all_runs = api_get(f"/report-runs?fund_id={fund['id']}&period_id={period['id']}") or []
runs_for_workbook = [r for r in all_runs if r["workbook_id"] == workbook["id"]]

if not runs_for_workbook:
    st.subheader("Start a report run")
    templates = api_get(f"/funds/{fund['id']}/templates") or []
    if not templates:
        st.warning("Upload a Word template for this fund first (Clients & Funds page).")
        st.stop()
    template = st.selectbox("Template", templates, format_func=lambda x: f"v{x['version']} - {x['filename']}")
    if user["role"] != "reviewer" and st.button("Create report run"):
        api_post("/report-runs", json={"workbook_id": workbook["id"], "template_id": template["id"]})
        st.rerun()
    st.stop()

run = runs_for_workbook[0]
run_id = run["id"]

status_labels = {
    "uploaded": "1. Uploaded",
    "validated": "2. Validated",
    "validation_failed": "2. Validation Failed",
    "draft_generated": "3. Draft Generated",
    "in_review": "4. In Review",
    "changes_requested": "4. Changes Requested",
    "approved": "5. Approved",
    "final_published": "6. Final Published",
}
st.subheader(f"Report Run #{run_id} — status: {status_labels.get(run['status'], run['status'])}")

col1, col2, col3, col4 = st.columns(4)

if user["role"] != "reviewer" and run["status"] in ("validated", "changes_requested"):
    if col1.button("Generate draft", type="primary"):
        api_post(f"/report-runs/{run_id}/generate-draft")
        st.rerun()
elif run["status"] == "validation_failed":
    st.error("This workbook has failing checks. Fix or override them on the Validation Dashboard first.")

if run.get("draft_docx_path"):
    draft_bytes = api_get(f"/report-runs/{run_id}/download/draft")
    col2.download_button("Download draft .docx", draft_bytes, file_name=f"{fund['short_code']}_draft.docx")

if user["role"] != "reviewer" and run["status"] == "draft_generated":
    if col3.button("Submit for review"):
        api_post(f"/report-runs/{run_id}/submit-review", json={"comment": None})
        st.rerun()

if user["role"] in ("reviewer", "admin") and run["status"] == "in_review":
    comment = st.text_input("Reviewer comment", key=f"comment_{run_id}")
    c1, c2 = st.columns(2)
    if c1.button("Approve", type="primary"):
        api_post(f"/report-runs/{run_id}/approve", json={"comment": comment or None})
        st.rerun()
    if c2.button("Request changes"):
        if not comment:
            st.error("A comment is required when requesting changes.")
        else:
            api_post(f"/report-runs/{run_id}/request-changes", json={"comment": comment})
            st.rerun()

if user["role"] in ("reviewer", "admin") and run["status"] == "approved":
    if col4.button("Publish final (.docx + .pdf)", type="primary"):
        with st.spinner("Rendering final documents..."):
            api_post(f"/report-runs/{run_id}/publish-final")
        st.rerun()

if run["status"] == "final_published":
    st.success("Final report has been published.")
    d1, d2 = st.columns(2)
    docx_bytes = api_get(f"/report-runs/{run_id}/download/final-docx")
    d1.download_button("Download final .docx", docx_bytes, file_name=f"{fund['short_code']}_FINAL.docx")
    pdf_bytes = api_get(f"/report-runs/{run_id}/download/final-pdf")
    d2.download_button("Download final .pdf", pdf_bytes, file_name=f"{fund['short_code']}_FINAL.pdf")

st.divider()
st.subheader("Approval log / audit trail")
logs = api_get(f"/report-runs/{run_id}/approval-log") or []
if logs:
    st.table(
        [{"when": entry["created_at"], "action": entry["action"], "comment": entry["comment"] or ""} for entry in logs]
    )
else:
    st.write("No approval actions yet.")
