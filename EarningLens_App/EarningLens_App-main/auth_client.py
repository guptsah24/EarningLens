"""
auth_client.py
Supabase auth operations — sign in, sign up, sign out.
"""
from __future__ import annotations
import os
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def _get_auth_client() -> Client:
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key)


def sign_in(email: str, password: str) -> dict:
    try:
        sb   = _get_auth_client()
        resp = sb.auth.sign_in_with_password({"email": email, "password": password})
        return {
            "ok":    True,
            "user":  resp.user,
            "token": resp.session.access_token,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def sign_up(email: str, password: str, full_name: str = "") -> dict:
    try:
        sb   = _get_auth_client()
        opts = {"email": email, "password": password}
        if full_name:
            opts["options"] = {"data": {"full_name": full_name}}
        resp = sb.auth.sign_up(opts)
        return {"ok": True, "user": resp.user}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def sign_out() -> None:
    try:
        _get_auth_client().auth.sign_out()
    except Exception:
        pass
    for key in ("user", "token"):
        st.session_state.pop(key, None)