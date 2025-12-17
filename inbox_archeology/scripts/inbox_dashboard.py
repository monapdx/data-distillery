import os
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Inbox Archeology Dashboard", layout="wide")

# If set, overrides where we read CSV outputs from
# e.g. set INBOX_ARCH_OUTPUT_DIR=C:\path\to\workspace\output
OUTPUT_OVERRIDE = os.environ.get("INBOX_ARCH_OUTPUT_DIR", "").strip()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = (BASE_DIR.parent / "output").resolve()  # inbox_archeology/output
OUTPUT_DIR = Path(OUTPUT_OVERRIDE).resolve() if OUTPUT_OVERRIDE else DEFAULT_OUTPUT_DIR

REL_CLEAN = OUTPUT_DIR / "relationships_clean.csv"
CORE_TL = OUTPUT_DIR / "core_timeline.csv"

def safe_read_csv(path: Path):
    if not path.exists():
        st.error(f"Missing file: {path}")
        st.stop()
    return pd.read_csv(path)

def tier_from_total(total):
    if total >= 100:
        return "CORE"
    elif total >= 25:
        return "RECURRING"
    else:
        return "PERIPHERAL"

def recip_class(sent, recv):
    if recv == 0:
        return "NO_RECEIVE"
    r = sent / recv
    if r > 1.5:
        return "MOSTLY_ME"
    elif r < 0.67:
        return "MOSTLY_THEM"
    else:
        return "BALANCED"

def normalize_email_label(email: str, hide: bool):
    if not isinstance(email, str):
        return ""
    if not hide:
        return email
    if "@" in email:
        _local, domain = email.split("@", 1)
        return "●●●@" + domain
    return "●●●"

st.sidebar.header("Filters")
st.sidebar.caption(f"Reading outputs from: {OUTPUT_DIR}")

hide_labels = st.sidebar.toggle("Hide labels (anonymize)", value=True)

tier_opts = ["CORE", "RECURRING", "PERIPHERAL"]
tiers = st.sidebar.multiselect("Tiers", tier_opts, default=["CORE", "RECURRING"])

recip_opts = ["MOSTLY_ME", "BALANCED", "MOSTLY_THEM", "NO_RECEIVE"]
recips = st.sidebar.multiselect("Reciprocity classes", recip_opts, default=recip_opts)

rel = safe_read_csv(REL_CLEAN)
rel["total_messages"] = rel["total_messages"].fillna(0).astype(int)
rel["sent_by_me"] = rel["sent_by_me"].fillna(0).astype(int)
rel["received_by_me"] = rel["received_by_me"].fillna(0).astype(int)
rel["first_contact"] = pd.to_datetime(rel["first_contact"], errors="coerce", utc=True)
rel["last_contact"] = pd.to_datetime(rel["last_contact"], errors="coerce", utc=True)

rel["tier"] = rel["total_messages"].apply(tier_from_total)
rel["recip_ratio"] = np.where(rel["received_by_me"] == 0, np.nan, rel["sent_by_me"] / rel["received_by_me"])
rel["recip_class"] = [recip_class(s, r) for s, r in zip(rel["sent_by_me"], rel["received_by_me"])]
rel["duration_days"] = (rel["last_contact"] - rel["first_contact"]).dt.days
rel["duration_years"] = rel["duration_days"] / 365.25

core_tl = safe_read_csv(CORE_TL)
core_tl["start"] = pd.to_datetime(core_tl["start"], errors="coerce", utc=True)
core_tl["end"] = pd.to_datetime(core_tl["end"], errors="coerce", utc=True)
core_tl["total_messages"] = core_tl["total_messages"].fillna(0).astype(int)

min_date = pd.to_datetime(rel["first_contact"].min(), utc=True)
max_date = pd.to_datetime(rel["last_contact"].max(), utc=True)
if pd.isna(min_date) or pd.isna(max_date):
    st.warning("Could not infer date range. Some dates may be missing.")
    min_date = pd.Timestamp("2000-01-01", tz="UTC")
    max_date = pd.Timestamp.utcnow().tz_localize("UTC")

start_date, end_date = st.sidebar.slider(
    "Time window (UTC)",
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime(),
    value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
)

min_messages = st.sidebar.slider("Min total messages", 1, int(rel["total_messages"].max()), 5)

f = rel.copy()
f = f[f["tier"].isin(tiers)]
f = f[f["recip_class"].isin(recips)]
f = f[f["total_messages"] >= min_messages]
f = f[(f["first_contact"] <= pd.to_datetime(end_date, utc=True)) & (f["last_contact"] >= pd.to_datetime(start_date, utc=True))]
f["label"] = f["email"].apply(lambda e: normalize_email_label(e, hide_labels))

st.title("Inbox Archeology — Exploratory Dashboard")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Relationships (filtered)", f"{len(f):,}")
c2.metric("CORE (filtered)", f"{(f['tier']=='CORE').sum():,}")
c3.metric("Balanced (filtered)", f"{(f['recip_class']=='BALANCED').sum():,}")
c4.metric("Mostly inbound (filtered)", f"{(f['recip_class']=='MOSTLY_THEM').sum():,}")

st.divider()

left, right = st.columns([1.15, 0.85], gap="large")

with left:
    st.subheader("Timeline (Gantt-style)")
    tl = f.dropna(subset=["first_contact", "last_contact"]).copy()
    tl = tl.sort_values(["first_contact", "total_messages"], ascending=[True, False])

    top_n = st.slider("Max bars shown (for readability)", 20, 200, 80)
    tl = tl.head(top_n)

    fig_tl = px.timeline(
        tl,
        x_start="first_contact",
        x_end="last_contact",
        y="label",
        color="tier",
        hover_data={
            "email": False if hide_labels else True,
            "total_messages": True,
            "sent_by_me": True,
            "received_by_me": True,
            "recip_ratio": ":.2f",
            "recip_class": True,
            "duration_days": True,
            "first_contact": True,
            "last_contact": True,
        },
    )
    fig_tl.update_yaxes(autorange="reversed", title="")
    fig_tl.update_xaxes(title="")
    fig_tl.update_layout(height=650, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_tl, use_container_width=True)

with right:
    st.subheader("CORE Density by Year")
    core_for_density = rel[rel["tier"] == "CORE"].dropna(subset=["first_contact", "last_contact"]).copy()
    core_for_density = core_for_density[
        (core_for_density["first_contact"] <= pd.to_datetime(end_date, utc=True)) &
        (core_for_density["last_contact"] >= pd.to_datetime(start_date, utc=True))
    ]

    years = range(pd.to_datetime(start_date, utc=True).year, pd.to_datetime(end_date, utc=True).year + 1)
    density = []
    for y in years:
        y_start = pd.Timestamp(f"{y}-01-01", tz="UTC")
        y_end = pd.Timestamp(f"{y}-12-31", tz="UTC")
        active = ((core_for_density["first_contact"] <= y_end) & (core_for_density["last_contact"] >= y_start)).sum()
        density.append({"year": y, "active_core": int(active)})

    dens = pd.DataFrame(density)
    fig_den = px.line(dens, x="year", y="active_core", markers=True)
    fig_den.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    fig_den.update_xaxes(dtick=1)
    st.plotly_chart(fig_den, use_container_width=True)

    st.subheader("Reciprocity (Sent vs Received)")
    scat = f.copy()
    fig_rec = px.scatter(
        scat,
        x="received_by_me",
        y="sent_by_me",
        color="tier",
        symbol="recip_class",
        size="total_messages",
        hover_data={
            "label": True,
            "email": False if hide_labels else True,
            "total_messages": True,
            "duration_years": ":.2f",
            "recip_ratio": ":.2f",
            "recip_class": True,
        },
        log_x=True,
        log_y=True,
    )
    fig_rec.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    fig_rec.update_xaxes(title="Received by me (log)")
    fig_rec.update_yaxes(title="Sent by me (log)")
    st.plotly_chart(fig_rec, use_container_width=True)

st.divider()

st.subheader("Lifecycle: Duration vs Volume")
life = f.dropna(subset=["duration_days"]).copy()
fig_life = px.scatter(
    life,
    x="duration_years",
    y="total_messages",
    color="recip_class",
    symbol="tier",
    hover_data={
        "label": True,
        "email": False if hide_labels else True,
        "sent_by_me": True,
        "received_by_me": True,
        "recip_ratio": ":.2f",
        "first_contact": True,
        "last_contact": True,
    },
)
fig_life.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10))
fig_life.update_xaxes(title="Duration (years)")
fig_life.update_yaxes(title="Total messages")
st.plotly_chart(fig_life, use_container_width=True)

with st.expander("Table (filtered relationships)"):
    show_cols = ["label","tier","total_messages","sent_by_me","received_by_me","recip_ratio","recip_class","duration_years","first_contact","last_contact"]
    st.dataframe(f[show_cols].sort_values("total_messages", ascending=False), use_container_width=True)
