import json

import streamlit as st

from api_client import api_get, api_post, current_user, require_login

st.set_page_config(page_title="Upload & Mapping", layout="wide")
require_login()
user = current_user()

st.title("Excel Mapping Configuration")
st.caption(
    "Every fund gets its own mapping config: which tabs exist, where each line item lives, "
    "and which cross-checks apply. Upload a sample workbook to auto-detect a starting point, "
    "then confirm/adjust it below before any data can be uploaded for this fund."
)

clients = api_get("/clients") or []
if not clients:
    st.info("Create a client and fund first on the Clients & Funds page.")
    st.stop()

client = st.selectbox("Client", clients, format_func=lambda x: x["name"])
funds = api_get(f"/clients/{client['id']}/funds") or []
if not funds:
    st.info("This client has no funds yet.")
    st.stop()

fund = st.selectbox("Fund", funds, format_func=lambda x: f"{x['legal_name']} ({x['short_code']})")

st.divider()
st.subheader("Step 1 — Auto-detect (optional)")
sample_file = st.file_uploader(
    "Upload a sample workbook to auto-detect sheets, columns, and candidate line items",
    type=["xlsx", "xlsm"],
    key="infer_uploader",
)
if sample_file and st.button("Run auto-detection"):
    result = api_post(f"/funds/{fund['id']}/mapping/infer", files={"file": (sample_file.name, sample_file.getvalue())})
    st.session_state["last_inference"] = result

if "last_inference" in st.session_state:
    result = st.session_state["last_inference"]
    st.write(f"Sheets found: {', '.join(result['sheet_names'])}")
    if result["warnings"]:
        st.warning("\n".join(f"- {w}" for w in result["warnings"]))
    with st.expander("Suggested config (starting point — edit in Step 2 below)"):
        st.json(result["suggested_config"])

st.divider()
st.subheader("Step 2 — Confirm the mapping config")

existing = api_get(f"/funds/{fund['id']}/mapping") or []
if existing:
    st.write("Existing versions:")
    st.table([{"version": m["version"], "status": m["status"], "created_at": m["created_at"]} for m in existing])
    default_json = json.dumps(existing[0]["config_json"], indent=2)
elif "last_inference" in st.session_state:
    default_json = json.dumps(st.session_state["last_inference"]["suggested_config"], indent=2)
else:
    default_json = json.dumps({"statements": {}, "cross_checks": []}, indent=2)

st.caption(
    "This mapping is a plain JSON document (see backend/app/excel_engine/mapping_schema.py for the full "
    "shape): which sheet backs each statement, the row/column for every line item, and the cross-check "
    "formulas that apply to this fund. A statement a fund doesn't have (e.g. no SOI for a debt fund) is "
    "simply marked `\"present\": false` and the engine skips it everywhere downstream."
)
config_text = st.text_area("Mapping config JSON", value=default_json, height=450, key=f"mapping_json_{fund['id']}")

if user["role"] != "reviewer":
    col1, col2 = st.columns(2)
    if col1.button("Save as draft"):
        try:
            parsed = json.loads(config_text)
            api_post(f"/funds/{fund['id']}/mapping", json={"config_json": parsed, "status": "draft"})
            st.success("Saved draft mapping config")
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
    if col2.button("Confirm mapping (required before uploading workbooks)"):
        try:
            parsed = json.loads(config_text)
            api_post(f"/funds/{fund['id']}/mapping", json={"config_json": parsed, "status": "confirmed"})
            st.success("Mapping confirmed. You can now upload workbooks for this fund.")
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")

st.divider()
st.subheader("Step 3 — Upload a period's workbook")

periods = api_get(f"/funds/{fund['id']}/periods") or []
if not periods:
    st.info("Add a period for this fund on the Clients & Funds page first.")
    st.stop()

period = st.selectbox("Period", periods, format_func=lambda x: x["period_label"])
workbook_file = st.file_uploader("Upload the NAV pack / leadsheet workbook (.xlsx)", type=["xlsx", "xlsm"], key="wb_uploader")
if user["role"] != "reviewer" and workbook_file and st.button("Upload workbook"):
    result = api_post(
        f"/funds/{fund['id']}/periods/{period['id']}/workbooks",
        files={"file": (workbook_file.name, workbook_file.getvalue())},
    )
    if result:
        st.success(f"Uploaded workbook #{result['id']}. Go to the Validation Dashboard to run cross-checks.")

workbooks = api_get(f"/funds/{fund['id']}/periods/{period['id']}/workbooks") or []
if workbooks:
    st.write("Uploaded workbooks for this period:")
    st.table([{"id": w["id"], "filename": w["filename"], "uploaded_at": w["uploaded_at"]} for w in workbooks])
