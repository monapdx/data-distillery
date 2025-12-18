import sys
from pathlib import Path
import streamlit as st

# Ensure project root is importable no matter how Streamlit is launched
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Takeout Toolkit – Home", layout="wide")

st.title("Streamlit Takeout Toolkit")
st.caption("Local-first tools for exploring Google Takeout + ChatGPT exports. Nothing is uploaded anywhere.")

# ---- App registry (add/edit here as your suite grows) ----
APPS = [
    {
        "title": "Inbox Archeology",
        "subtitle": "Email relationship analysis from Gmail Takeout (.mbox)",
        "path": "apps/inbox_archeology_app.py",
        "tags": ["Gmail", "MBOX", "Relationships", "Timeline"],
    },
    {
        "title": "InboxGPT",
        "subtitle": "Chat history explorer (ChatGPT exports / logs)",
        "path": "apps/inboxGPT_app.py",
        "tags": ["ChatGPT", "Search", "Explore"],
    },
    {
        "title": "Category Viewer",
        "subtitle": "Browse/export categories (Takeout JSON/HTML utilities)",
        "path": "apps/category_viewer.py",
        "tags": ["Takeout", "Viewer"],
    },
    {
        "title": "MBOX Viewer",
        "subtitle": "Quickly browse an .mbox mailbox",
        "path": "apps/mbox_viewer_streamlit.py",
        "tags": ["MBOX", "Email"],
    },
    {
        "title": "Search History Analyzer",
        "subtitle": "Explore Google Search history exports",
        "path": "apps/search_history_app.py",
        "tags": ["Google", "Search History"],
    },
    {
        "title": "WordLab",
        "subtitle": "Text exploration / word tools",
        "path": "apps/wordlab_streamlit_app.py",
        "tags": ["Text", "NLP-ish", "Playground"],
    },
]

EXTRAS = [
    {
        "title": "Offline Chat Viewer (HTML)",
        "subtitle": "Standalone offline conversation viewer",
        "relpath": "extras/html/offline-GPT.html",
    },
    {
        "title": "Email Viewer (HTML)",
        "subtitle": "Standalone lightweight email exploration tool",
        "relpath": "extras/html/email-viewer.html",
    },
]


def exists(relpath: str) -> bool:
    return (PROJECT_ROOT / relpath).exists()


def launch_streamlit(relpath: str):
    """
    Re-launch Streamlit pointing at another app file.
    This replaces the current process (simple + reliable on Windows).
    """
    target = PROJECT_ROOT / relpath
    if not target.exists():
        st.error(f"Missing file: {relpath}")
        st.stop()

    args = [
        "streamlit", "run", str(target),
        "--server.headless=true",
    ]
    # Exec replaces current python process
    import os
    os.execvp(sys.executable, [sys.executable, "-m"] + args)


st.markdown("---")
st.subheader("Apps")

cols = st.columns(2, gap="large")
for i, app in enumerate(APPS):
    col = cols[i % 2]
    with col:
        st.markdown(f"### {app['title']}")
        st.write(app["subtitle"])
        st.caption(" • ".join(app["tags"]))

        ok = exists(app["path"])
        if not ok:
            st.warning(f"Missing: `{app['path']}`")

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button(f"Open {app['title']}", disabled=not ok, use_container_width=True, key=f"open_{i}"):
                launch_streamlit(app["path"])
        with c2:
            st.code(app["path"], language="text")

st.markdown("---")
st.subheader("Offline HTML tools (no Streamlit)")
st.write("These run directly in your browser. Double-click them in File Explorer.")

for item in EXTRAS:
    p = PROJECT_ROOT / item["relpath"]
    st.markdown(f"**{item['title']}** — {item['subtitle']}")
    st.code(str(p), language="text")

st.markdown("---")
with st.expander("Privacy note"):
    st.write(
        "This toolkit is designed to run locally. Your Takeout/exports stay on your computer unless you choose to share them."
    )
