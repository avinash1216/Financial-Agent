# dashboard/streamlit_app.py
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # adjust if file is elsewhere
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)


import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from app.db import SessionLocal
from app.models import PayslipRecord
from typing import Optional

# top of app/dashboards/streamlit_app.py (insert before any other imports)



st.set_page_config(page_title="Payslip Dashboard", layout="wide", initial_sidebar_state="expanded")

CURRENCY = "₹"

def to_float_safe(x: Optional[float]):
    try:
        if x is None:
            return np.nan
        return float(x)
    except Exception:
        return np.nan

@st.cache_data(ttl=300)
def load_data_from_db():
    """Load payslip records from DB and return normalized DataFrame."""
    session = SessionLocal()
    try:
        rows = session.query(PayslipRecord).all()
        if not rows:
            return pd.DataFrame()
        records = []
        for r in rows:
            records.append({
                "filename": r.raw.filename if r.raw else None,
                "month_raw": r.month,
                "pay_date": r.pay_date,
                "gross_salary": to_float_safe(r.gross_salary),
                "net_pay": to_float_safe(r.net_pay),
                "tds": to_float_safe(r.tds),
                "pf_employee": to_float_safe(r.pf_employee),
                "pf_employer": to_float_safe(r.pf_employer),
                "components_json": r.components_json or "{}",
            })
        df = pd.DataFrame(records)

        # Normalize month -> datetime (prefer pay_date if present)
        def parse_month(row):
            # try pay_date first
            if row.get("pay_date"):
                try:
                    return pd.to_datetime(row["pay_date"])
                except Exception:
                    pass
            # try YYYY-MM
            m = row.get("month_raw")
            if not m:
                return pd.NaT
            try:
                # allow YYYY-MM or MMM YYYY or other human forms
                return pd.to_datetime(m, format="%Y-%m", errors="coerce") \
                    .fillna(pd.to_datetime(m, errors="coerce"))
            except Exception:
                return pd.NaT

        df["date"] = df.apply(parse_month, axis=1)
        # Use YYYY-MM label for display/sorting
        df["month"] = df["date"].dt.to_period("M").astype(str)
        # computed fields
        df["savings"] = df["gross_salary"] - df["net_pay"]
        df["savings_rate"] = (df["savings"] / df["gross_salary"]).replace([np.inf, -np.inf], np.nan)
        # sort by date ascending
        df = df.sort_values("date").reset_index(drop=True)
        return df
    finally:
        session.close()

def money(x):
    if pd.isna(x):
        return "-"
    return f"{CURRENCY}{x:,.2f}"

# Load data
df = load_data_from_db()

st.title("Payslip Dashboard")
st.markdown("Interactive view of your parsed payslips — totals, trends, and downloadable data.")

if df.empty:
    st.info("No records found. Run the extractor first and ensure your DB is configured.")
    st.stop()

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    months = sorted(df["month"].dropna().unique())
    if months:
        default_start = months[0]
        default_end = months[-1]
    else:
        default_start = default_end = None

    # Date range using the parsed date
    min_date = df["date"].min()
    max_date = df["date"].max()
    date_from, date_to = st.date_input("Date range (inclusive)", [min_date.date(), max_date.date()] if pd.notna(min_date) else [None, None])
    # quick month picker (multi-select)
    selected_months = st.multiselect("Select months (optional)", months, default=None)

    st.write("---")
    st.caption("Download or sort the table below. Use filters to focus on a specific period.")

# Apply filters
filtered = df.copy()
try:
    if date_from and date_to:
        # Convert date inputs to datetimes
        start_dt = pd.to_datetime(date_from)
        end_dt = pd.to_datetime(date_to)
        filtered = filtered[(filtered["date"] >= start_dt) & (filtered["date"] <= end_dt)]
    if selected_months:
        filtered = filtered[filtered["month"].isin(selected_months)]
except Exception:
    # if filtering fails, keep original
    pass

if filtered.empty:
    st.warning("No payslip records match the selected filters.")
    st.stop()

# KPIs row
total_gross = filtered["gross_salary"].sum(min_count=1)
total_net = filtered["net_pay"].sum(min_count=1)
total_tds = filtered["tds"].sum(min_count=1)
avg_savings_rate = filtered["savings_rate"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Gross", money(total_gross))
col2.metric("Total Net", money(total_net))
col3.metric("Total TDS", money(total_tds))
col4.metric("Avg Savings Rate", f"{(avg_savings_rate * 100):.2f}%" if not pd.isna(avg_savings_rate) else "-")

st.divider()

# Charts and visuals
chart_col1, chart_col2 = st.columns([2, 1])

with chart_col1:
    st.subheader("Gross vs Net (by month)")
    ts = filtered.groupby("month").agg({"gross_salary": "sum", "net_pay": "sum"}).reset_index()
    ts = ts.sort_values("month")
    st.line_chart(ts.set_index("month")[["gross_salary", "net_pay"]])

    st.subheader("Savings over time")
    sav = filtered.groupby("month").agg({"savings": "sum"}).reset_index().sort_values("month")
    st.area_chart(sav.set_index("month")["savings"])

with chart_col2:
    st.subheader("TDS by Month")
    tds = filtered.groupby("month").agg({"tds": "sum"}).reset_index().sort_values("month")
    st.bar_chart(tds.set_index("month")["tds"])

    st.subheader("Top Deductions / Components (sample)")
    # Extract top components across filtered rows (components_json stored as string)
    comp_series = {}
    for s in filtered["components_json"].dropna():
        try:
            d = pd.json.loads(s) if isinstance(s, str) else s
        except Exception:
            # try using json
            import json
            try:
                d = json.loads(s)
            except Exception:
                d = {}
        if isinstance(d, dict):
            for k,v in d.items():
                try:
                    val = float(str(v).replace(",", "").replace("₹", "").strip())
                except Exception:
                    continue
                comp_series[k] = comp_series.get(k, 0.0) + val
    # show top 5
    if comp_series:
        top5 = sorted(comp_series.items(), key=lambda x: -x[1])[:5]
        comp_df = pd.DataFrame(top5, columns=["component", "total"])
        comp_df["total_formatted"] = comp_df["total"].apply(money)
        st.table(comp_df[["component", "total_formatted"]].rename(columns={"total_formatted": "total"}))
    else:
        st.write("No component breakdown available.")

st.divider()

# Data table with download option
st.subheader("Detailed payslip records")
display_df = filtered[["filename", "month", "gross_salary", "net_pay", "tds", "pf_employee", "pf_employer", "savings", "savings_rate"]].copy()
# formatting
display_df["gross_salary"] = display_df["gross_salary"].apply(lambda x: money(x))
display_df["net_pay"] = display_df["net_pay"].apply(lambda x: money(x))
display_df["tds"] = display_df["tds"].apply(lambda x: money(x))
display_df["pf_employee"] = display_df["pf_employee"].apply(lambda x: money(x))
display_df["pf_employer"] = display_df["pf_employer"].apply(lambda x: money(x))
display_df["savings"] = display_df["savings"].apply(lambda x: money(x))
display_df["savings_rate"] = display_df["savings_rate"].apply(lambda x: f"{(x*100):.2f}%" if not pd.isna(x) else "-")

st.dataframe(display_df.sort_values("month", ascending=False), use_container_width=True)

# CSV download
csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered CSV", data=csv_bytes, file_name="payslip_filtered.csv", mime="text/csv")

st.caption("Pro tip: use filters on the left to focus on specific months or date ranges.")
