# Data Distillery

Data Distillery is a **local-first** suite of tools for turning large personal data exports
(Google Takeout, Gmail, ChatGPT archives) into **human-readable** insight.

Most people can download their data.
Very few can do anything meaningful with it.

This project exists to close that gap.

## Why this exists

Modern platforms will happily give you “your data” — but what you get back is usually:

- enormous files

- obscure formats

- thousands of rows with no narrative

- data that is technically complete but practically unusable

## Data Distillery focuses on:

- reducing overwhelming datasets into something readable

- segmenting large volumes into meaningful slices

- surfacing patterns over time, not just raw logs

- keeping everything on your own computer

There is no upload, no cloud, and no tracking.
If your data feels too personal to hand to a web app, this toolkit is for you.

This folder is meant to be downloaded and run **100% locally** on the user’s computer. The apps process files the user selects (e.g., Gmail Takeout `.mbox`, Google Takeout JSON/HTML), and **nothing is uploaded anywhere** unless the user explicitly does so.

## Quick start (Windows)

1) Install **Python 3.12+** from python.org (if you don’t already have it).
2) Unzip this project.
3) Double-click **RUN_ME.bat**.

It will:
- create a `.venv` virtual environment (first run only)
- install dependencies from `requirements.txt`
- let you choose which app to run

## Apps included

The batch menu assumes these files exist:

- `apps/inbox_archeology_app.py`
- `apps/inboxGPT_app.py`
- `apps/category_viewer.py`
- `apps/mbox_viewer_streamlit.py`
- `apps/search_history_app.py`
- `apps/wordlab_streamlit_app.py`

If you rename apps, update `RUN_ME.bat` accordingly.

## Privacy / safety note

These tools are designed to run locally. Users should avoid sharing exported Takeout data with others.  
If you ship demo data, ensure it is **fully anonymized** and does not include private messages, email addresses, or identifiers.

## Troubleshooting

### “Python was not found”
- Install Python from python.org
- Reopen the terminal
- Run: `python --version`

### ModuleNotFoundError / missing packages
- Run `RUN_ME.bat` again (it installs dependencies).
- Or manually:
  - `.\.venv\Scripts\activate`
  - `pip install -r requirements.txt`

### Streamlit opens but app can’t import your package
- Ensure your app adds project root to `sys.path` (you already did this in `inbox_archeology_app.py`).
- Ensure `inbox_archeology/__init__.py` exists.

## Developer notes

Re-freeze dependencies (maintainer only):
1) Activate venv: `.\.venv\Scripts\activate`
2) `pip freeze > requirements.txt`
