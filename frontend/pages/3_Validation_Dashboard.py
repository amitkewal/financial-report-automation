import streamlit as st

from api_client import api_get, api_post, current_user, require_login

st.set_page_config(page_title="Validation Dashboard", layout="wide")
require_login()
user = current_user()

st.title("Validation Dashboard")
st.caption(
    "Re-runs every cross-check that applies to this fund (BS ties to PCAP, IS net income ties to SCPC, "
    "CF ties to BS, SOI ties to BS investments, etc). Checks referencing a statement this fund doesn't "
    "have are reported as SKIPPED, not FAIL."
)

STATUS_ICON = {"pass": "✅", "fail": "❌", "warning": "⚠️", "skipped": "⏭️"}

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
    st.info("No workbook uploaded for this period yet. Use the Upload & Mapping page.")
    st.stop()
workbook = st.selectbox("Workbook", workbooks, format_func=lambda x: f"#{x['id']} - {x['filename']}")

if user["role"] != "reviewer" and st.button("Run validation now", type="primary"):
    api_post(f"/workbooks/{workbook['id']}/validate")
    st.rerun()

checks = api_get(f"/workbooks/{workbook['id']}/validation") or []
if not checks:
    st.info("No validation results yet. Click 'Run validation now'.")
    st.stop()

passed = sum(1 for c in checks if c["status"] == "pass")
failed = [c for c in checks if c["status"] == "fail"]
warnings = sum(1 for c in checks if c["status"] == "warning")
skipped = sum(1 for c in checks if c["status"] == "skipped")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Passed", passed)
c2.metric("Failed", len(failed))
c3.metric("Warnings", warnings)
c4.metric("Skipped (not applicable)", skipped)

if failed and not all(c["is_overridden"] for c in failed):
    st.error("Report generation is BLOCKED until every failing check passes or is overridden with a documented justification.")
elif failed:
    st.warning("All failing checks have been overridden with a documented justification. Report generation is unblocked.")
else:
    st.success("All checks pass (or are not applicable to this fund). Ready to generate a draft report.")

for check in checks:
    icon = STATUS_ICON.get(check["status"], "")
    with st.expander(f"{icon} [{check['status'].upper()}] {check['name']}"):
        st.write(f"Statement: `{check['statement']}`")
        st.write(f"Expected (right-hand side): {check['expected_value']}")
        st.write(f"Actual (left-hand side): {check['actual_value']}")
        st.write(f"Difference: {check['difference']}")
        if check["message"]:
            st.write(check["message"])
        if check["is_overridden"]:
            st.info(f"Overridden: {check['override_comment']}")
        elif check["status"] == "fail" and user["role"] in ("reviewer", "admin"):
            comment = st.text_input("Override justification (required)", key=f"override_{check['id']}")
            if st.button("Override this check", key=f"override_btn_{check['id']}") and comment:
                api_post(f"/validation-checks/{check['id']}/override", json={"comment": comment})
                st.success("Check overridden")
                st.rerun()
