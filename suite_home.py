# suite_home.py
from __future__ import annotations

import sys
from pathlib import Path
import streamlit as st

# Ensure project root is importable no matter how Streamlit is launched
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Data Distillery – Home", layout="wide")

# ----------------------------
# Navigation (Option B Router)
# ----------------------------
PAGE_HOME = "home"
PAGE_INBOX_ARCH = "inbox_archeology"
PAGE_INBOXGPT = "inboxgpt"

if "dd_page" not in st.session_state:
    st.session_state.dd_page = PAGE_HOME


def go(page: str):
    st.session_state.dd_page = page
    st.rerun()


def render_home():
    st.title("Data Distillery")
    st.caption(
        "Local-first tools for exploring Google Takeout + ChatGPT exports. "
        "Nothing is uploaded anywhere."
    )

    st.markdown("---")
    st.subheader("Apps")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("### Inbox Archeology")
        st.write("Email relationship analysis from Gmail Takeout (`.mbox`).")
        st.caption("Gmail • MBOX • Relationships • Timeline")
        if st.button("Open Inbox Archeology", use_container_width=True):
            go(PAGE_INBOX_ARCH)

    with col2:
        st.markdown("### InboxGPT")
        st.write("Categorize/label your ChatGPT `conversations.json` export.")
        st.caption("ChatGPT • Categories • Local DB • Export")
        if st.button("Open InboxGPT", use_container_width=True):
            go(PAGE_INBOXGPT)

    st.markdown("---")
    st.subheader("Offline HTML tools (no Streamlit)")
    st.write("These run directly in your browser. Double-click them in File Explorer.")

    extras = [
        ("Offline Chat Viewer (HTML)", "extras/html/offline-GPT.html"),
        ("Email Viewer (HTML)", "extras/html/email-viewer.html"),
    ]
    for title, relpath in extras:
        p = (PROJECT_ROOT / relpath)
        st.markdown(f"**{title}**")
        st.code(str(p), language="text")

    st.markdown("---")
    with st.expander("Privacy note"):
        st.write(
            "This toolkit is designed to run locally. Your Takeout/exports stay on your computer "
            "unless you choose to share them."
        )


def render_inbox_archeology():
    # Import lazily so the module doesn't run at import time
    from apps import inbox_archeology_app
    inbox_archeology_app.main(go_home=lambda: go(PAGE_HOME))


def render_inboxgpt():
    from apps import inboxGPT_app
    inboxGPT_app.main(go_home=lambda: go(PAGE_HOME))


# ----------------------------
# Router
# ----------------------------
page = st.session_state.dd_page

if page == PAGE_HOME:
    render_home()
elif page == PAGE_INBOX_ARCH:
    render_inbox_archeology()
elif page == PAGE_INBOXGPT:
    render_inboxgpt()
else:
    # Fallback
    st.session_state.dd_page = PAGE_HOME
    st.rerun()
