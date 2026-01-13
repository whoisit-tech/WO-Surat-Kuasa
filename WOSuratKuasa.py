# =====================================================
# WO SURAT KUASA MONITORING DASHBOARD – SLA SUKSES (FINAL)
# =====================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="WO SK Monitoring",
    page_icon="",
    layout="wide"
)

st.title("Dashboard Monitoring Surat Kuasa (WO)")
st.caption("Fokus SLA Kontrak Sukses Periode Tahun 2025")

# =====================================================
# HELPER
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
# BUSINESS RULE
# =====================================================
SUCCESS_STATUS = ["EARLY_TERMINATION", "CREDIT_SETTLEMENT_PROCESS"]

df["status_sk"] = np.where(
    df["status"].isin(SUCCESS_STATUS),
    "Sukses",
    "Gagal"
)

df["is_success"] = (df["status_sk"] == "Sukses").astype(int)

# =====================================================
# FEATURE ENGINEERING
# =====================================================
# SLA
df["sla_hari"] = (df["finish_date"] - df["assign_date"]).dt.days

# Overdue
df["overdue_num"] = (
    df["overdue"]
    .astype(str)
    .str.extract(r"(\d+)")
    .astype(float)
)

df["overdue_bucket"] = np.where(
    df["overdue_num"] < 90,
    "OVD < 90",
    "OVD ≥ 90"
)

# Month
df["month"] = df["assign_date"].dt.to_period("M").astype(str)

# Frekuensi Cetak SK
cetak = (
    df.groupby("NoKontrak")
    .size()
    .reset_index(name="jumlah_cetak")
)

df = df.merge(cetak, on="NoKontrak", how="left")

df["kategori_cetak"] = np.where(
    df["jumlah_cetak"] > 1,
    "Cetak > 1x",
    "Cetak 1x"
)

# =====================================================
# SIDEBAR FILTER
# =====================================================
with st.sidebar:
    st.header("🔍 Filter Data")

    start_date, end_date = st.date_input(
        "Assign Date",
        value=(df["assign_date"].min(), df["assign_date"].max())
    )

    region = st.multiselect(
        "Branch / Region",
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
if status_filter:
    df = df[df["status_sk"].isin(status_filter)]
if search_kontrak:
    df = df[df["NoKontrak"].astype(str).str.contains(search_kontrak)]

# =====================================================
# DATA SUKSES ONLY (UNTUK SLA)
# =====================================================
df_sukses = df[df["status_sk"] == "Sukses"]

# =====================================================
# KPI UTAMA
# =====================================================
total_sk = len(df)
total_kontrak = df["NoKontrak"].nunique()
success_sk = df["is_success"].sum()
failed_sk = total_sk - success_sk
success_rate = pct(success_sk, total_sk)

median_sla = df_sukses["sla_hari"].median()
min_sla = df_sukses["sla_hari"].min()
max_sla = df_sukses["sla_hari"].max()
sla_30 = pct((df_sukses["sla_hari"] <= 30).sum(), len(df_sukses))

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total SK", f"{total_sk:,}")
c2.metric("Total Kontrak", f"{total_kontrak:,}")
c3.metric("SK Sukses", f"{success_sk:,}")
c4.metric("SK Gagal", f"{failed_sk:,}")
c5.metric("Success Rate", f"{success_rate}%")
c6.metric(
    "Median SLA Sukses (Hari)",
    f"{int(median_sla)}",
    help=f"Min: {int(min_sla)} | Max: {int(max_sla)} | ≤30 Hari: {sla_30}%"
)

st.divider()

# =====================================================
# DISTRIBUSI STATUS
# =====================================================
fig_status = px.pie(
    df,
    names="status_sk",
    title="Distribusi Status SK"
)
st.plotly_chart(fig_status, use_container_width=True)

# =====================================================
# DISTRIBUSI SLA SUKSES
# =====================================================
fig_sla = px.histogram(
    df_sukses,
    x="sla_hari",
    nbins=20,
    title="Distribusi Lama SLA Kontrak Sukses (Hari)"
)
st.plotly_chart(fig_sla, use_container_width=True)

# =====================================================
# SLA SUKSES BY OVERDUE
# =====================================================
sla_ovd = (
    df_sukses.groupby("overdue_bucket")
    .agg(
        kontrak=("NoKontrak", "nunique"),
        median_sla=("sla_hari", "median"),
        min_sla=("sla_hari", "min"),
        max_sla=("sla_hari", "max")
    )
    .reset_index()
)

st.subheader("⏱ SLA Sukses berdasarkan Overdue")
st.dataframe(sla_ovd, use_container_width=True)

# =====================================================
# SLA SUKSES BY FREKUENSI CETAK
# =====================================================
sla_cetak = (
    df_sukses.groupby("kategori_cetak")
    .agg(
        kontrak=("NoKontrak", "nunique"),
        median_sla=("sla_hari", "median"),
        min_sla=("sla_hari", "min"),
        max_sla=("sla_hari", "max")
    )
    .reset_index()
)

st.subheader(" SLA Sukses berdasarkan Frekuensi Cetak SK")
st.dataframe(sla_cetak, use_container_width=True)

# =====================================================
# REGION PERFORMANCE (SLA SUKSES)
# =====================================================
region_perf = (
    df.groupby("branch_city")
    .agg(
        total_sk=("NoKontrak", "count"),
        sukses=("is_success", "sum")
    )
    .reset_index()
)

region_perf["success_rate_%"] = region_perf.apply(
    lambda x: pct(x["sukses"], x["total_sk"]), axis=1
)

region_sla = (
    df_sukses.groupby("branch_city")
    .agg(
        median_sla=("sla_hari", "median"),
        min_sla=("sla_hari", "min"),
        max_sla=("sla_hari", "max")
    )
    .reset_index()
)

region_perf = region_perf.merge(region_sla, on="branch_city", how="left")

st.subheader(" Region Performance (SLA Sukses)")
st.dataframe(
    region_perf.sort_values("total_sk", ascending=False).head(10),
    use_container_width=True
)

# =====================================================
# COLLECTOR PERFORMANCE (SLA SUKSES)
# =====================================================
collector_perf = (
    df.groupby("professional_collector")
    .agg(
        total_sk=("NoKontrak", "count"),
        sukses=("is_success", "sum")
    )
    .reset_index()
)

collector_perf["success_rate_%"] = collector_perf.apply(
    lambda x: pct(x["sukses"], x["total_sk"]), axis=1
)

collector_sla = (
    df_sukses.groupby("professional_collector")
    .agg(
        median_sla=("sla_hari", "median"),
        min_sla=("sla_hari", "min"),
        max_sla=("sla_hari", "max")
    )
    .reset_index()
)

collector_perf = collector_perf.merge(
    collector_sla,
    on="professional_collector",
    how="left"
)

st.subheader(" Top 10 Professional Collector (SLA Sukses)")
st.dataframe(
    collector_perf.sort_values("total_sk", ascending=False).head(10),
    use_container_width=True
)

# =====================================================
# TREND BULANAN
# =====================================================
trend = (
    df.groupby(["month", "status_sk"])
    .size()
    .reset_index(name="total_sk")
)

fig_trend = px.line(
    trend,
    x="month",
    y="total_sk",
    color="status_sk",
    markers=True,
    title="Trend SK Bulanan"
)
st.plotly_chart(fig_trend, use_container_width=True)

# =====================================================
# RAW DATA
# =====================================================
with st.expander("📄 Raw Data"):
    st.dataframe(df, use_container_width=True)
