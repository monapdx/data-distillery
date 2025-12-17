from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from typing import Callable, Optional, Dict, Any

ProgressCB = Optional[Callable[[float, str], None]]

def _call_progress(cb: ProgressCB, p: float, msg: str) -> None:
    if cb:
        cb(float(p), msg)

def _run_script(script_path: Path, args: list[str]) -> None:
    cmd = [sys.executable, str(script_path)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Script failed: {script_path.name}\n\n"
            f"CMD: {' '.join(cmd)}\n\n"
            f"STDOUT:\n{proc.stdout}\n\n"
            f"STDERR:\n{proc.stderr}"
        )

def run_pipeline(mbox_path: str | Path, work_dir: str | Path, progress_cb: ProgressCB = None) -> Dict[str, Any]:
    mbox_path = Path(mbox_path)
    work_dir = Path(work_dir)

    out_dir = work_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    ia_root = Path(__file__).resolve().parent
    scripts_dir = ia_root / "scripts"

    inbox_metadata = out_dir / "inbox_metadata.csv"
    rel_raw = out_dir / "relationships_raw.csv"
    rel_filtered = out_dir / "relationships_filtered.csv"
    rel_clean = out_dir / "relationships_clean.csv"
    core_timeline = out_dir / "core_timeline.csv"

    _call_progress(progress_cb, 0.05, "Extracting headers from MBOX…")
    _run_script(scripts_dir / "extract_headers.py", ["--mbox", str(mbox_path), "--out", str(inbox_metadata)])
    _call_progress(progress_cb, 0.25, "Building raw relationships…")
    _run_script(scripts_dir / "extract_relationships.py", ["--in", str(inbox_metadata), "--out", str(rel_raw)])
    _call_progress(progress_cb, 0.45, "Filtering relationships…")
    _run_script(scripts_dir / "filter_relationships.py", ["--in", str(rel_raw), "--out", str(rel_filtered)])
    _call_progress(progress_cb, 0.60, "Cleaning relationships…")
    _run_script(scripts_dir / "clean_relationships.py", ["--in", str(rel_filtered), "--out", str(rel_clean)])
    _call_progress(progress_cb, 0.78, "Building CORE timeline…")
    _run_script(scripts_dir / "build_core_timeline.py", ["--in", str(rel_clean), "--out", str(core_timeline)])
    _call_progress(progress_cb, 1.0, "Done.")

    return {
        "out_dir": out_dir,
        "inbox_metadata": inbox_metadata,
        "relationships_raw": rel_raw,
        "relationships_filtered": rel_filtered,
        "relationships_clean": rel_clean,
        "core_timeline": core_timeline,
    }
