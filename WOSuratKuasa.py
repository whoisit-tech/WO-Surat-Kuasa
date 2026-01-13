# =====================================================
# EXECUTIVE SK MONITORING DASHBOARD (FINAL VERSION)
# =====================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Executive SK Monitoring",
    layout="wide"
)

st.title(" Dashboard Monitoring Surat Kuasa (SK)")
st.caption("Periode Januari - Desember 2025")

# =====================================================
# HELPER FUNCTION
# =====================================================
def pct(a, b):
    return round(a / b * 100, 2) if b else 0

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_excel("AppsWO.xlsx")

    for col in ["assign_date", "finish_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

df = load_data()

# =====================================================
# DATA CLEANING
# =====================================================
# Overdue numeric
df["overdue_num"] = (
    df["overdue"]
    .astype(str)
    .str.extract(r"(\d+)")
    .astype(float)
)

# Overdue bucket
df["overdue_bucket"] = pd.cut(
    df["overdue_num"],
    bins=[0,30,60,90,120,9999],
    labels=["0-30","31-60","61-90","91-120",">120"],
    include_lowest=True
)

# =====================================================
# BUSINESS RULE
# =====================================================
SUCCESS_STATUS = ["EARLY_TERMINATION", "CREDIT_SETTLEMENT_PROCESS"]

df["status_sk"] = np.where(
    df["status"].isin(SUCCESS_STATUS),
    "Sukses",
    "Gagal"
)

df["is_success"] = (df["status_sk"] == "Sukses").astype(int)

# Month
df["month"] = df["assign_date"].dt.to_period("M").astype(str)

# SLA (hari)
df["sla_hari"] = (df["finish_date"] - df["assign_date"]).dt.days

# =====================================================
# CETAK SK > 1 (PER NO KONTRAK)
# =====================================================
sk_per_kontrak = (
    df.groupby("NoKontrak")
    .size()
    .reset_index(name="jumlah_cetak_sk")
)

sk_per_kontrak["is_multi_sk"] = np.where(
    sk_per_kontrak["jumlah_cetak_sk"] > 1, 1, 0
)

df = df.merge(sk_per_kontrak, on="NoKontrak", how="left")

# =====================================================
# SIDEBAR FILTER
# =====================================================
with st.sidebar:
    st.header(" Filter Data")

    min_date = df["assign_date"].min()
    max_date = df["assign_date"].max()

    start_date, end_date = st.date_input(
        "Assign Date",
        value=(min_date, max_date)
    )

    region = st.multiselect(
        "Region / Branch",
        sorted(df["branch_city"].dropna().unique())
    )

    collector = st.multiselect(
        "Professional Collector",
        sorted(df["professional_collector"].dropna().unique())
    )

    collector_type = st.multiselect(
        "Collector Type",
        sorted(df["collector_type"].dropna().unique())
    )

    status_filter = st.multiselect(
        "Status SK",
        ["Sukses", "Gagal"],
        default=["Sukses", "Gagal"]
    )

    search_kontrak = st.text_input(" Search No Kontrak")

# =====================================================
# APPLY FILTER
# =====================================================
df = df[
    (df["assign_date"] >= pd.to_datetime(start_date)) &
    (df["assign_date"] <= pd.to_datetime(end_date))
]

if region:
    df = df[df["branch_city"].isin(region)]

if collector:
    df = df[df["professional_collector"].isin(collector)]

if collector_type:
    df = df[df["collector_type"].isin(collector_type)]

df = df[df["status_sk"].isin(status_filter)]

if search_kontrak:
    df = df[df["NoKontrak"].astype(str).str.contains(search_kontrak)]

# =====================================================
# EXECUTIVE KPI
# =====================================================
total_sk = len(df)
total_kontrak = df["NoKontrak"].nunique()
success_sk = df["is_success"].sum()
success_rate = pct(success_sk, total_sk)

multi_sk_kontrak = df[df["is_multi_sk"] == 1]["NoKontrak"].nunique()
multi_sk_rate = pct(multi_sk_kontrak, total_kontrak)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total SK", f"{total_sk:,}")
c2.metric("Total Kontrak", f"{total_kontrak:,}")
c3.metric("SK Sukses", f"{success_sk:,}")
c4.metric("Success Rate", f"{success_rate}%")
c5.metric("Kontrak Cetak SK >1", f"{multi_sk_kontrak:,}")

st.divider()

# =====================================================
# TREND BULANAN
# =====================================================
trend = (
    df.groupby(["month","status_sk"])
    .size()
    .reset_index(name="jumlah")
)

fig_trend = px.line(
    trend,
    x="month",
    y="jumlah",
    color="status_sk",
    markers=True,
    title="Trend SK Bulanan"
)
st.plotly_chart(fig_trend, use_container_width=True)

# =====================================================
# REGION EFFECTIVENESS (DIGABUNG)
# =====================================================
region_perf = (
    df.groupby("branch_city")
    .agg(
        total_sk=("NoKontrak","count"),
        total_kontrak=("NoKontrak","nunique"),
        sukses=("is_success","sum"),
        kontrak_multi_sk=("is_multi_sk","sum"),
        sla=("sla_hari","count")
    )
    .reset_index()
)

region_perf["success_rate_%"] = region_perf.apply(
    lambda x: pct(x["sukses"], x["total_sk"]), axis=1
)

region_perf["multi_sk_rate_%"] = region_perf.apply(
    lambda x: pct(x["kontrak_multi_sk"], x["total_kontrak"]), axis=1
)

st.subheader(" Region Performance Summary")
st.dataframe(
    region_perf.sort_values("total_sk", ascending=False),
    use_container_width=True
)

# =====================================================
# COLLECTOR PERFORMANCE
# =====================================================
collector_perf = (
    df.groupby("professional_collector")
    .agg(
        total_sk=("NoKontrak","count"),
        total_kontrak=("NoKontrak","nunique"),
        sukses=("is_success","sum"),
        sla=("sla_hari","count"),
        
    )
    .reset_index()
)

collector_perf["success_rate_%"] = collector_perf.apply(
    lambda x: pct(x["sukses"], x["total_sk"]), axis=1
)

st.subheader(" Professional Collector Performance")
st.dataframe(
    collector_perf.sort_values("total_sk", ascending=False).head(10),
    use_container_width=True
)

# =====================================================
# OVERDUE vs STATUS
# =====================================================
bucket_perf = (
    df.groupby(["overdue_bucket","status_sk"])
    .size()
    .reset_index(name="jumlah")
)

fig_bucket = px.bar(
    bucket_perf,
    x="overdue_bucket",
    y="jumlah",
    color="status_sk",
    barmode="group",
    title="Overdue Bucket vs Status SK"
)
st.plotly_chart(fig_bucket, use_container_width=True)

# =====================================================
# RAW DATA
# =====================================================
with st.expander(" Raw Data Detail"):

    st.dataframe(df, use_container_width=True)
