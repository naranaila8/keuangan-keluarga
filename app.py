import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import numpy as np

# --- PENGATURAN HALAMAN ---
st.set_page_config(page_title="Keuangan Keluarga Advance", layout="wide")
st.title("💰 Aplikasi Keuangan Keluarga (Advance)")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def format_teks(teks):
    if pd.isna(teks) or teks == "" or str(teks).strip().lower() == "none": return "-"
    teks = str(teks).strip().title()
    pengganti = {"Bca": "BCA", "Bri": "BRI", "Bni": "BNI", "Bsi": "BSI", "Ovo": "OVO", "Gopay": "GoPay"}
    return pengganti.get(teks, teks)

def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(how="all") 
        for col in ["Akun", "Akun Tujuan", "Penginput"]:
            if col not in df.columns: df[col] = "-"
        
        for col in ["Akun", "Akun Tujuan", "Item", "Kategori", "Penginput"]:
            if col in df.columns: df[col] = df[col].apply(format_teks)
                
        df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors='coerce').fillna(0)
        df['Bulan_Tahun'] = pd.to_datetime(df['Tanggal'], errors='coerce').dt.strftime('%Y-%m')
        return df
    except Exception as e:
        st.error(f"Gagal membaca data: {e}")
        return pd.DataFrame()

df = load_data()
bulan_ini = datetime.today().strftime('%Y-%m')

# --- SIDEBAR: PROFIL KELUARGA (ADVANCE) ---
st.sidebar.header("⚙️ Profil Keluarga & Target")
with st.sidebar.expander("Atur Umur & Inflasi (Untuk Rumus Pakar)"):
    umur_suami = st.number_input("Umur Suami", 20, 80, 30)
    umur_istri = st.number_input("Umur Istri", 20, 80, 28)
    jumlah_anak = st.number_input("Jumlah Anak", 0, 10, 1)
    umur_anak_terlama = st.number_input("Umur Anak Pertama", 0, 30, 3) if jumlah_anak > 0 else 0
    inflasi = st.slider("Asumsi Inflasi Tahunan (%)", 1, 15, 6)
    biaya_kuliah_saat_ini = st.number_input("Est. Biaya Kuliah Total (Saat ini)", value=150000000, step=10000000)

# --- SIDEBAR: INPUT TRANSAKSI ---
st.sidebar.markdown("---")
st.sidebar.header("📝 Input Transaksi Baru")

# Ambil daftar akun
akun_history = []
if not df.empty:
    akun_history = list(set(df["Akun"].dropna().unique().tolist() + df["Akun Tujuan"].dropna().unique().tolist()))
default_akun = ["Cash", "BCA", "Mandiri", "GoPay", "Tabungan Emas", "Reksadana", "Deposito"]
all_akun = sorted(list(set([format_teks(a) for a in default_akun + akun_history])))
all_akun = [a for a in all_akun if a not in ["", "-", "nan", None]]
all_akun.insert(0, "-- Buat Akun Baru --")

with st.sidebar.form("form_transaksi"):
    penginput = st.selectbox("Siapa yang Input?", ["Suami", "Istri", "Bersama"])
    tanggal = st.date_input("Tanggal", datetime.today())
    jenis = st.selectbox("Jenis Transaksi", ["Pemasukan", "Pengeluaran", "Tabungan", "Kredit", "Masa Depan", "Saldo Awal", "Transfer"])
    
    kategori = st.selectbox("Kategori Pengeluaran", ["50% Kebutuhan (Wajib)", "30% Keinginan (Hiburan/Tersier)"]) if jenis == "Pengeluaran" else jenis

    if jenis == "Transfer":
        pilih_akun_asal = st.selectbox("Akun Asal", all_akun)
        akun_asal_baru = st.text_input("Atau ketik Akun Asal Baru")
        akun_final = akun_asal_baru if pilih_akun_asal == "-- Buat Akun Baru --" or akun_asal_baru != "" else pilih_akun_asal
        pilih_akun_tujuan = st.selectbox("Akun Tujuan", all_akun, key="tujuan")
        akun_tujuan_baru = st.text_input("Atau ketik Akun Tujuan Baru")
        akun_tujuan_final = akun_tujuan_baru if pilih_akun_tujuan == "-- Buat Akun Baru --" or akun_tujuan_baru != "" else pilih_akun_tujuan
        item_final = "Transfer Saldo"
    else:
        pilih_akun = st.selectbox("Pilih Akun / Dompet", all_akun)
        akun_baru = st.text_input("Atau ketik Akun Baru")
        akun_final = akun_baru if pilih_akun == "-- Buat Akun Baru --" or akun_baru != "" else pilih_akun
        akun_tujuan_final = "-"
        
        item_history = df[df["Jenis"] == jenis]["Item"].dropna().unique().tolist() if not df.empty and "Item" in df.columns else []
        item_history.insert(0, "-- Buat Item Baru --")
        pilih_item = st.selectbox("Pilih Item", item_history)
        item_baru = st.text_input("Atau ketik Item Baru")
        item_final = item_baru if pilih_item == "-- Buat Item Baru --" or item_baru != "" else pilih_item
    
    jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=10000)
    keterangan = st.text_area("Keterangan Opsional")
    submit = st.form_submit_button("Simpan Transaksi")
    
    if submit:
        if item_final == "" or akun_final == "":
            st.sidebar.error("Item & Akun wajib diisi!")
        else:
            data_baru = pd.DataFrame({
                "Tanggal": [tanggal.strftime("%Y-%m-%d")], "Jenis": [jenis], "Kategori": [kategori], 
                "Item": [format_teks(item_final)], "Jumlah": [jumlah], "Keterangan": [keterangan],
                "Akun": [format_teks(akun_final)], "Akun Tujuan": [format_teks(akun_tujuan_final)], "Penginput": [penginput]
            })
            df_updated = pd.concat([df, data_baru], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df_updated)
            st.sidebar.success(f"Berhasil disimpan oleh {penginput}!")
            st.rerun()

# --- KALKULASI UTAMA ---
if df.empty:
    st.warning("Data masih kosong. Silakan input transaksi pertama Anda.")
    st.stop()

# Filter Bulan Ini
df_bulan_ini = df[df['Bulan_Tahun'] == bulan_ini]
pemasukan_bulan_ini = df_bulan_ini[df_bulan_ini["Jenis"] == "Pemasukan"]["Jumlah"].sum()
min_tabungan_bln_ini = pemasukan_bulan_ini * 0.2
max_pengeluaran_bln_ini = pemasukan_bulan_ini * 0.8
terpakai_bln_ini = df_bulan_ini[df_bulan_ini["Jenis"].isin(["Pengeluaran", "Kredit"])]["Jumlah"].sum()
nabung_bln_ini = df_bulan_ini[df_bulan_ini["Jenis"] == "Tabungan"]["Jumlah"].sum()

# Kalkulasi Total
total_pemasukan = df[df["Jenis"] == "Pemasukan"]["Jumlah"].sum()
total_kebutuhan = df[df["Kategori"] == "50% Kebutuhan (Wajib)"]["Jumlah"].sum()
total_tabungan = df[df["Jenis"] == "Tabungan"]["Jumlah"].sum()

# Kalkulasi Saldo Per Akun
saldo_akun = {}
for _, row in df.iterrows():
    j, jml, a, at = row["Jenis"], row["Jumlah"], row["Akun"], row["Akun Tujuan"]
    if a not in saldo_akun: saldo_akun[a] = 0
    if at not in saldo_akun: saldo_akun[at] = 0
    
    if j in ["Pemasukan", "Saldo Awal"]: saldo_akun[a] += jml
    elif j in ["Pengeluaran", "Tabungan", "Kredit", "Masa Depan"]: saldo_akun[a] -= jml
    elif j == "Transfer":
        saldo_akun[a] -= jml
        saldo_akun[at] += jml

# Memisahkan Dana Aktif vs Tabungan
kata_kunci_tabungan = ['emas', 'reksadana', 'deposito', 'saham', 'investasi', 'saving', 'berjangka']
akun_aktif = {}
akun_tabungan = {}

for ak, sld in saldo_akun.items():
    if ak in ["", "-", "nan"] or sld == 0: continue
    # Jika nama akun mengandung kata kunci tabungan, masuk ke aset
    if any(k in ak.lower() for k in kata_kunci_tabungan):
        akun_tabungan[ak] = sld
    else:
        akun_aktif[ak] = sld

# --- DASHBOARD DOMPET & ASET ---
col_akt, col_ast = st.columns(2)
with col_akt:
    st.subheader("💳 Dana Aktif (Dompet & Bank)")
    if akun_aktif:
        for ak, sld in akun_aktif.items():
            st.metric(ak, f"Rp {sld:,.0f}")
    else: st.caption("Belum ada dana aktif.")

with col_ast:
    st.subheader("💎 Aset Tabungan & Investasi")
    if akun_tabungan:
        for ak, sld in akun_tabungan.items():
            st.metric(ak, f"Rp {sld:,.0f}")
    else: st.caption("Belum ada aset tabungan.")

st.markdown("---")

# --- SPEDOMETER & TARGET BULAN INI ---
st.subheader("📊 Kesehatan Finansial & Target Bulan Ini")
col_s1, col_s2, col_s3 = st.columns([1.5, 1, 1])

# Menghitung Batas Rawan (Asumsi 6x Rata-rata Pengeluaran Wajib Bulanan)
bulan_aktif = len(df['Bulan_Tahun'].unique()) if len(df['Bulan_Tahun'].unique()) > 0 else 1
rata_wajib_bulanan = total_kebutuhan / bulan_aktif
batas_rawan = rata_wajib_bulanan * 6 if rata_wajib_bulanan > 0 else (pemasukan_bulan_ini * 0.5 * 6)
selisih_rawan = total_tabungan - batas_rawan

with col_s1:
    rasio = (total_tabungan / total_pemasukan * 100) if total_pemasukan > 0 else 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = rasio, title = {'text': "Rasio Total Tabungan %"},
        gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "darkblue"},
                 'steps': [{'range': [0, 10], 'color': "red"}, {'range': [10, 20], 'color': "yellow"}, {'range': [20, 100], 'color': "green"}],
                 'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': 20}}
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    
    # Caption Status Keuangan
    if selisih_rawan >= 0:
        st.success(f"🌟 **Keuangan Sehat!** Total tabungan Anda Surplus **+ Rp {selisih_rawan:,.0f}** di atas Batas Rawan Dana Darurat.")
    else:
        st.error(f"⚠️ **Keuangan Rawan!** Anda kekurangan **- Rp {abs(selisih_rawan):,.0f}** untuk mencapai Batas Aman Dana Darurat.")

with col_s2:
    st.info("📉 **Batas Pengeluaran Bulan Ini**")
    st.metric("Anggaran Maksimal", f"Rp {max_pengeluaran_bln_ini:,.0f}")
    st.metric("Telah Terpakai", f"Rp {terpakai_bln_ini:,.0f}", delta=f"Sisa: Rp {(max_pengeluaran_bln_ini - terpakai_bln_ini):,.0f}", delta_color="normal")

with col_s3:
    st.success("📈 **Target Menabung Bulan Ini**")
    st.metric("Minimal Ditabung", f"Rp {min_tabungan_bln_ini:,.0f}")
    st.metric("Realisasi Nabung", f"Rp {nabung_bln_ini:,.0f}", delta=f"Kurang: Rp {(min_tabungan_bln_ini - nabung_bln_ini):,.0f}" if nabung_bln_ini < min_tabungan_bln_ini else "Target Tercapai!", delta_color="inverse" if nabung_bln_ini < min_tabungan_bln_ini else "normal")

st.markdown("---")

# --- ANALISIS MASA DEPAN (RUMUS PAKAR) ---
st.subheader("🔮 Analisis Masa Depan (Robo-Advisor)")
col_adv1, col_adv2 = st.columns(2)

with col_adv1:
    st.markdown("**🛡️ Analisis Pensiun (Fidelity Rule)**")
    st.caption("*Pakar menyarankan: Umur 30 punya tabungan 1x Gaji Tahunan, Umur 40 (3x Gaji).*")
    # Perkiraan Gaji Tahunan
    gaji_tahunan = (total_pemasukan / bulan_aktif) * 12
    umur_tertinggi = max(umur_suami, umur_istri)
    
    if umur_tertinggi < 30: target_pensiun = gaji_tahunan * 0.5
    elif umur_tertinggi < 40: target_pensiun = gaji_tahunan * 1
    elif umur_tertinggi < 50: target_pensiun = gaji_tahunan * 3
    else: target_pensiun = gaji_tahunan * 6
    
    st.metric("Target Tabungan Sesuai Umur Anda", f"Rp {target_pensiun:,.0f}")
    st.progress(min(total_tabungan / target_pensiun, 1.0) if target_pensiun > 0 else 0)

with col_adv2:
    st.markdown("**🎓 Proyeksi Biaya Pendidikan Anak**")
    if jumlah_anak > 0:
        tahun_menuju_kuliah = 18 - umur_anak_terlama
        if tahun_menuju_kuliah > 0:
            # Rumus Future Value (FV = PV * (1 + r)^n)
            fv_kuliah = biaya_kuliah_saat_ini * ((1 + (inflasi/100)) ** tahun_menuju_kuliah)
            st.caption(f"*Dengan inflasi {inflasi}%/thn, biaya kuliah {tahun_menuju_kuliah} tahun lagi akan menjadi:*")
            st.metric(f"Proyeksi Biaya Kuliah", f"Rp {fv_kuliah:,.0f}")
            nabung_pendidikan_per_bulan = fv_kuliah / (tahun_menuju_kuliah * 12)
            st.info(f"💡 Anda harus menyisihkan **Rp {nabung_pendidikan_per_bulan:,.0f} / bulan** khusus untuk ini.")
        else:
            st.success("Anak Anda sudah/akan segera memasuki usia kuliah.")
    else:
        st.caption("Anda belum memasukkan data anak pada profil keluarga di sidebar.")

# --- FILTER DATA BERDASARKAN ANGGOTA KELUARGA ---
st.markdown("---")
st.subheader("🕵️ Filter & Edit Data Keluarga")

col_f1, col_f2 = st.columns(2)
filter_penginput = col_f1.selectbox("Filter berdasarkan Penginput", ["Semua", "Suami", "Istri", "Bersama"])
filter_bulan = col_f2.selectbox("Filter Bulan", ["Semua"] + df['Bulan_Tahun'].dropna().unique().tolist())

df_filtered = df.copy()
if filter_penginput != "Semua": df_filtered = df_filtered[df_filtered['Penginput'] == filter_penginput]
if filter_bulan != "Semua": df_filtered = df_filtered[df_filtered['Bulan_Tahun'] == filter_bulan]

# Tabel Interaktif yang sudah disaring
edited_df = st.data_editor(df_filtered.drop(columns=['Bulan_Tahun']), num_rows="dynamic", use_container_width=True, key="data_editor")

if st.button("💾 Simpan Perubahan Tabel", type="primary"):
    # Gabungkan data lama dengan data yang diedit
    df_others = df[~df.index.isin(df_filtered.index)]
    df_final = pd.concat([df_others, edited_df]).sort_index()
    conn.update(worksheet="Sheet1", data=df_final)
    st.success("Tabel berhasil diupdate!")
    st.rerun()
