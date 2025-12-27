# apps/inbox_dashboard_app.py
#
# Thin wrapper that mounts the Inbox Archeology dashboard inside the
# Data Distillery router.

from __future__ import annotations

from typing import Callable

import streamlit as st


def main(go_home: Callable[[], None] | None = None, out_dir: str = ""):
    # If Inbox Archeology just ran, it will pass (or store) an output directory.
    if out_dir:
        st.session_state.dd_inbox_arch_out_dir = out_dir

    # Optional "Back" button (router-aware). NOTE: This must happen
    # before importing the dashboard module *only if* the dashboard is
    # not calling st.set_page_config. Ours guards set_page_config, so
    # this is safe.
    if go_home is not None:
        if st.button("← Back to Home", use_container_width=True):
            go_home()

    # Importing this module renders the dashboard.
    # It reads dd_inbox_arch_out_dir from st.session_state if set.
    import inbox_archeology.scripts.inbox_dashboard  # noqa: F401
