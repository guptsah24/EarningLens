"""
pages/02_signup.py — Create Account
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
st.set_page_config(page_title="Create Account · EarningsLens", page_icon="🔭", layout="wide")


import styles, auth_client

st.markdown(styles.GLOBAL_CSS, unsafe_allow_html=True)

st.markdown("""
<style>
/* Hide Sidebar and UI elements */
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }
div[data-testid="stAlert"]         { display: none !important; }

/* Main container constraints */
.main .block-container {
    max-width: 100% !important;
    padding-top: 0 !important;
    padding-left: 4rem !important;
    padding-right: 4rem !important;
}

/* Style the form container to look like a card */
div[data-testid="stForm"] {
    max-width: 660px !important;
    margin: 0 auto !important;
    background: #0d1526 !important;
    border: 1px solid rgba(99,179,237,0.2) !important;
    border-top: 3px solid #1a56db !important;
    border-radius: 14px !important;
    padding: 32px 32px 28px !important;
}

/* Submit button styling */
div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #1a56db, #0ea5e9) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    height: 48px !important;
    box-shadow: 0 0 24px rgba(14,165,233,0.2) !important;
    margin-top: 8px !important;
    width: 100% !important;
}

/* Input labels */
div[data-testid="stForm"] label {
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    color: #4a6a8a !important;
}

/* --- THE FIX: Remove red background and stop border rounding on click --- */

/* Target the wrapper and prevent background color changes */
div[data-testid="stTextInput"] [data-baseweb="input"],
div[data-testid="stTextInput"] [data-baseweb="base-input"] {
    background-color: #111e35 !important;
    border-radius: 8px !important;
    transition: none !important;
}

/* Target internal divs that cause the 'red' flash and rounded shift */
div[data-testid="stTextInput"] [data-baseweb="input"] > div {
    background-color: transparent !important;
    border-radius: inherit !important;
    border: none !important;
}

/* Force focus state to remain consistent and blue */
div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
    border: 1px solid #63b3ed !important;
    background-color: #111e35 !important;
    box-shadow: none !important;
}

/* --- Password Eye Icon Alignment Fix --- */

/* 1. Target the flex container inside the text input */
div[data-testid="stTextInput"] > div {
    display: flex !important;
    align-items: stretch !important;
    padding-right: 0px !important; 
    background-color: transparent !important;
}

/* 2. Style the password input field */
div[data-testid="stTextInput"] input {
    background-color: transparent !important;
    color: #e8eaf0 !important;
    border-radius: 8px 0 0 8px !important;
    border: none !important;
    flex-grow: 1 !important;
}

/* 3. Style the eye icon button to sit flush on the right */
div[data-testid="stTextInput"] button {
    background: transparent !important;
    border: none !important;
    color: #63b3ed !important;
    padding: 0 12px !important;
    height: auto !important;
    margin: 0 !important;
    margin-right: 0px !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

div[data-testid="stTextInput"] button:hover {
    background: transparent !important;
    color: #90cdf4 !important;
}

div[data-testid="stTextInput"] button svg {
    color: #63b3ed !important;
    width: 18px !important;
    height: 18px !important;
}

/* Page link nav styling */
div[data-testid="stPageLink"] a {
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    color: #63b3ed !important;
    text-decoration: none !important;
}
</style>
""", unsafe_allow_html=True)

if st.session_state.get("user"):
    st.switch_page("app.py")

st.markdown("""
<div style="text-align:center;padding:52px 0 28px;">
  <div style="font-size:40px;margin-bottom:12px;">🔭</div>
  <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;
              color:#e8eaf0;letter-spacing:0.5px;">EarningsLens</div>
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#3d5a7a;
              letter-spacing:2.5px;text-transform:uppercase;margin-top:8px;">
    Guidance Intelligence Platform
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="max-width:660px;margin:0 auto;">
  <div style="font-family:'Syne',sans-serif;font-size:20px;font-weight:700;
              color:#e8eaf0;margin-bottom:4px;padding-left:2px;">Create account</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#4a6a8a;
              margin-bottom:12px;padding-left:2px;">Free access · 531 companies · 2023–2025</div>
</div>
""", unsafe_allow_html=True)

feedback_slot = st.empty()

with st.form("signup_form"):
    full_name = st.text_input("Full name", placeholder="Jane Smith")
    email     = st.text_input("Email address", placeholder="analyst@fund.com")
    password  = st.text_input("Password", type="password", placeholder="Min. 8 characters")
    confirm   = st.text_input("Confirm password", type="password", placeholder="••••••••")
    submit    = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

if submit:
    if not full_name or not email or not password or not confirm:
        feedback_slot.markdown(styles.msg_error("Please fill in all fields."), unsafe_allow_html=True)
    elif len(password) < 8:
        feedback_slot.markdown(styles.msg_error("Password must be at least 8 characters."), unsafe_allow_html=True)
    elif password != confirm:
        feedback_slot.markdown(styles.msg_error("Passwords don't match."), unsafe_allow_html=True)
    else:
        with st.spinner("Creating your account…"):
            result = auth_client.sign_up(email.strip(), password, full_name.strip())
        if result["ok"]:
            feedback_slot.markdown(
                styles.msg_success("Account created! You can now sign in."),
                unsafe_allow_html=True,
            )
        else:
            feedback_slot.markdown(styles.msg_error(f"Sign-up failed: {result['error']}"), unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
_, center, _ = st.columns([1, 2, 1])
with center:
    st.markdown("<div style='font-family:DM Mono,monospace;font-size:11px;color:#3d5a7a;margin-bottom:2px;'>Have an account?</div>", unsafe_allow_html=True)
    st.page_link("app.py", label="Sign in →")