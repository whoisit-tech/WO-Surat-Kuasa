# =====================================================
# APPS WO - SURAT KUASA DASHBOARD (FINAL VERSION)
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

    # Datetime
    df['assign_date'] = pd.to_datetime(df['assign_date'], errors='coerce')
    df['finish_date'] = pd.to_datetime(df['finish_date'], errors='coerce')

    # Overdue clean
    df['overdue_clean'] = (
        df['overdue']
        .astype(str)
        .str.extract(r'(\d+)')
        .astype(float)
    )

    # Status mapping
    sukses_status = ['EARLY_TERMINATION', 'CREDIT_SETTLEMENT_PROCESS']
    gagal_status = ['CANCEL', 'ASSIGNMENT_LETTER']

    df['hasil'] = np.where(
        df['status'].isin(sukses_status), 'SUKSES',
        np.where(df['status'].isin(gagal_status), 'GAGAL', 'LAINNYA')
    )

    # SLA (hari FIX)
    df['sla_days_exact'] = (
        (df['finish_date'] - df['assign_date'])
        .dt.total_seconds() / (24*3600)
    )

    # Bulan
    df['bulan'] = df['assign_date'].dt.to_period('M').astype(str)

    return df

df = load_data()

# =====================================================
# SIDEBAR FILTER
# =====================================================
st.sidebar.header(" Filter")

bulan_selected = st.sidebar.multiselect(
    "Bulan",
    sorted(df['bulan'].dropna().unique()),
    default=sorted(df['bulan'].dropna().unique())
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

tipe_surat_selected = st.sidebar.multiselect(
    "Tipe Surat",
    df['tipe_surat'].dropna().unique(),
    default=df['tipe_surat'].dropna().unique(),
)

search_kontrak = st.sidebar.text_input("Search No Kontrak")

filtered = df[
    (df['bulan'].isin(bulan_selected)) &
    (df['collector_type'].isin(collector_type)) &
    (df['branch_city'].isin(branch_city)) &
    (df['hasil'].isin(status_filter)) &
    (df['tipe_surat'].isin(tipe_surat_selected))
]

if search_kontrak:
    filtered = filtered[
        filtered['NoKontrak'].astype(str).str.contains(search_kontrak, case=False)
    ]

# =====================================================
# KPI SUMMARY
# =====================================================
total_sk = len(filtered)
total_kontrak = filtered['NoKontrak'].nunique()

sk_per_kontrak = filtered.groupby('NoKontrak').size().reset_index(name='total_sk')
sk_1x = sk_per_kontrak.query('total_sk == 1')
sk_gt1 = sk_per_kontrak.query('total_sk > 1')

sukses = filtered[filtered['hasil'] == 'SUKSES']
gagal = filtered[filtered['hasil'] == 'GAGAL']

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total SK", total_sk)
col2.metric("Total No Kontrak", total_kontrak)
col3.metric("SK Sukses", f"{len(sukses)} ({len(sukses)/total_sk*100:.1f}%)")
col4.metric("SK Gagal", f"{len(gagal)} ({len(gagal)/total_sk*100:.1f}%)")
col5.metric("No Kontrak SK 1x", len(sk_1x))
col6.metric("No Kontrak SK >1x", len(sk_gt1))

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
        total_sla_days=('sla_days_exact', 'sum')
    )
    .reset_index()
)

region_perf['avg_cetak_sk'] = region_perf['total_sk'] / region_perf['total_kontrak']
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
        total_sla_days=('sla_days_exact', 'sum')
    )
    .reset_index()
)

collector_perf['avg_cetak_sk'] = collector_perf['total_sk'] / collector_perf['total_kontrak']
collector_perf['sukses_%'] = collector_perf['sukses'] / collector_perf['total_sk'] * 100
collector_perf['gagal_%'] = collector_perf['gagal'] / collector_perf['total_sk'] * 100

st.dataframe(collector_perf)

# =====================================================
# NO KONTRAK PERFORMANCE (FINAL VERSION)
# =====================================================
st.subheader(" Performance per No Kontrak")

kontrak_perf = (
    filtered
    .groupby('NoKontrak')
    .agg(
        region=('branch_city', 'first'),
        tipe_surat=('tipe_surat', lambda x: ', '.join(x.dropna().unique())),
        total_sk=('NoKontrak', 'count'),
        sukses=('hasil', lambda x: (x == 'SUKSES').sum()),
        gagal=('hasil', lambda x: (x == 'GAGAL').sum()),
        sla_sukses_days=(
            'sla_days_exact',
            lambda x: x[filtered.loc[x.index, 'hasil'] == 'SUKSES'].sum()
        )
    )
    .reset_index()
)

st.dataframe(kontrak_perf)

# =====================================================
# TOP 10 VISUALIZATION
# =====================================================
st.subheader(" Top 10 Region (Total SK)")
fig_r = px.bar(region_perf.sort_values('total_sk', ascending=False).head(10),
               x='branch_city', y='total_sk')
st.plotly_chart(fig_r, use_container_width=True)

st.subheader(" Top 10 Professional Collector")
fig_c = px.bar(collector_perf.sort_values('total_sk', ascending=False).head(10),
               x='professional_collector', y='total_sk')
st.plotly_chart(fig_c, use_container_width=True)

st.subheader(" Top 10 No Kontrak (Cetak SK Terbanyak)")
top_kontrak = sk_per_kontrak.sort_values('total_sk', ascending=False).head(10)
fig_k = px.bar(top_kontrak, x='NoKontrak', y='total_sk')
st.plotly_chart(fig_k, use_container_width=True)

# =====================================================
# RAW DATA (FILTERED)
# =====================================================
st.subheader(" Raw Data (Filtered)")
st.dataframe(filtered)







