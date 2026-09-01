import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- PENGATURAN HALAMAN ---
st.set_page_config(page_title="Keuangan Keluarga", layout="wide")
st.title("💰 Aplikasi Keuangan Keluarga")

# --- KONEKSI KE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNGSI LOAD DATA ---
def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(how="all") 
        # Tambahkan kolom baru jika membaca data lama agar tidak error
        for col in ["Akun", "Akun Tujuan"]:
            if col not in df.columns:
                df[col] = "-"
        return df
    except Exception as e:
        st.error(f"Gagal membaca data: {e}")
        return pd.DataFrame(columns=["Tanggal", "Jenis", "Kategori", "Item", "Jumlah", "Keterangan", "Akun", "Akun Tujuan"])

df = load_data()

# Siapkan daftar Akun (Cash, Bank, E-Wallet) dari riwayat yang ada
akun_history = list(set(df["Akun"].dropna().unique().tolist() + df["Akun Tujuan"].dropna().unique().tolist()))
default_akun = ["Cash", "BCA", "Mandiri", "GoPay", "OVO", "Dana"]
all_akun = sorted(list(set(default_akun + akun_history)))
all_akun = [a for a in all_akun if a not in ["", "-", "nan", None]]
all_akun.insert(0, "-- Buat Akun Baru --")

# --- SIDEBAR: INPUT DATA ---
st.sidebar.header("📝 Input Transaksi Baru")

with st.sidebar.form("form_transaksi"):
    tanggal = st.date_input("Tanggal", datetime.today())
    jenis = st.selectbox("Jenis Transaksi", ["Pemasukan", "Pengeluaran", "Tabungan", "Kredit", "Masa Depan (Terjadwal)", "Saldo Awal", "Transfer"])
    
    # Pengaturan Kategori
    if jenis == "Pengeluaran":
        kategori = st.selectbox("Kategori Pengeluaran", ["50% Kebutuhan (Wajib)", "30% Keinginan (Hiburan/Tersier)"])
    else:
        kategori = jenis

    # Pengaturan Akun & Transfer
    if jenis == "Transfer":
        st.markdown("---")
        pilih_akun_asal = st.selectbox("Akun Asal (Sumber Dana)", all_akun)
        akun_asal_baru = st.text_input("Atau ketik Akun Asal Baru")
        akun_final = akun_asal_baru if pilih_akun_asal == "-- Buat Akun Baru --" or akun_asal_baru != "" else pilih_akun_asal
        
        pilih_akun_tujuan = st.selectbox("Akun Tujuan (Penerima Dana)", all_akun, key="tujuan")
        akun_tujuan_baru = st.text_input("Atau ketik Akun Tujuan Baru")
        akun_tujuan_final = akun_tujuan_baru if pilih_akun_tujuan == "-- Buat Akun Baru --" or akun_tujuan_baru != "" else pilih_akun_tujuan
        item_final = "Transfer Saldo"
    else:
        pilih_akun = st.selectbox("Pilih Akun / Dompet", all_akun)
        akun_baru = st.text_input("Atau ketik Akun Baru")
        akun_final = akun_baru if pilih_akun == "-- Buat Akun Baru --" or akun_baru != "" else pilih_akun
        akun_tujuan_final = "-"
        
        # Fitur Item Fleksibel
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
        if item_final == "" or akun_final == "":
            st.sidebar.error("Data Item atau Akun tidak boleh kosong!")
        else:
            data_baru = pd.DataFrame({
                "Tanggal": [tanggal.strftime("%Y-%m-%d")], "Jenis": [jenis], "Kategori": [kategori], 
                "Item": [item_final], "Jumlah": [jumlah], "Keterangan": [keterangan],
                "Akun": [akun_final], "Akun Tujuan": [akun_tujuan_final]
            })
            
            df_updated = pd.concat([df, data_baru], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df_updated)
            st.sidebar.success(f"Berhasil disimpan!")
            st.rerun()

# --- KALKULASI DATA ---
df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0)

total_pemasukan = df[df["Jenis"].isin(["Pemasukan"])]["Jumlah"].sum()
total_kebutuhan = df[df["Kategori"] == "50% Kebutuhan (Wajib)"]["Jumlah"].sum()
total_keinginan = df[df["Kategori"] == "30% Keinginan (Hiburan/Tersier)"]["Jumlah"].sum()
total_tabungan = df[df["Jenis"] == "Tabungan"]["Jumlah"].sum()
total_kredit = df[df["Jenis"] == "Kredit"]["Jumlah"].sum()

rasio_tabungan = (total_tabungan / total_pemasukan * 100) if total_pemasukan > 0 else 0

# KALKULASI SALDO PER AKUN (BUG TELAH DIPERBAIKI DI SINI)
saldo_akun = {}
for _, row in df.iterrows():
    j = row["Jenis"]
    jml = row["Jumlah"]
    a = str(row["Akun"])
    at = str(row["Akun Tujuan"])
    
    # Berikan nilai awal 0 untuk SEMUA jenis karakter agar sistem tidak bingung/error
    if a not in saldo_akun: saldo_akun[a] = 0
    if at not in saldo_akun: saldo_akun[at] = 0
    
    if j in ["Pemasukan", "Saldo Awal"]:
        saldo_akun[a] += jml
    elif j in ["Pengeluaran", "Tabungan", "Kredit", "Masa Depan (Terjadwal)"]:
        saldo_akun[a] -= jml
    elif j == "Transfer":
        saldo_akun[a] -= jml
        saldo_akun[at] += jml

# --- TAMPILAN DASHBOARD ---
st.subheader("💳 Saldo Dompet & Rekening Aktif")
# Hilangkan akun kosong/strip saat ditampilkan di layar
saldo_aktif = {k: v for k, v in saldo_akun.items() if k not in ["", "-", "nan"]}
if saldo_aktif:
    cols = st.columns(len(saldo_aktif) if len(saldo_aktif) < 5 else 5)
    idx = 0
    for ak, sld in saldo_aktif.items():
        cols[idx % 5].metric(ak, f"Rp {sld:,.0f}")
        idx += 1
else:
    st.info("Belum ada data saldo. Silakan input 'Saldo Awal' atau 'Pemasukan' terlebih dahulu.")

st.markdown("---")
st.subheader("📊 Kesehatan Finansial (Aturan 50/30/20)")
col1, col2, col3 = st.columns(3)
col1.metric("Total Pemasukan", f"Rp {total_pemasukan:,.0f}")
col2.metric("Pengeluaran & Kredit", f"Rp {(total_kebutuhan + total_keinginan + total_kredit):,.0f}")
col3.metric("Total Tabungan", f"Rp {total_tabungan:,.0f}")

fig = go.Figure(go.Indicator(
    mode = "gauge+number", value = rasio_tabungan, title = {'text': "Rasio Tabungan %"},
    gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "darkblue"},
             'steps': [{'range': [0, 10], 'color': "red"}, {'range': [10, 20], 'color': "yellow"}, {'range': [20, 100], 'color': "green"}],
             'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': 20}}
))
st.plotly_chart(fig, use_container_width=True)

# --- FILTER & DOWNLOAD DATA ---
st.markdown("---")
st.subheader("📥 Filter & Download Riwayat Transaksi")

df['Tanggal_DT'] = pd.to_datetime(df['Tanggal'], errors='coerce')
df['Bulan_Tahun'] = df['Tanggal_DT'].dt.strftime('%B %Y')

list_bulan = ["Semua"] + df['Bulan_Tahun'].dropna().unique().tolist()
list_jenis = ["Semua"] + sorted(df['Jenis'].dropna().unique().tolist())
list_akun = ["Semua"] + all_akun[1:]

col_f1, col_f2, col_f3 = st.columns(3)
filter_bulan = col_f1.selectbox("Pilih Bulan", list_bulan)
filter_jenis = col_f2.selectbox("Pilih Jenis", list_jenis)
filter_akun = col_f3.selectbox("Pilih Akun", list_akun)

df_filtered = df.copy()
if filter_bulan != "Semua":
    df_filtered = df_filtered[df_filtered['Bulan_Tahun'] == filter_bulan]
if filter_jenis != "Semua":
    df_filtered = df_filtered[df_filtered['Jenis'] == filter_jenis]
if filter_akun != "Semua":
    df_filtered = df_filtered[(df_filtered['Akun'] == filter_akun) | (df_filtered['Akun Tujuan'] == filter_akun)]

df_display = df_filtered.drop(columns=['Tanggal_DT', 'Bulan_Tahun'], errors='ignore')
st.dataframe(df_display, use_container_width=True)

csv_data = df_display.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Data yang Difilter (CSV)",
    data=csv_data,
    file_name=f'Data_Keuangan_{filter_bulan}.csv',
    mime='text/csv'
)
