# apps/inbox_archeology_app.py
#
# Inbox Archeology – Streamlit wrapper (local-first)
# Refactored for Data Distillery "Option B" router navigation.
# NOTE: Do NOT call st.set_page_config() in this file.

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable

import streamlit as st


def main(go_home: Callable[[], None] | None = None):
    # --------------------------------------------------
    # Bootstrap: ensure repo root is importable
    # --------------------------------------------------
    PROJECT_ROOT = Path(__file__).resolve().parents[1]  # repo root
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    # --------------------------------------------------
    # Header + Back button
    # --------------------------------------------------
    top_left, top_right = st.columns([0.8, 0.2])
    with top_left:
        st.title("Inbox Archeology")
        st.caption("Local-first Gmail Takeout analysis. Nothing leaves your computer.")
    with top_right:
        if go_home is not None:
            if st.button("← Back to Home", use_container_width=True):
                go_home()

    st.markdown("---")

    # --------------------------------------------------
    # Import pipeline
    # --------------------------------------------------
    try:
        from inbox_archeology.pipeline import run_pipeline
    except Exception as e:
        st.error(
            "Could not import Inbox Archeology pipeline.\n\n"
            "Expected: `inbox_archeology/pipeline.py` with `run_pipeline(...)`\n\n"
            f"Error:\n{e}"
        )
        st.stop()

    # --------------------------------------------------
    # Paths
    # --------------------------------------------------
    IA_ROOT = PROJECT_ROOT / "inbox_archeology"
    INPUT_DIR = IA_ROOT / "input"
    WORKSPACES = IA_ROOT / "workspaces"

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACES.mkdir(parents=True, exist_ok=True)

    def slugify(name: str) -> str:
        s = name.strip()
        s = re.sub(r"\.mbox$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "run"

    # --------------------------------------------------
    # Sidebar
    # --------------------------------------------------
    with st.sidebar:
        st.header("Run settings")

        keep_workspace = st.toggle(
            "Keep workspace after run",
            value=True,
            help="If off, you can delete the workspace manually after reviewing outputs.",
        )

        open_dashboard = st.toggle(
            "Open dashboard automatically when finished",
            value=True,
            help="After the pipeline completes, jump straight into the interactive dashboard.",
        )

        st.divider()
        st.markdown("### Input folder")
        st.write("Drop your Gmail Takeout `.mbox` file here:")
        st.code(str(INPUT_DIR), language="text")

        st.markdown("### Output folder")
        st.write("Outputs are written here:")
        st.code(str(WORKSPACES), language="text")

        st.info(
            "Tip: Gmail Takeout 'All Mail.mbox' is often very large. "
            "This app reads it from disk instead of uploading through the browser."
        )

    # --------------------------------------------------
    # Pick an MBOX from inbox_archeology/input/
    # --------------------------------------------------
    st.header("1) Place your .mbox file")
    st.markdown(
        f"""
1. Export Gmail from Google Takeout.
2. Find the file usually named **All Mail.mbox**.
3. Copy it into:

{INPUT_DIR}


Then click **Refresh list**.
"""
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Refresh list", use_container_width=True):
            st.rerun()
    with c2:
        st.write("")

    mbox_files = sorted(
        INPUT_DIR.glob("*.mbox"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not mbox_files:
        st.warning(
            "No `.mbox` files found in the input folder yet.\n\n"
            "Add an `.mbox` to the folder shown above, then click **Refresh list**."
        )
        st.stop()

    selected_mbox = st.selectbox(
        "Select an .mbox file to analyze",
        options=mbox_files,
        format_func=lambda p: p.name,
    )
    mbox_path = selected_mbox.resolve()
    st.success(f"Selected:\n{mbox_path}")

    # --------------------------------------------------
    # Workspace setup
    # --------------------------------------------------
    st.header("2) Workspace")

    default_run_name = slugify(mbox_path.stem)
    run_name = st.text_input(
        "Run name (folder name under workspaces/)",
        value=default_run_name,
        help="Use this to keep multiple runs separate (e.g. All_Mail_2025_12_20).",
    )
    run_name = slugify(run_name)

    workspace_dir = (WORKSPACES / run_name).resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)

    st.caption(f"Workspace:\n{workspace_dir}")

    # --------------------------------------------------
    # Run pipeline (button-gated)
    # --------------------------------------------------
    st.header("3) Run analysis")

    run_clicked = st.button("Run Inbox Archeology", type="primary", use_container_width=True)

    progress_bar = st.progress(0)
    status = st.empty()

    def progress_cb(pct: float, msg: str | None = None):
        progress_bar.progress(min(max(int(pct * 100), 0), 100))
        if msg:
            status.write(msg)

    if run_clicked:
        with st.spinner("Running Inbox Archeology pipeline..."):
            try:
                outputs = run_pipeline(
                    mbox_path=mbox_path,
                    work_dir=workspace_dir,
                    progress_cb=progress_cb,
                )
            except Exception as e:
                st.error("Pipeline failed")
                st.exception(e)
                st.stop()

        progress_bar.progress(100)
        status.success("Pipeline complete")

        # Hand-off to the dashboard page (suite router)
        try:
            if open_dashboard:
                out_dir = Path(outputs.get("out_dir", workspace_dir / "output")).resolve()
                st.session_state.dd_inbox_arch_out_dir = str(out_dir)
                st.session_state.dd_page = "inbox_dashboard"
                st.rerun()
        except Exception:
            # If anything goes wrong, we still show the manual next-steps below.
            pass

        st.header("Results")
        st.markdown(
            f"""
**Done.** Outputs are stored locally at:

inbox_archeology/workspaces/{run_name}/output/

"""
        )

        if isinstance(outputs, dict) and outputs:
            st.subheader("Generated files")
            for k, v in outputs.items():
                st.write(f"**{k}** → {v}")

        out_dir = workspace_dir / "output"
        st.subheader("Explore in dashboard")
        if st.button("Open dashboard now", use_container_width=True):
            st.session_state.dd_inbox_arch_out_dir = str(out_dir)
            st.session_state.dd_page = "inbox_dashboard"
            st.rerun()

        if not keep_workspace:
            st.warning(
                "Workspace retention is disabled. "
                "You can delete the workspace folder after you're done reviewing outputs."
            )
    else:
        st.info("Ready when you are — click **Run Inbox Archeology** to start.")
