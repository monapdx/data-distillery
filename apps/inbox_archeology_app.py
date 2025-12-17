# Inbox Archeology – Streamlit wrapper
# Drop this file into: Streamlit/apps/inbox_archeology_app.py
# This file does NOT modify your existing scripts.
# It only orchestrates them safely.

from pathlib import Path
import tempfile
import shutil
import streamlit as st

# ---- import your pipeline ----
# Expected: Streamlit/inbox_archeology/pipeline.py
# with a function run_pipeline(mbox_path, work_dir, progress_cb=None)
try:
    from inbox_archeology.pipeline import run_pipeline
except Exception as e:
    run_pipeline = None
    PIPELINE_IMPORT_ERROR = e

# -----------------------------
# App setup
# -----------------------------
st.set_page_config(
    page_title="Inbox Archeology (Local)",
    layout="wide",
)

st.title("Inbox Archeology")
st.caption("Local-first analysis of a Gmail Takeout .mbox file. Nothing leaves your computer.")

# Fail fast if pipeline import is broken
if run_pipeline is None:
    st.error(
        "Could not import Inbox Archeology pipeline.\n\n"
        "Expected: Streamlit/inbox_archeology/pipeline.py with run_pipeline(...).\n\n"
        f"Error: {PIPELINE_IMPORT_ERROR}"
    )
    st.stop()

# -----------------------------
# Paths
# -----------------------------
APP_ROOT = Path(__file__).resolve().parents[1]   # Streamlit/
IA_ROOT = APP_ROOT / "inbox_archeology"
WORKSPACES = IA_ROOT / "workspaces"
WORKSPACES.mkdir(exist_ok=True)

# -----------------------------
# Sidebar – controls
# -----------------------------
with st.sidebar:
    st.header("Run settings")

    keep_workspace = st.toggle(
        "Keep workspace after run",
        value=True,
        help="If off, temporary files are deleted when the app reruns."
    )

    st.divider()
    st.markdown("**Expected input**")
    st.write("• Gmail Takeout `.mbox` (All Mail)")
    st.write("• Output stored locally under `inbox_archeology/workspaces/`")

# -----------------------------
# Main UI
# -----------------------------
uploaded = st.file_uploader(
    "Upload your Gmail Takeout .mbox file",
    type=["mbox"],
    accept_multiple_files=False,
)

if not uploaded:
    st.info("Upload an .mbox file to begin analysis.")
    st.stop()

# -----------------------------
# Workspace handling
# -----------------------------
# Each run gets its own folder so nothing collides
workspace_dir = WORKSPACES / uploaded.name.replace(".mbox", "")
workspace_dir.mkdir(parents=True, exist_ok=True)

mbox_path = workspace_dir / uploaded.name

# Save uploaded file to disk
with open(mbox_path, "wb") as f:
    f.write(uploaded.getbuffer())

st.success(f"Saved upload to {mbox_path}")

# -----------------------------
# Run pipeline
# -----------------------------
st.header("Processing inbox")

progress = st.progress(0)
status = st.empty()


def progress_cb(pct: float, msg: str | None = None):
    progress.progress(min(max(int(pct * 100), 0), 100))
    if msg:
        status.write(msg)

with st.spinner("Running Inbox Archeology pipeline..."):
    try:
        outputs = run_pipeline(
            mbox_path=mbox_path,
            work_dir=workspace_dir,
            progress_cb=lambda p, m=None: progress_cb(p, m),
        )
    except Exception as e:
        st.error("Pipeline failed")
        st.exception(e)
        st.stop()

progress.progress(100)
status.success("Pipeline complete")

# -----------------------------
# Results
# -----------------------------
st.header("Results")

st.markdown(
    """
    The analysis has finished successfully.

    Generated files are stored locally in:

    ```
    inbox_archeology/workspaces/
    ```
    """
)

if isinstance(outputs, dict):
    st.subheader("Generated outputs")
    for key, value in outputs.items():
        st.write(f"**{key}** → {value}")

# -----------------------------
# Launch dashboard (optional)
# -----------------------------
st.subheader("Inbox Dashboard")
st.markdown(
    "If you want to explore the results interactively, you can now open the Inbox Dashboard app."
)

st.code("streamlit run inbox_archeology/scripts/inbox_dashboard.py", language="bash")

# -----------------------------
# Cleanup (optional)
# -----------------------------
if not keep_workspace:
    st.warning("Workspace will be deleted on next run.")
