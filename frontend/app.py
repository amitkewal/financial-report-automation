import streamlit as st

from api_client import DEFAULT_BASE_URL, current_user, is_logged_in, login, logout

st.set_page_config(page_title="Financial Report Automation", page_icon=":bar_chart:", layout="wide")

st.title("Multi-Client Financial Report Automation Platform")

with st.sidebar:
    st.subheader("Backend connection")
    st.session_state.setdefault("api_base_url", DEFAULT_BASE_URL)
    st.session_state["api_base_url"] = st.text_input("API base URL", value=st.session_state["api_base_url"])

if is_logged_in():
    user = current_user()
    st.success(f"Logged in as **{user['full_name']}** ({user['email']}) — role: **{user['role']}**")
    if st.button("Log out"):
        logout()
        st.rerun()

    st.markdown(
        """
### Navigate using the sidebar pages:

1. **Clients & Funds** — set up clients, funds, and Word report templates
2. **Upload & Mapping** — upload a fund's workbook and confirm its Excel mapping config
3. **Validation Dashboard** — re-run cross-checks and review PASS/FAIL/WARNING results
4. **Draft Review & Approval** — generate drafts, submit for review, approve, and publish final reports
5. **History & Downloads** — search past runs across every client/fund/period and download outputs

Each fund can have a completely different set of statements and cross-checks
— a debt fund with no Schedule of Investments is handled exactly like a
private equity fund with one, without any code changes.
"""
    )
else:
    st.subheader("Log in")
    with st.form("login_form"):
        email = st.text_input("Email", value="admin@example.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
        if submitted:
            try:
                user = login(email, password)
                st.success(f"Welcome, {user['full_name']}!")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Login failed: {exc}")

    st.info(
        "First run? The backend seeds a default admin on startup "
        "(`admin@example.com` / `ChangeMe123!` unless overridden via "
        "`FRA_ADMIN_EMAIL` / `FRA_ADMIN_PASSWORD`). Log in as admin, then "
        "create Preparer/Reviewer users from the Clients & Funds page."
    )
