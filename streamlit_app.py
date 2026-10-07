import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# KONFIGURASI
# =========================================================

st.set_page_config(
    page_title="Dashboard Harga Pangan Kendari",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>

    /* Background utama */
    .stApp {
        background-color: #f5f7fb;
    }

    /* Header */
    .main-header {
        background: linear-gradient(
            135deg,
            #2563eb 0%,
            #1d4ed8 50%,
            #1e40af 100%
        );
        padding: 30px 35px;
        border-radius: 18px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 8px 25px rgba(37, 99, 235, 0.20);
    }

    .main-header h1 {
        color: white;
        font-size: 36px;
        margin-bottom: 5px;
    }

    .main-header p {
        color: #dbeafe;
        font-size: 16px;
        margin-bottom: 0;
    }

    /* KPI */
    .kpi-card {
        background: white;
        padding: 22px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        min-height: 125px;
    }

    .kpi-title {
        color: #64748b;
        font-size: 14px;
        margin-bottom: 8px;
    }

    .kpi-value {
        color: #1e293b;
        font-size: 28px;
        font-weight: 700;
    }

    .kpi-description {
        color: #94a3b8;
        font-size: 12px;
        margin-top: 5px;
    }

    /* Insight */
    .insight-box {
        background: white;
        border-left: 5px solid #2563eb;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 10px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.04);
    }

    .insight-title {
        font-weight: 700;
        color: #1e293b;
        font-size: 16px;
    }

    .insight-text {
        color: #475569;
        margin-top: 6px;
        line-height: 1.6;
    }

    /* Section title */
    .section-title {
        color: #1e293b;
        font-size: 24px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 15px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 13px;
        padding: 25px;
    }

</style>
""", unsafe_allow_html=True)

# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data
def load_data():

    df = pd.read_csv("dashboard_harga_pangan.csv")

    df["tanggal"] = pd.to_datetime(
        df["tanggal"],
        errors="coerce"
    )

    df["harga"] = pd.to_numeric(
        df["harga"],
        errors="coerce"
    )

    # Kolom cuaca
    kolom_cuaca = [
        "curah_hujan_mm",
        "suhu_rata_rata",
        "suhu_min",
        "suhu_max"
    ]

    for kolom in kolom_cuaca:
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(
                df[kolom],
                errors="coerce"
            )

    df = df.dropna(
        subset=["tanggal", "harga"]
    )

    return df


df = load_data()

# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="main-header">

<h1>📊 Dashboard Harga Pangan Kota Kendari</h1>

<p>
Monitoring dan analisis harga pangan berdasarkan periode,
komoditas, serta kondisi cuaca di Kota Kendari.
</p>

</div>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown("## 🔎 Filter Dashboard")
st.sidebar.markdown("---")

# Komoditas

daftar_komoditas = sorted(
    df["komoditas"]
    .dropna()
    .unique()
)

pilih_komoditas = st.sidebar.multiselect(
    "🥬 Komoditas",
    options=daftar_komoditas,
    default=daftar_komoditas
)

# Tanggal

tanggal_min = df["tanggal"].min().date()
tanggal_max = df["tanggal"].max().date()

rentang_tanggal = st.sidebar.date_input(
    "📅 Periode",
    value=(tanggal_min, tanggal_max),
    min_value=tanggal_min,
    max_value=tanggal_max
)

st.sidebar.markdown("---")

st.sidebar.info(
    "Gunakan filter di atas untuk melihat "
    "perubahan harga pada komoditas dan periode tertentu."
)

# =========================================================
# FILTER DATA
# =========================================================

df_filter = df.copy()

if pilih_komoditas:

    df_filter = df_filter[
        df_filter["komoditas"].isin(
            pilih_komoditas
        )
    ]

else:

    df_filter = df_filter.iloc[0:0]


if isinstance(rentang_tanggal, tuple):

    if len(rentang_tanggal) == 2:

        tanggal_awal = pd.to_datetime(
            rentang_tanggal[0]
        )

        tanggal_akhir = pd.to_datetime(
            rentang_tanggal[1]
        )

        df_filter = df_filter[
            (df_filter["tanggal"] >= tanggal_awal)
            &
            (df_filter["tanggal"] <= tanggal_akhir)
        ]

# =========================================================
# CEK DATA
# =========================================================

if len(df_filter) == 0:

    st.warning(
        "⚠️ Tidak ada data berdasarkan filter yang dipilih."
    )

    st.stop()

# =========================================================
# KPI
# =========================================================

jumlah_data = len(df_filter)

jumlah_komoditas = (
    df_filter["komoditas"].nunique()
)

harga_rata = (
    df_filter["harga"].mean()
)

harga_tertinggi = (
    df_filter["harga"].max()
)

harga_terendah = (
    df_filter["harga"].min()
)

# =========================================================
# KPI CARDS
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.markdown(f"""
    <div class="kpi-card">

    <div class="kpi-title">
    📦 Jumlah Data
    </div>

    <div class="kpi-value">
    {jumlah_data:,}
    </div>

    <div class="kpi-description">
    Data setelah filter
    </div>

    </div>
    """, unsafe_allow_html=True)


with col2:

    st.markdown(f"""
    <div class="kpi-card">

    <div class="kpi-title">
    🥬 Komoditas
    </div>

    <div class="kpi-value">
    {jumlah_komoditas}
    </div>

    <div class="kpi-description">
    Jenis komoditas
    </div>

    </div>
    """, unsafe_allow_html=True)


with col3:

    st.markdown(f"""
    <div class="kpi-card">

    <div class="kpi-title">
    💰 Harga Rata-rata
    </div>

    <div class="kpi-value">
    Rp {harga_rata:,.0f}
    </div>

    <div class="kpi-description">
    Rata-rata seluruh data
    </div>

    </div>
    """, unsafe_allow_html=True)


with col4:

    st.markdown(f"""
    <div class="kpi-card">

    <div class="kpi-title">
    🔝 Harga Tertinggi
    </div>

    <div class="kpi-value">
    Rp {harga_tertinggi:,.0f}
    </div>

    <div class="kpi-description">
    Nilai maksimum
    </div>

    </div>
    """, unsafe_allow_html=True)

# =========================================================
# PERIODE
# =========================================================

st.markdown(
    f"""
    <div style="
        background:#eff6ff;
        padding:15px 20px;
        border-radius:12px;
        margin-top:20px;
        margin-bottom:20px;
        color:#1e40af;
    ">
    📅 <b>Periode data:</b>
    {df_filter["tanggal"].min().strftime("%d %B %Y")}
    –
    {df_filter["tanggal"].max().strftime("%d %B %Y")}
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Tren Harga",
    "🏆 Perbandingan",
    "🌦️ Cuaca",
    "📋 Data"
])

# =========================================================
# TAB 1 — TREN HARGA
# =========================================================

with tab1:

    st.markdown(
        '<div class="section-title">📈 Pergerakan Harga Pangan</div>',
        unsafe_allow_html=True
    )

    tren = (
        df_filter
        .groupby(
            ["tanggal", "komoditas"],
            as_index=False
        )["harga"]
        .mean()
    )

    fig = px.line(
        tren,
        x="tanggal",
        y="harga",
        color="komoditas",
        markers=True,
        labels={
            "tanggal": "Tanggal",
            "harga": "Harga (Rp)",
            "komoditas": "Komoditas"
        }
    )

    fig.update_layout(
        height=500,
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend_title="Komoditas"
    )

    fig.update_yaxes(
        tickprefix="Rp ",
        tickformat=","
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Gunakan filter komoditas di sebelah kiri "
        "untuk membandingkan pergerakan harga tertentu."
    )

    # -----------------------------------------------------
    # INSIGHT OTOMATIS
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">💡 Insight Harga</div>',
        unsafe_allow_html=True
    )

    rata_komoditas = (
        df_filter
        .groupby("komoditas")["harga"]
        .mean()
        .sort_values(ascending=False)
    )

    komoditas_mahal = rata_komoditas.index[0]
    harga_mahal = rata_komoditas.iloc[0]

    komoditas_murah = rata_komoditas.index[-1]
    harga_murah = rata_komoditas.iloc[-1]

    st.markdown(f"""
    <div class="insight-box">

    <div class="insight-title">
    🏆 Komoditas dengan harga rata-rata tertinggi
    </div>

    <div class="insight-text">
    <b>{komoditas_mahal}</b> memiliki harga rata-rata
    sebesar <b>Rp {harga_mahal:,.0f}</b>.
    </div>

    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="insight-box">

    <div class="insight-title">
    💰 Komoditas dengan harga rata-rata terendah
    </div>

    <div class="insight-text">
    <b>{komoditas_murah}</b> memiliki harga rata-rata
    sebesar <b>Rp {harga_murah:,.0f}</b>.
    </div>

    </div>
    """, unsafe_allow_html=True)

# =========================================================
# TAB 2 — PERBANDINGAN
# =========================================================

with tab2:

    st.markdown(
        '<div class="section-title">🏆 Perbandingan Harga Komoditas</div>',
        unsafe_allow_html=True
    )

    rata = (
        df_filter
        .groupby("komoditas")["harga"]
        .mean()
        .reset_index()
        .sort_values(
            "harga",
            ascending=True
        )
    )

    fig_bar = px.bar(
        rata,
        x="harga",
        y="komoditas",
        orientation="h",
        text_auto=".0f",
        labels={
            "harga": "Harga Rata-rata (Rp)",
            "komoditas": "Komoditas"
        }
    )

    fig_bar.update_layout(
        height=max(500, len(rata) * 35),
        plot_bgcolor="white",
        paper_bgcolor="white"
    )

    fig_bar.update_xaxes(
        tickprefix="Rp ",
        tickformat=","
    )

    st.plotly_chart(
        fig_bar,
        use_container_width=True
    )

    # -----------------------------------------------------
    # DISTRIBUSI HARGA
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">📊 Distribusi Harga</div>',
        unsafe_allow_html=True
    )

    fig_box = px.box(
        df_filter,
        x="komoditas",
        y="harga",
        labels={
            "komoditas": "Komoditas",
            "harga": "Harga (Rp)"
        }
    )

    fig_box.update_layout(
        height=500,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_tickangle=-45
    )

    fig_box.update_yaxes(
        tickprefix="Rp ",
        tickformat=","
    )

    st.plotly_chart(
        fig_box,
        use_container_width=True
    )

# =========================================================
# TAB 3 — CUACA
# =========================================================

with tab3:

    st.markdown(
        '<div class="section-title">🌦️ Kondisi Cuaca</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    # -----------------------------------------------------
    # SUHU
    # -----------------------------------------------------

    with col1:

        if "suhu_rata_rata" in df_filter.columns:

            suhu = (
                df_filter
                .groupby("tanggal", as_index=False)
                ["suhu_rata_rata"]
                .mean()
            )

            fig_suhu = px.line(
                suhu,
                x="tanggal",
                y="suhu_rata_rata",
                markers=True,
                labels={
                    "tanggal": "Tanggal",
                    "suhu_rata_rata": "Suhu (°C)"
                }
            )

            fig_suhu.update_layout(
                title="🌡️ Suhu Rata-rata",
                plot_bgcolor="white",
                paper_bgcolor="white"
            )

            st.plotly_chart(
                fig_suhu,
                use_container_width=True
            )

        else:

            st.info(
                "Data suhu rata-rata tidak tersedia."
            )

    # -----------------------------------------------------
    # CURAH HUJAN
    # -----------------------------------------------------

    with col2:

        if "curah_hujan_mm" in df_filter.columns:

            hujan = (
                df_filter
                .groupby("tanggal", as_index=False)
                ["curah_hujan_mm"]
                .mean()
            )

            fig_hujan = px.bar(
                hujan,
                x="tanggal",
                y="curah_hujan_mm",
                labels={
                    "tanggal": "Tanggal",
                    "curah_hujan_mm": "Curah Hujan (mm)"
                }
            )

            fig_hujan.update_layout(
                title="🌧️ Curah Hujan",
                plot_bgcolor="white",
                paper_bgcolor="white"
            )

            st.plotly_chart(
                fig_hujan,
                use_container_width=True
            )

        else:

            st.info(
                "Data curah hujan tidak tersedia."
            )

    # -----------------------------------------------------
    # SUHU MIN / MAX
    # -----------------------------------------------------

    if (
        "suhu_min" in df_filter.columns
        and
        "suhu_max" in df_filter.columns
    ):

        suhu_harian = (
            df_filter
            .groupby("tanggal", as_index=False)
            .agg(
                suhu_min=("suhu_min", "mean"),
                suhu_max=("suhu_max", "mean")
            )
        )

        fig_range = go.Figure()

        fig_range.add_trace(
            go.Scatter(
                x=suhu_harian["tanggal"],
                y=suhu_harian["suhu_min"],
                mode="lines",
                name="Suhu Minimum"
            )
        )

        fig_range.add_trace(
            go.Scatter(
                x=suhu_harian["tanggal"],
                y=suhu_harian["suhu_max"],
                mode="lines",
                name="Suhu Maksimum"
            )
        )

        fig_range.update_layout(
            title="🌡️ Rentang Suhu Harian",
            xaxis_title="Tanggal",
            yaxis_title="Suhu (°C)",
            height=450,
            plot_bgcolor="white",
            paper_bgcolor="white"
        )

        st.plotly_chart(
            fig_range,
            use_container_width=True
        )

# =========================================================
# TAB 4 — DATA
# =========================================================

with tab4:

    st.markdown(
        '<div class="section-title">📋 Data Harga Pangan</div>',
        unsafe_allow_html=True
    )

    # Statistik ringkas
    ringkasan = (
        df_filter
        .groupby("komoditas")
        .agg(
            harga_rata_rata=("harga", "mean"),
            harga_minimum=("harga", "min"),
            harga_maksimum=("harga", "max"),
            jumlah_data=("harga", "count")
        )
        .reset_index()
    )

    ringkasan = ringkasan.rename(
        columns={
            "komoditas": "Komoditas",
            "harga_rata_rata": "Harga Rata-rata",
            "harga_minimum": "Harga Minimum",
            "harga_maksimum": "Harga Maksimum",
            "jumlah_data": "Jumlah Data"
        }
    )

    ringkasan["Harga Rata-rata"] = (
        ringkasan["Harga Rata-rata"]
        .round(0)
        .astype(int)
    )

    ringkasan["Harga Minimum"] = (
        ringkasan["Harga Minimum"]
        .round(0)
        .astype(int)
    )

    ringkasan["Harga Maksimum"] = (
        ringkasan["Harga Maksimum"]
        .round(0)
        .astype(int)
    )

    st.write("### 📌 Ringkasan per Komoditas")

    st.dataframe(
        ringkasan,
        use_container_width=True,
        hide_index=True
    )

    st.write("### 📄 Data Detail")

    st.dataframe(
        df_filter.sort_values(
            "tanggal",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# FOOTER
# =========================================================

st.markdown("""
<div class="footer">

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Dashboard Harga Pangan Kota Kendari</b>

<br>

Sistem monitoring dan analisis harga pangan,
komoditas, serta kondisi cuaca.

<br><br>

Data digunakan untuk mendukung analisis
perubahan harga pangan di Kota Kendari.

</div>
""", unsafe_allow_html=True)