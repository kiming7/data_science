from airflow.decorators import dag, task
from pendulum import datetime, now

import requests
import pandas as pd

from airflow.providers.mysql.hooks.mysql import MySqlHook


# =========================================================
# KONFIGURASI
# =========================================================

BASE_URL = "https://harga-pangan.fly.dev"

PROVINSI = "Sulawesi Tenggara"
KOTA = "Kota Kendari"

JUMLAH_HARI = 90

MYSQL_CONN_ID = "mysql_harga_pangan"

# Koordinat Kota Kendari
LATITUDE = -3.9985
LONGITUDE = 122.5129

# Data cuaca mulai dari tanggal ini
CURAH_HUJAN_START_DATE = "2026-08-10"


# =========================================================
# 1. EXTRACT HARGA PANGAN
# =========================================================

@task
def extract_harga_pangan():

    url = f"{BASE_URL}/harga/historis"

    daftar_komoditas = [
        "Bawang Merah Ukuran Sedang",
        "Bawang Putih Ukuran Sedang",
        "Beras Kualitas Bawah I",
        "Beras Kualitas Bawah II",
        "Beras Kualitas Medium I",
        "Beras Kualitas Medium II",
        "Beras Kualitas Super I",
        "Beras Kualitas Super II",
        "Cabai Merah Besar",
        "Cabai Merah Keriting",
        "Cabai Rawit Hijau",
        "Cabai Rawit Merah",
        "Daging Ayam Ras Segar",
        "Daging Sapi Kualitas 1",
        "Daging Sapi Kualitas 2",
        "Gula Pasir Kualitas Premium",
        "Gula Pasir Lokal",
        "Minyak Goreng Curah",
        "Minyak Goreng Kemasan Bermerk 1",
        "Minyak Goreng Kemasan Bermerk 2",
        "Telur Ayam Ras Segar"
    ]

    semua_data = []

    for komoditas in daftar_komoditas:

        params = {
            "komoditas": komoditas,
            "provinsi": PROVINSI,
            "kota": KOTA,
            "hari": JUMLAH_HARI
        }

        response = requests.get(
            url,
            params=params,
            timeout=60
        )

        print("====================================")
        print("EXTRACT:", komoditas)
        print("Status:", response.status_code)
        print("Kota:", KOTA)

        response.raise_for_status()

        data = response.json()

        semua_data.append(data)

    print("====================================")
    print("EXTRACT HARGA PANGAN SELESAI")
    print("Jumlah komoditas:", len(semua_data))
    print("Wilayah:", KOTA)
    print("====================================")

    return semua_data


# =========================================================
# 2. TRANSFORM HARGA PANGAN
# =========================================================

@task
def transform_harga_pangan(data):

    records = []

    for response_data in data:

        for item in response_data.get("data", []):

            komoditas_info = item.get("komoditas", {})
            wilayah_info = item.get("wilayah", {})
            riwayat = item.get("riwayat", [])

            komoditas = komoditas_info.get("nama")
            satuan = komoditas_info.get("satuan")

            wilayah = wilayah_info.get("nama")
            provinsi = wilayah_info.get("provinsi")

            for harga in riwayat:

                records.append({
                    "tanggal": harga.get("tanggal"),
                    "komoditas": komoditas,
                    "wilayah": wilayah,
                    "provinsi": provinsi,
                    "harga": harga.get("harga"),
                    "satuan": satuan
                })

    df = pd.DataFrame(records)

    if df.empty:
        print("Data harga pangan kosong.")
        return []

    # Konversi tanggal
    df["tanggal"] = pd.to_datetime(
        df["tanggal"],
        errors="coerce"
    ).dt.date

    # Konversi harga menjadi angka
    df["harga"] = pd.to_numeric(
        df["harga"],
        errors="coerce"
    )

    # Hapus data tidak valid
    df = df.dropna(
        subset=[
            "tanggal",
            "komoditas",
            "wilayah",
            "harga"
        ]
    )

    # Hapus data duplikat
    df = df.drop_duplicates(
        subset=[
            "tanggal",
            "komoditas",
            "wilayah",
            "satuan"
        ]
    )

    # Urutkan data
    df = df.sort_values(
        by=[
            "tanggal",
            "komoditas"
        ]
    )

    print("====================================")
    print("TRANSFORM HARGA PANGAN SELESAI")
    print("====================================")
    print("Jumlah data:", len(df))
    print("Jumlah komoditas:", df["komoditas"].nunique())
    print("Wilayah:", df["wilayah"].unique())
    print("Tanggal awal:", df["tanggal"].min())
    print("Tanggal akhir:", df["tanggal"].max())
    print("====================================")

    return df.to_dict(
        orient="records"
    )

# =========================================================
# 3. LOAD HARGA PANGAN
# =========================================================

@task
def load_harga_pangan(records):

    if not records:
        print("Tidak ada data harga pangan.")
        return

    df = pd.DataFrame(records)

    hook = MySqlHook(
        mysql_conn_id=MYSQL_CONN_ID
    )

    hook.run("""
        CREATE TABLE IF NOT EXISTS harga_pangan (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tanggal DATE,
            komoditas VARCHAR(150),
            wilayah VARCHAR(100),
            provinsi VARCHAR(100),
            harga DECIMAL(12,2),
            satuan VARCHAR(20),

            UNIQUE KEY unique_harga (
                tanggal,
                komoditas,
                wilayah,
                satuan
            )
        );
    """)

    rows = []

    for _, row in df.iterrows():

        rows.append((
            row["tanggal"],
            row["komoditas"],
            row["wilayah"],
            row["provinsi"],
            row["harga"],
            row["satuan"]
        ))

    sql = """
        INSERT INTO harga_pangan
        (
            tanggal,
            komoditas,
            wilayah,
            provinsi,
            harga,
            satuan
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE
            harga = VALUES(harga),
            provinsi = VALUES(provinsi);
    """

    conn = hook.get_conn()
    cursor = conn.cursor()

    cursor.executemany(
        sql,
        rows
    )

    conn.commit()

    cursor.close()
    conn.close()

    print("====================================")
    print("LOAD HARGA PANGAN SELESAI")
    print("====================================")
    print("Jumlah data diproses:", len(rows))
    print("Database: airflow_db")
    print("Tabel: harga_pangan")
    print("====================================")


# =========================================================
# 4. EXTRACT CURAH HUJAN
# =========================================================

@task
def extract_curah_hujan():

    url = "https://archive-api.open-meteo.com/v1/archive"

    end_date = (
        now("Asia/Makassar")
        .subtract(days=1)
        .to_date_string()
    )

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": CURAH_HUJAN_START_DATE,
        "end_date": end_date,
        "daily": "precipitation_sum",
        "timezone": "Asia/Makassar"
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    print("====================================")
    print("EXTRACT CURAH HUJAN")
    print("====================================")
    print("URL API:")
    print(response.url)
    print("Status API:")
    print(response.status_code)
    print(
        "Periode:",
        CURAH_HUJAN_START_DATE,
        "sampai",
        end_date
    )

    response.raise_for_status()

    data = response.json()

    print("Data curah hujan berhasil diambil.")

    return data


# =========================================================
# 5. TRANSFORM CURAH HUJAN
# =========================================================

@task
def transform_curah_hujan(data):

    df = pd.DataFrame({
        "tanggal": data["daily"]["time"],
        "curah_hujan_mm": data["daily"]["precipitation_sum"]
    })

    df["tanggal"] = pd.to_datetime(
        df["tanggal"],
        errors="coerce"
    ).dt.date

    df["curah_hujan_mm"] = pd.to_numeric(
        df["curah_hujan_mm"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["tanggal"]
    )

    df = df.drop_duplicates(
        subset=["tanggal"]
    )

    df = df.sort_values(
        by="tanggal"
    )

    print("====================================")
    print("TRANSFORM CURAH HUJAN SELESAI")
    print("====================================")
    print("Jumlah data:", len(df))
    print("Tanggal awal:", df["tanggal"].min())
    print("Tanggal akhir:", df["tanggal"].max())
    print("====================================")

    return df.to_dict(
        orient="records"
    )


# =========================================================
# 6. LOAD CURAH HUJAN
# =========================================================

@task
def load_curah_hujan(records):

    if not records:
        print("Tidak ada data curah hujan.")
        return

    df = pd.DataFrame(records)

    hook = MySqlHook(
        mysql_conn_id=MYSQL_CONN_ID
    )

    hook.run("""
        CREATE TABLE IF NOT EXISTS curah_hujan (
            tanggal DATE PRIMARY KEY,
            curah_hujan_mm DECIMAL(10,2)
        );
    """)

    rows = []

    for _, row in df.iterrows():

        rows.append((
            row["tanggal"],
            row["curah_hujan_mm"]
        ))

    sql = """
        INSERT INTO curah_hujan
        (
            tanggal,
            curah_hujan_mm
        )
        VALUES (
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE
            curah_hujan_mm = VALUES(
                curah_hujan_mm
            );
    """

    conn = hook.get_conn()
    cursor = conn.cursor()

    cursor.executemany(
        sql,
        rows
    )

    conn.commit()

    cursor.close()
    conn.close()

    print("====================================")
    print("LOAD CURAH HUJAN SELESAI")
    print("====================================")
    print("Jumlah data diproses:", len(rows))
    print("Database: airflow_db")
    print("Tabel: curah_hujan")
    print("====================================")


# =========================================================
# 7. EXTRACT SUHU HARIAN
# =========================================================

@task
def extract_suhu_harian():

    url = "https://archive-api.open-meteo.com/v1/archive"

    end_date = (
        now("Asia/Makassar")
        .subtract(days=1)
        .to_date_string()
    )

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": CURAH_HUJAN_START_DATE,
        "end_date": end_date,
        "daily": (
            "temperature_2m_mean,"
            "temperature_2m_min,"
            "temperature_2m_max"
        ),
        "timezone": "Asia/Makassar"
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    print("====================================")
    print("EXTRACT SUHU HARIAN")
    print("====================================")
    print("URL API:")
    print(response.url)
    print("Status API:")
    print(response.status_code)
    print(
        "Periode:",
        CURAH_HUJAN_START_DATE,
        "sampai",
        end_date
    )

    response.raise_for_status()

    data = response.json()

    print("Data suhu harian berhasil diambil.")

    return data


# =========================================================
# 5. EXTRACT KURS USD/IDR
# =========================================================

@task
def extract_kurs():

    url = "https://api.frankfurter.dev/v2/rates"

    end_date = now("Asia/Makassar").subtract(days=1).to_date_string()

    params = {
        "base": "USD",
        "quotes": "IDR",
        "from": CURAH_HUJAN_START_DATE,
        "to": end_date
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    print("====================================")
    print("EXTRACT KURS USD/IDR")
    print("Status:", response.status_code)
    print("Periode:", CURAH_HUJAN_START_DATE, "sampai", end_date)
    print("====================================")

    response.raise_for_status()

    return response.json()


# =========================================================
# 6. TRANSFORM KURS USD/IDR
# =========================================================

@task
def transform_kurs(data):

    df = pd.DataFrame(data)

    if df.empty:
        print("Data kurs kosong.")
        return []

    df = df.rename(
        columns={
            "date": "tanggal",
            "rate": "usd_idr"
        }
    )

    df["tanggal"] = pd.to_datetime(
        df["tanggal"],
        errors="coerce"
    ).dt.date

    df["usd_idr"] = pd.to_numeric(
        df["usd_idr"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "tanggal",
            "usd_idr"
        ]
    )

    df = df.drop_duplicates(
        subset=["tanggal"]
    )

    df = df.sort_values(
        by="tanggal"
    )

    print("====================================")
    print("TRANSFORM KURS USD/IDR SELESAI")
    print("====================================")
    print("Jumlah data:", len(df))
    print("Tanggal awal:", df["tanggal"].min())
    print("Tanggal akhir:", df["tanggal"].max())
    print("====================================")

    return df[
        ["tanggal", "usd_idr"]
    ].to_dict(
        orient="records"
    )


# =========================================================
# 7. LOAD KURS USD/IDR
# =========================================================

@task
def load_kurs(records):

    if not records:
        print("Data kurs kosong.")
        return

    df = pd.DataFrame(records)

    hook = MySqlHook(
        mysql_conn_id=MYSQL_CONN_ID
    )

    hook.run("""
        CREATE TABLE IF NOT EXISTS kurs_harian (
            tanggal DATE PRIMARY KEY,
            usd_idr DECIMAL(12,2)
        );
    """)

    rows = [
        (
            row["tanggal"],
            row["usd_idr"]
        )
        for _, row in df.iterrows()
    ]

    sql = """
        INSERT INTO kurs_harian (
            tanggal,
            usd_idr
        )
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE
            usd_idr = VALUES(usd_idr);
    """

    conn = hook.get_conn()
    cursor = conn.cursor()

    cursor.executemany(
        sql,
        rows
    )

    conn.commit()

    cursor.close()
    conn.close()

    print("====================================")
    print("LOAD KURS USD/IDR SELESAI")
    print("Jumlah data:", len(rows))
    print("====================================")

# =========================================================
# 8. TRANSFORM SUHU HARIAN
# =========================================================

@task
def transform_suhu_harian(data):

    df = pd.DataFrame({
        "tanggal": data["daily"]["time"],
        "suhu_rata_rata": data["daily"]["temperature_2m_mean"],
        "suhu_min": data["daily"]["temperature_2m_min"],
        "suhu_max": data["daily"]["temperature_2m_max"]
    })

    df["tanggal"] = pd.to_datetime(
        df["tanggal"],
        errors="coerce"
    ).dt.date

    df["suhu_rata_rata"] = pd.to_numeric(
        df["suhu_rata_rata"],
        errors="coerce"
    )

    df["suhu_min"] = pd.to_numeric(
        df["suhu_min"],
        errors="coerce"
    )

    df["suhu_max"] = pd.to_numeric(
        df["suhu_max"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["tanggal"]
    )

    df = df.drop_duplicates(
        subset=["tanggal"]
    )

    df = df.sort_values(
        by="tanggal"
    )

    print("====================================")
    print("TRANSFORM SUHU HARIAN SELESAI")
    print("====================================")
    print("Jumlah data:", len(df))
    print("Tanggal awal:", df["tanggal"].min())
    print("Tanggal akhir:", df["tanggal"].max())
    print("====================================")

    return df.to_dict(
        orient="records"
    )


# =========================================================
# 9. LOAD SUHU HARIAN
# =========================================================

@task
def load_suhu_harian(records):

    if not records:
        print("Tidak ada data suhu.")
        return

    df = pd.DataFrame(records)

    hook = MySqlHook(
        mysql_conn_id=MYSQL_CONN_ID
    )

    hook.run("""
        CREATE TABLE IF NOT EXISTS suhu_harian (
            tanggal DATE PRIMARY KEY,
            suhu_rata_rata DECIMAL(5,2),
            suhu_min DECIMAL(5,2),
            suhu_max DECIMAL(5,2)
        );
    """)

    rows = []

    for _, row in df.iterrows():

        rows.append((
            row["tanggal"],
            row["suhu_rata_rata"],
            row["suhu_min"],
            row["suhu_max"]
        ))

    sql = """
        INSERT INTO suhu_harian
        (
            tanggal,
            suhu_rata_rata,
            suhu_min,
            suhu_max
        )
        VALUES (
            %s,
            %s,
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE
            suhu_rata_rata = VALUES(
                suhu_rata_rata
            ),
            suhu_min = VALUES(
                suhu_min
            ),
            suhu_max = VALUES(
                suhu_max
            );
    """

    conn = hook.get_conn()
    cursor = conn.cursor()

    cursor.executemany(
        sql,
        rows
    )

    conn.commit()

    cursor.close()
    conn.close()

    print("====================================")
    print("LOAD SUHU HARIAN SELESAI")
    print("====================================")
    print("Jumlah data diproses:", len(rows))
    print("Database: airflow_db")
    print("Tabel: suhu_harian")
    print("====================================")


# =========================================================
# DAG
# =========================================================

@dag(
    dag_id="harga_pangan_etl",
    schedule="@daily",
    start_date=datetime(
        2026,
        9,
        22,
        tz="Asia/Makassar"
    ),
    catchup=False,
    tags=[
        "data-science",
        "harga-pangan",
        "curah-hujan",
        "suhu",
        "kota-kendari"
    ],
)
def harga_pangan_etl():

    # Harga pangan
    harga = extract_harga_pangan()
    harga_transform = transform_harga_pangan(harga)
    harga_load = load_harga_pangan(harga_transform)

    # Curah hujan
    hujan = extract_curah_hujan()
    hujan_transform = transform_curah_hujan(hujan)
    hujan_load = load_curah_hujan(hujan_transform)

    # Suhu
    suhu = extract_suhu_harian()
    suhu_transform = transform_suhu_harian(suhu)
    suhu_load = load_suhu_harian(suhu_transform)

    # Kurs USD/IDR
    kurs = extract_kurs()
    kurs_transform = transform_kurs(kurs)
    kurs_load = load_kurs(kurs_transform)


# =========================================================
# AKTIFKAN DAG
# =========================================================

harga_pangan_etl()