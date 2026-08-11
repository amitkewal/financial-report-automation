"""Thin wrapper around the FastAPI backend REST API for the Streamlit POC UI.

This POC uses Streamlit intentionally per the project spec ("fastest local
POC... swapped for React once multi-user auth and role-based workflows are
needed"). Every screen below talks to the backend exclusively through this
module - the UI has no direct DB or filesystem access, so swapping the
frontend later doesn't touch business logic at all.
"""

import requests
import streamlit as st

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def get_base_url() -> str:
    return st.session_state.get("api_base_url", DEFAULT_BASE_URL)


def is_logged_in() -> bool:
    return "token" in st.session_state


def current_user() -> dict | None:
    return st.session_state.get("user")


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state['token']}"}


def login(email: str, password: str) -> dict:
    resp = requests.post(f"{get_base_url()}/auth/login", json={"email": email, "password": password}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    st.session_state["token"] = data["access_token"]
    st.session_state["user"] = data["user"]
    return data["user"]


def logout():
    for key in ("token", "user"):
        st.session_state.pop(key, None)


def _handle(resp: requests.Response):
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        st.error(f"API error {resp.status_code}: {detail}")
        resp.raise_for_status()
    if not resp.content:
        return None
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.json()
    return resp.content


def api_get(path: str, **kwargs):
    resp = requests.get(f"{get_base_url()}{path}", headers=auth_headers(), timeout=30, **kwargs)
    return _handle(resp)


def api_post(path: str, **kwargs):
    resp = requests.post(f"{get_base_url()}{path}", headers=auth_headers(), timeout=60, **kwargs)
    return _handle(resp)


def api_put(path: str, **kwargs):
    resp = requests.put(f"{get_base_url()}{path}", headers=auth_headers(), timeout=30, **kwargs)
    return _handle(resp)


def require_login():
    if not is_logged_in():
        st.warning("Please log in from the Home page first.")
        st.stop()


def require_role(*roles: str):
    require_login()
    user = current_user()
    if user["role"] != "admin" and user["role"] not in roles:
        st.error(f"This page requires one of these roles: {', '.join(roles)}. You are a {user['role']}.")
        st.stop()
