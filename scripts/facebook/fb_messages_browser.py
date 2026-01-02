import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import streamlit as st
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

INDEX_FILE = "messages.htm"
MESSAGES_DIR = "messages"
EXCLUDE_NAME = "Facebook User"

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def is_group_title(title: str) -> bool:
    return "," in title

def parse_timestamp(meta_text: str):
    t = normalize_ws(meta_text)
    try:
        return dateparser.parse(t, fuzzy=True)
    except Exception:
        t2 = re.sub(r"\b(PST|PDT|EST|EDT|CST|CDT|MST|MDT)\b", "", t).strip()
        try:
            return dateparser.parse(t2, fuzzy=True)
        except Exception:
            return None

@dataclass
class ThreadRow:
    title: str
    href: str
    is_group: bool

@dataclass
class Message:
    user: str
    meta: str
    dt: Optional[str]
    text: str

@st.cache_data(show_spinner=False)
def load_index(base_dir: str) -> List[ThreadRow]:
    index_path = os.path.join(base_dir, INDEX_FILE)
    with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    rows: List[ThreadRow] = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if href.startswith("messages/") and href.endswith(".html"):
            title = normalize_ws(a.get_text(" ", strip=True))
            rows.append(ThreadRow(title=title, href=href, is_group=is_group_title(title)))
    return rows

def thread_full_path(base_dir: str, href: str) -> str:
    return os.path.join(base_dir, href.replace("/", os.sep))

@st.cache_data(show_spinner=False)
def parse_thread(base_dir: str, href: str) -> List[Message]:
    path = thread_full_path(base_dir, href)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    msgs: List[Message] = []

    # Facebook export pattern:
    # <div class="message"><div class="message_header"><span class="user">...</span><span class="meta">...</span></div></div>
    # <p>message text</p>
    # repeated...
    headers = soup.select("div.message")

    for h in headers:
        user_el = h.select_one("span.user")
        meta_el = h.select_one("span.meta")

        user = normalize_ws(user_el.get_text(" ", strip=True)) if user_el else ""
        meta = normalize_ws(meta_el.get_text(" ", strip=True)) if meta_el else ""

        dt_obj = parse_timestamp(meta) if meta else None
        dt_iso = dt_obj.isoformat(sep=" ") if dt_obj else None

        # body is usually the next sibling <p> (sometimes can be missing)
        body = ""
        sib = h.find_next_sibling()
        if sib and sib.name == "p":
            body = normalize_ws(sib.get_text(" ", strip=True))

        msgs.append(Message(user=user, meta=meta, dt=dt_iso, text=body))

    return msgs

def filter_threads(rows: List[ThreadRow], q: str, include_groups: bool, include_facebook_user: bool) -> List[ThreadRow]:
    q = (q or "").lower().strip()
    out = []
    for r in rows:
        if not include_groups and r.is_group:
            continue
        if not include_facebook_user and normalize_ws(r.title) == EXCLUDE_NAME:
            continue
        if q and q not in r.title.lower():
            continue
        out.append(r)
    return out

def main():
    st.set_page_config(page_title="FB Messages Browser", layout="wide")
    st.title("Facebook Messages Browser (HTML export)")

    base_dir = st.text_input("Base folder (where messages.htm lives):", value=os.getcwd())

    # Guardrails
    if not os.path.isfile(os.path.join(base_dir, INDEX_FILE)):
        st.error(f"Couldn't find {INDEX_FILE} in: {base_dir}")
        st.stop()
    if not os.path.isdir(os.path.join(base_dir, MESSAGES_DIR)):
        st.error(f"Couldn't find {MESSAGES_DIR}/ folder in: {base_dir}")
        st.stop()

    rows = load_index(base_dir)

    with st.sidebar:
        st.header("Browse")
        q = st.text_input("Search names / titles")
        include_groups = st.checkbox("Include group chats", value=False)
        include_facebook_user = st.checkbox("Include 'Facebook User'", value=False)

        filtered = filter_threads(rows, q, include_groups, include_facebook_user)

        st.caption(f"{len(filtered)} threads shown (of {len(rows)})")

        # Choose thread
        options = [f"{r.title}  —  {r.href}" for r in filtered]
        selected = st.selectbox("Thread", options=options, index=0 if options else None)

    if not filtered:
        st.info("No threads match your filters.")
        st.stop()

    # Resolve selection back to href
    selected_href = selected.split("—")[-1].strip()
    msgs = parse_thread(base_dir, selected_href)

    # Simple stats
    st.subheader(normalize_ws(selected.split("—")[0]))
    col1, col2, col3 = st.columns(3)
    col1.metric("Messages (header count)", len(msgs))

    # date range
    dts = [m.dt for m in msgs if m.dt]
    if dts:
        col2.metric("First", dts[0])
        col3.metric("Last", dts[-1])
    else:
        col2.metric("First", "—")
        col3.metric("Last", "—")

    st.divider()

    # Filters for display
    with st.expander("Display controls", expanded=True):
        users = sorted({m.user for m in msgs if m.user})
        user_filter = st.multiselect("Show only these senders (optional)", users, default=[])
        contains = st.text_input("Message contains (optional)")
        limit = st.slider("Max messages to render", 50, 5000, 500, step=50)

    shown = []
    for m in msgs:
        if user_filter and m.user not in user_filter:
            continue
        if contains and contains.lower() not in (m.text or "").lower():
            continue
        shown.append(m)
        if len(shown) >= limit:
            break

    st.caption(f"Showing {len(shown)} messages (out of {len(msgs)})")

    for m in shown:
        header = f"{m.user or 'Unknown'}"
        if m.meta:
            header += f" • {m.meta}"
        with st.container(border=True):
            st.markdown(f"**{header}**")
            st.write(m.text or "")

if __name__ == "__main__":
    main()
