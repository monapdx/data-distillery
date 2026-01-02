import json
from datetime import datetime
from typing import List, Dict

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Google Search History Browser",
    layout="wide",
)


@st.cache_data
def load_search_history(file) -> pd.DataFrame:
    """
    Load a Google MyActivity JSON file and return a DataFrame
    with only Search entries and parsed timestamps.
    """
    data = json.load(file)  # UploadedFile works directly with json.load

    rows: List[Dict] = []

    for item in data:
        # Keep only Search entries
        if item.get("header") != "Search":
            continue

        time_str = item.get("time")
        if not time_str:
            continue

        # Example: "2025-01-05T07:16:52.067Z"
        # Replace Z with +00:00 so datetime.fromisoformat can parse it
        try:
            time_clean = time_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(time_clean)
        except Exception:
            # Skip weird/unparseable timestamps
            continue

        title = item.get("title", "")
        url = item.get("titleUrl", "")

        rows.append(
            {
                "datetime": dt,
                "date": dt.date(),
                "year": dt.year,
                "month": dt.month,
                "month_name": dt.strftime("%B"),
                "time_of_day": dt.time().strftime("%H:%M:%S"),
                "query": title,
                "url": url,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Sort newest first by default
    df = df.sort_values("datetime", ascending=False).reset_index(drop=True)
    return df


def main():
    st.title("🔎 Google Search History Browser")

    st.write(
        "Upload your **MyActivity.json** from Google Takeout (the one inside "
        "`Takeout/My Activity/Search/`)."
    )

    uploaded_file = st.file_uploader("Upload MyActivity.json", type="json")

    if not uploaded_file:
        st.info("⏫ Upload your MyActivity.json file to get started.")
        return

    # Load and parse
    df = load_search_history(uploaded_file)

    if df.empty:
        st.warning("No Search entries found in this file.")
        return

    # Sidebar controls
    st.sidebar.header("Filters")

    # Year selector
    years = sorted(df["year"].unique(), reverse=True)
    selected_year = st.sidebar.selectbox("Year", years)

    # Month selector (only those present in that year)
    months_in_year = df.loc[df["year"] == selected_year, ["month", "month_name"]]
    months_in_year = months_in_year.drop_duplicates().sort_values("month")

    month_options = ["All months"] + [
        f"{row.month:02d} - {row.month_name}" for row in months_in_year.itertuples()
    ]
    selected_month_label = st.sidebar.selectbox("Month", month_options)

    # Keyword filter
    keyword = st.sidebar.text_input(
        "Search within queries (optional)",
        placeholder="",
    )

    # Apply filters
    filtered = df[df["year"] == selected_year]

    if selected_month_label != "All months":
        # First two chars are the numeric month
        selected_month_num = int(selected_month_label.split(" - ")[0])
        filtered = filtered[filtered["month"] == selected_month_num]

    if keyword.strip():
        kw = keyword.strip()
        filtered = filtered[filtered["query"].str.contains(kw, case=False, na=False)]

    # Summary / metrics
    st.subheader("Overview")

    total_searches = len(df)
    filtered_searches = len(filtered)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total searches in file", f"{total_searches:,}")
    col2.metric("Searches in current view", f"{filtered_searches:,}")

    if not filtered.empty:
        date_range = f"{filtered['date'].min()} → {filtered['date'].max()}"
    else:
        date_range = "–"

    col3.metric("Date range (current view)", date_range)

    st.subheader("Searches")

    if filtered.empty:
        st.info("No searches match these filters.")
        return

    # Display table
    display_cols = ["datetime", "query", "url"]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    # Download CSV of current filtered view
    csv_name_parts = [str(selected_year)]
    if selected_month_label != "All months":
        csv_name_parts.append(selected_month_label.split(" - ")[0])
    if keyword.strip():
        csv_name_parts.append("search")

    csv_file_name = "searches_" + "_".join(csv_name_parts) + ".csv"

    csv_data = filtered.to_csv(index=False)
    st.download_button(
        "⬇️ Download this view as CSV",
        data=csv_data,
        file_name=csv_file_name,
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
