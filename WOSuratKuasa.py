# =====================================================
# APPS WO - SURAT KUASA DASHBOARD (FULL VERSION)
# =====================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Apps WO Monitoring", layout="wide")
st.title(" Dashboard Monitoring Surat Kuasa (WO)")

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():
    df = pd.read_excel("AppsWO.xlsx")

    # Date parsing
    df['assign_date'] = pd.to_datetime(df['assign_date'], errors='coerce')
    df['finish_date'] = pd.to_datetime(df['finish_date'], errors='coerce')

    # Clean overdue -> numeric only
    df['overdue_clean'] = (
        df['overdue']
        .astype(str)
        .str.extract('(\d+)')
        .astype(float)
    )

    # Status mapping
    sukses_status = ['EARLY_TERMINATION', 'CREDIT_SETTLEMENT_PROCESS']
    gagal_status = ['CANCEL', 'ASSIGNMENT_LETTER']

    df['hasil'] = np.where(
        df['status'].isin(sukses_status), 'SUKSES',
        np.where(df['status'].isin(gagal_status), 'GAGAL', 'LAINNYA')
    )

    # SLA (days)
    df['sla_days'] = (df['finish_date'] - df['assign_date']).dt.days

    # Month
    df['bulan'] = df['assign_date'].dt.to_period('M').astype(str)

    return df

df = load_data()

# =====================================================
# SIDEBAR FILTER
# =====================================================
st.sidebar.header(" Filter")

# Bulan filter
bulan_opt = sorted(df['bulan'].dropna().unique())
bulan_selected = st.sidebar.multiselect(
    "Bulan",
    bulan_opt,
    default=bulan_opt
)

collector_type = st.sidebar.multiselect(
    "Collector Type",
    df['collector_type'].dropna().unique(),
    default=df['collector_type'].dropna().unique()
)

branch_city = st.sidebar.multiselect(
    "Region / Branch",
    df['branch_city'].dropna().unique(),
    default=df['branch_city'].dropna().unique()
)

status_filter = st.sidebar.multiselect(
    "Hasil",
    ['SUKSES', 'GAGAL'],
    default=['SUKSES', 'GAGAL']
)

search_kontrak = st.sidebar.text_input("Search No Kontrak")

filtered = df[
    (df['bulan'].isin(bulan_selected)) &
    (df['collector_type'].isin(collector_type)) &
    (df['branch_city'].isin(branch_city)) &
    (df['hasil'].isin(status_filter))
]

if search_kontrak:
    filtered = filtered[filtered['NoKontrak'].astype(str).str.contains(search_kontrak, case=False)]

# =====================================================
# KPI SUMMARY
# =====================================================

total_sk = len(filtered)
total_kontrak = filtered['NoKontrak'].nunique()

sukses = filtered[filtered['hasil'] == 'SUKSES']
gagal = filtered[filtered['hasil'] == 'GAGAL']

sk_per_kontrak = filtered.groupby('NoKontrak').size().reset_index(name='total_sk')
sk_sekali = sk_per_kontrak.query('total_sk == 1')
sk_lebih_1 = sk_per_kontrak.query('total_sk > 1')

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total SK", total_sk)
col2.metric("Total No Kontrak", total_kontrak)
col3.metric("SK Sukses", f"{len(sukses)} ({len(sukses)/total_sk*100:.1f}%)")
col4.metric("SK Gagal", f"{len(gagal)} ({len(gagal)/total_sk*100:.1f}%)")
col5.metric("No Kontrak SK > 1x", f"{len(sk_lebih_1)} ({len(sk_lebih_1)/total_kontrak*100:.1f}%)")
# =====================================================
total_sk = len(filtered)
total_kontrak = filtered['NoKontrak'].nunique()

sukses = filtered[filtered['hasil'] == 'SUKSES']
gagal = filtered[filtered['hasil'] == 'GAGAL']

sk_multi = (
    filtered.groupby('NoKontrak')
    .size()
    .reset_index(name='total_sk')
    .query('total_sk > 1')
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total SK", total_sk)
col2.metric("Total No Kontrak (Distinct)", total_kontrak)
col3.metric("SK Sukses", f"{len(sukses)} ({len(sukses)/total_sk*100:.1f}%)")
col4.metric("SK Gagal", f"{len(gagal)} ({len(gagal)/total_sk*100:.1f}%)")

# =====================================================
# TREN SK BULANAN
# =====================================================
st.subheader(" Tren SK Bulanan")

trend = (
    filtered
    .groupby(['bulan', 'hasil'])
    .size()
    .reset_index(name='total')
)

fig = px.line(trend, x='bulan', y='total', color='hasil', markers=True)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(trend)

# =====================================================
# REGION PERFORMANCE
# =====================================================
st.subheader(" Region Performance")

region_perf = (
    filtered
    .groupby('branch_city')
    .agg(
        total_sk=('NoKontrak', 'count'),
        total_kontrak=('NoKontrak', 'nunique'),
        sukses=('hasil', lambda x: (x == 'SUKSES').sum()),
        gagal=('hasil', lambda x: (x == 'GAGAL').sum()),
        kontrak_multi_sk=('NoKontrak', lambda x: x.value_counts().gt(1).sum()),
        total_sla=('sla_days', 'sum')
    )
    .reset_index()
)

region_perf['sukses_%'] = region_perf['sukses'] / region_perf['total_sk'] * 100
region_perf['gagal_%'] = region_perf['gagal'] / region_perf['total_sk'] * 100

st.dataframe(region_perf)

# =====================================================
# PROFESSIONAL COLLECTOR PERFORMANCE
# =====================================================
st.subheader(" Professional Collector Performance")

collector_perf = (
    filtered
    .groupby('professional_collector')
    .agg(
        total_sk=('NoKontrak', 'count'),
        total_kontrak=('NoKontrak', 'nunique'),
        sukses=('hasil', lambda x: (x == 'SUKSES').sum()),
        gagal=('hasil', lambda x: (x == 'GAGAL').sum()),
        kontrak_multi_sk=('NoKontrak', lambda x: x.value_counts().gt(1).sum()),
        total_sla=('sla_days', 'sum')
    )
    .reset_index()
)

collector_perf['sukses_%'] = collector_perf['sukses'] / collector_perf['total_sk'] * 100
collector_perf['gagal_%'] = collector_perf['gagal'] / collector_perf['total_sk'] * 100

st.dataframe(collector_perf)

# =====================================================
# NO KONTRAK PERFORMANCE
# =====================================================
st.subheader(" Performance per No Kontrak")

kontrak_perf = (
    filtered
    .groupby('NoKontrak')
    .agg(
        total_sk=('NoKontrak', 'count'),
        region=('branch_city', 'first'),
        sukses=('hasil', lambda x: (x == 'SUKSES').sum()),
        gagal=('hasil', lambda x: (x == 'GAGAL').sum()),
        total_sla=('sla_days', 'sum'),
        avg_overdue=('overdue_clean', 'mean')
    )
    .reset_index()
)

st.dataframe(kontrak_perf)

# =====================================================
# OVERDUE DISTRIBUTION
# =====================================================
st.subheader(" Distribusi Overdue")

fig2 = px.histogram(filtered, x='overdue_clean', nbins=30)
st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# RAW DATA
# =====================================================
st.subheader(" Raw Data")
st.dataframe(filtered)


