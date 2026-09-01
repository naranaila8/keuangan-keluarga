import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import json
from datetime import datetime

# --- PENGATURAN HALAMAN ---
st.set_page_config(page_title="Keuangan Keluarga", layout="wide")
st.title("💰 Aplikasi Keuangan Keluarga")

# --- KONEKSI KE GOOGLE SHEETS ---
url_sheet = st.secrets["url_google_sheet"]
credentials = json.loads(st.secrets["gcp_service_account"])
conn = st.connection("gsheets", type=GSheetsConnection, service_account=credentials)

# --- FUNGSI LOAD DATA ---
def load_data():
    try:
        # Membaca data dari Google Sheets
        df = conn.read(spreadsheet=url_sheet, worksheet="Sheet1")
        df = df.dropna(how="all") # Bersihkan baris kosong
        return df
    except Exception as e:
        st.error(f"Gagal membaca data: {e}")
        return pd.DataFrame(columns=["Tanggal", "Jenis", "Kategori", "Item", "Jumlah", "Keterangan"])

df = load_data()

# --- SIDEBAR: INPUT DATA ---
st.sidebar.header("📝 Input Transaksi Baru")

with st.sidebar.form("form_transaksi"):
    tanggal = st.date_input("Tanggal", datetime.today())
    jenis = st.selectbox("Jenis Transaksi", ["Pemasukan", "Pengeluaran", "Tabungan", "Kredit", "Masa Depan (Terjadwal)"])
    
    if jenis == "Pengeluaran":
        kategori = st.selectbox("Kategori Pengeluaran", ["50% Kebutuhan (Wajib)", "30% Keinginan (Hiburan/Tersier)"])
    else:
        kategori = jenis

    # Fitur Item Fleksibel: Mengambil riwayat item
    if not df.empty and "Item" in df.columns:
        item_history = df[df["Jenis"] == jenis]["Item"].dropna().unique().tolist()
    else:
        item_history = []
        
    item_history.insert(0, "-- Buat Item Baru --")
    pilih_item = st.selectbox("Pilih Item (Riwayat)", item_history)
    item_baru = st.text_input("Atau ketik Item Baru")
    item_final = item_baru if pilih_item == "-- Buat Item Baru --" or item_baru != "" else pilih_item
    
    jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=10000)
    keterangan = st.text_area("Keterangan Opsional")
    submit = st.form_submit_button("Simpan Transaksi")
    
    if submit:
        if item_final == "":
            st.sidebar.error("Item tidak boleh kosong!")
        else:
            # Siapkan data baru
            data_baru = pd.DataFrame({
                "Tanggal": [tanggal.strftime("%Y-%m-%d")], 
                "Jenis": [jenis], 
                "Kategori": [kategori], 
                "Item": [item_final], 
                "Jumlah": [jumlah], 
                "Keterangan": [keterangan]
            })
            
            # Gabungkan dengan data lama
            df_updated = pd.concat([df, data_baru], ignore_index=True)
            
            # Update ke Google Sheets
            conn.update(worksheet="Sheet1", data=df_updated)
            
            st.sidebar.success(f"Berhasil disimpan ke Google Sheets!")
            st.rerun()

# --- KALKULASI DASHBOARD ---
# Pastikan kolom jumlah berupa angka
df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0)

total_pemasukan = df[df["Jenis"] == "Pemasukan"]["Jumlah"].sum()
total_kebutuhan = df[df["Kategori"] == "50% Kebutuhan (Wajib)"]["Jumlah"].sum()
total_keinginan = df[df["Kategori"] == "30% Keinginan (Hiburan/Tersier)"]["Jumlah"].sum()
total_tabungan = df[df["Jenis"] == "Tabungan"]["Jumlah"].sum()
total_kredit = df[df["Jenis"] == "Kredit"]["Jumlah"].sum()

rasio_tabungan = (total_tabungan / total_pemasukan * 100) if total_pemasukan > 0 else 0

# --- DASHBOARD & SPEDOMETER ---
st.subheader("📊 Dashboard Kesehatan Keuangan")
col1, col2, col3 = st.columns(3)
col1.metric("Total Pemasukan", f"Rp {total_pemasukan:,.0f}")
col2.metric("Pengeluaran & Kredit", f"Rp {(total_kebutuhan + total_keinginan + total_kredit):,.0f}")
col3.metric("Total Tabungan", f"Rp {total_tabungan:,.0f}")

fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = rasio_tabungan,
    title = {'text': "Kesehatan Finansial (Rasio Tabungan %)"},
    gauge = {
        'axis': {'range': [None, 100]},
        'bar': {'color': "darkblue"},
        'steps': [
            {'range': [0, 10], 'color': "red"},
            {'range': [10, 20], 'color': "yellow"},
            {'range': [20, 100], 'color': "green"}
        ],
        'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': 20}
    }
))
st.plotly_chart(fig, use_container_width=True)

# --- REKOMENDASI PAKAR ---
st.subheader("💡 Rekomendasi Pakar (Aturan 50/30/20)")
if total_pemasukan > 0:
    st.info(f"""
    Target anggaran ideal bulan ini:
    *   **Kebutuhan Pokok & Kredit (Maks 50%):** Rp {(total_pemasukan * 0.5):,.0f} (Terpakai: Rp {(total_kebutuhan + total_kredit):,.0f})
    *   **Keinginan (Maks 30%):** Rp {(total_pemasukan * 0.3):,.0f} (Terpakai: Rp {total_keinginan:,.0f})
    *   **Tabungan (Min 20%):** Rp {(total_pemasukan * 0.2):,.0f} (Terkumpul: Rp {total_tabungan:,.0f})
    """)
else:
    st.warning("Belum ada pemasukan untuk menghitung rekomendasi.")

# --- TABEL DATA ---
st.subheader("📂 Riwayat Transaksi")
st.dataframe(df, use_container_width=True)
