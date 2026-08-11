import streamlit as st

from api_client import api_get, require_login

st.set_page_config(page_title="History & Downloads", layout="wide")
require_login()

st.title("Report Run History")
st.caption("Search and filter every report run this user has access to, across all clients, funds, and periods.")

clients = api_get("/clients") or []
client_options = {"All clients": None} | {c["name"]: c["id"] for c in clients}
client_label = st.selectbox("Client", list(client_options.keys()))
client_id = client_options[client_label]

fund_id = None
if client_id:
    funds = api_get(f"/clients/{client_id}/funds") or []
    fund_options = {"All funds": None} | {f"{f['legal_name']} ({f['short_code']})": f["id"] for f in funds}
    fund_label = st.selectbox("Fund", list(fund_options.keys()))
    fund_id = fund_options[fund_label]

status_options = [
    "All statuses",
    "uploaded",
    "validated",
    "validation_failed",
    "draft_generated",
    "in_review",
    "changes_requested",
    "approved",
    "final_published",
]
status = st.selectbox("Status", status_options)

params = []
if client_id:
    params.append(f"client_id={client_id}")
if fund_id:
    params.append(f"fund_id={fund_id}")
if status != "All statuses":
    params.append(f"status={status}")
query = "?" + "&".join(params) if params else ""

runs = api_get(f"/report-runs{query}") or []

if not runs:
    st.info("No report runs match these filters.")
else:
    st.table(
        [
            {
                "run_id": r["id"],
                "fund_id": r["fund_id"],
                "period_id": r["period_id"],
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "has_final": bool(r.get("final_pdf_path")),
            }
            for r in runs
        ]
    )

    selected_id = st.number_input("Enter a run ID to download its outputs", min_value=0, step=1)
    if selected_id:
        matching = [r for r in runs if r["id"] == selected_id]
        if matching:
            run = matching[0]
            c1, c2, c3 = st.columns(3)
            if run.get("draft_docx_path"):
                data = api_get(f"/report-runs/{run['id']}/download/draft")
                c1.download_button("Draft .docx", data, file_name=f"run_{run['id']}_draft.docx")
            if run.get("final_docx_path"):
                data = api_get(f"/report-runs/{run['id']}/download/final-docx")
                c2.download_button("Final .docx", data, file_name=f"run_{run['id']}_FINAL.docx")
            if run.get("final_pdf_path"):
                data = api_get(f"/report-runs/{run['id']}/download/final-pdf")
                c3.download_button("Final .pdf", data, file_name=f"run_{run['id']}_FINAL.pdf")
        else:
            st.warning("No run with that ID in the current filtered results.")
