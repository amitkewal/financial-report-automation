import streamlit as st

from api_client import api_get, api_post, current_user, require_login

st.set_page_config(page_title="Clients & Funds", layout="wide")
require_login()
user = current_user()

st.title("Client & Fund Management")

if user["role"] == "admin":
    with st.expander("Create a new user (Admin only)"):
        with st.form("create_user_form"):
            c1, c2, c3, c4 = st.columns(4)
            new_email = c1.text_input("Email")
            new_name = c2.text_input("Full name")
            new_password = c3.text_input("Password", type="password")
            new_role = c4.selectbox("Role", ["preparer", "reviewer", "admin"])
            if st.form_submit_button("Create user"):
                api_post("/auth/users", json={"email": new_email, "full_name": new_name, "password": new_password, "role": new_role})
                st.success(f"Created user {new_email}")

    with st.expander("Create a new client (Admin only)"):
        with st.form("create_client_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Client name")
            onshore = c2.text_input("Onshore team")
            c3, c4 = st.columns(2)
            offshore = c3.text_input("Offshore team")
            storage_link = c4.text_input("Storage link")
            if st.form_submit_button("Create client"):
                api_post(
                    "/clients",
                    json={
                        "name": name,
                        "onshore_team": onshore,
                        "offshore_team": offshore,
                        "storage_link": storage_link,
                    },
                )
                st.success(f"Created client {name}")
                st.rerun()

    with st.expander("Grant a user access to a client (Admin only)"):
        users = api_get("/auth/users") or []
        clients = api_get("/clients") or []
        if users and clients:
            with st.form("grant_access_form"):
                u = st.selectbox("User", users, format_func=lambda x: f"{x['full_name']} ({x['email']})")
                c = st.selectbox("Client", clients, format_func=lambda x: x["name"])
                if st.form_submit_button("Grant access"):
                    api_post("/auth/grant-client-access", json={"user_id": u["id"], "client_id": c["id"]})
                    st.success(f"Granted {u['email']} access to {c['name']}")

st.divider()

clients = api_get("/clients") or []
if not clients:
    st.info("No clients yet. Ask an admin to create one above.")
    st.stop()

client = st.selectbox("Select a client", clients, format_func=lambda x: x["name"])
st.session_state["selected_client_id"] = client["id"]

st.subheader(f"Funds for {client['name']}")

if user["role"] != "reviewer":
    with st.expander("Add a new fund"):
        with st.form("create_fund_form"):
            c1, c2 = st.columns(2)
            legal_name = c1.text_input("Fund legal name")
            short_code = c2.text_input("Short code (e.g. ALPHA1)")
            c3, c4, c5 = st.columns(3)
            fund_type = c3.selectbox("Fund type", ["private_equity", "real_estate", "debt", "hedge_fund", "other"])
            fye = c4.text_input("Fiscal year end (MM-DD)", value="12-31")
            currency = c5.text_input("Currency", value="USD")
            if st.form_submit_button("Create fund"):
                api_post(
                    f"/clients/{client['id']}/funds",
                    json={
                        "legal_name": legal_name,
                        "short_code": short_code,
                        "fund_type": fund_type,
                        "fiscal_year_end": fye,
                        "currency": currency,
                    },
                )
                st.success(f"Created fund {legal_name}")
                st.rerun()

funds = api_get(f"/clients/{client['id']}/funds") or []
if not funds:
    st.info("No funds yet for this client.")
    st.stop()

for fund in funds:
    with st.expander(f"{fund['legal_name']} ({fund['short_code']}) — {fund['fund_type']}"):
        st.write(f"Currency: {fund['currency']} | Fiscal year end: {fund['fiscal_year_end']}")

        st.markdown("**Report template**")
        templates = api_get(f"/funds/{fund['id']}/templates") or []
        if templates:
            st.table(
                [{"version": t["version"], "filename": t["filename"], "active": t["is_active"]} for t in templates]
            )
        if user["role"] != "reviewer":
            uploaded = st.file_uploader(
                "Upload a new .docx template for this fund", type=["docx"], key=f"tpl_{fund['id']}"
            )
            if uploaded and st.button("Upload template", key=f"tpl_btn_{fund['id']}"):
                api_post(f"/funds/{fund['id']}/templates", files={"file": (uploaded.name, uploaded.getvalue())})
                st.success("Template uploaded")
                st.rerun()

        st.markdown("**Periods**")
        periods = api_get(f"/funds/{fund['id']}/periods") or []
        if periods:
            st.table([{"label": p["period_label"], "end_date": p["period_end_date"]} for p in periods])
        if user["role"] != "reviewer":
            c1, c2 = st.columns(2)
            new_period_label = c1.text_input("New period label (e.g. 2025-Q4)", key=f"period_{fund['id']}")
            new_period_end = c2.text_input("Period end date (YYYY-MM-DD)", key=f"period_end_{fund['id']}")
            if st.button("Add period", key=f"period_btn_{fund['id']}") and new_period_label:
                api_post(
                    f"/funds/{fund['id']}/periods",
                    json={"period_label": new_period_label, "period_end_date": new_period_end or None},
                )
                st.success(f"Added period {new_period_label}")
                st.rerun()
