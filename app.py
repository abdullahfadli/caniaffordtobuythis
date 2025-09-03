import streamlit as st

st.set_page_config(
    page_title="Can I afford to buy this?",  # Nama halaman/tab
    page_icon="💵",                          # Icon halaman/tab
    layout="centered",                        # Layout
    initial_sidebar_state="expanded"          # Sidebar default
)

st.title("💡 Can I afford to buy this?")

def format_rupiah(value):
    return f"{value:,}".replace(",", ".")

def parse_rupiah(text):
    try:
        return int(text.replace(".", "").strip())
    except:
        return 0

def saw_rekomendasi(uang_sekarang, harga_barang, bahagia, penting):
    # Affordability
    if uang_sekarang > 0:
        affordability = harga_barang / uang_sekarang
    else:
        affordability = 1e9

    # Normalisasi
    n_afford = min(1 / affordability, 1)
    n_bahagia = bahagia / 100
    n_penting = penting / 100

    # Bobot
    bobot_afford = 0.6
    bobot_bahagia = 0.15
    bobot_penting = 0.25

    skor = n_afford * bobot_afford + n_bahagia * bobot_bahagia + n_penting * bobot_penting
    tabungan_minimal = harga_barang * 10

    return skor, n_afford, n_bahagia, n_penting, tabungan_minimal

# ---------------- Sidebar Input SPK ----------------
st.sidebar.header("Input kondisi finansial dan psikologis:")
uang_str = st.sidebar.text_input("Uang yang Dimiliki Sekarang (Rp)", value="1.000.000")
harga_str = st.sidebar.text_input("Harga Barang (Rp)", value="2.500.000")

uang_sekarang = parse_rupiah(uang_str)
harga_barang = parse_rupiah(harga_str)

bahagia = st.sidebar.slider("Tingkat Kebahagiaan Jika Membeli\n1 = Biasa saja, 100 = Sangat bahagia", 1, 100, 50)
penting = st.sidebar.slider("Tingkat Kepentingan Barang\n1 = Biasa saja, 100 = Sangat penting", 1, 100, 50)

# ---------------- Sidebar Simulasi Tabungan ----------------
st.sidebar.header("🗓️ Simulasi Tabungan")
tabungan_perbulan = st.sidebar.number_input("Jumlah menabung per bulan (Rp)", min_value=0, value=500_000, step=100_000)

# ---------------- Hasil Rekomendasi ----------------
if st.button("🔍 Lihat Rekomendasi"):
    skor, n_afford, n_bahagia, n_penting, tabungan_minimal = saw_rekomendasi(uang_sekarang, harga_barang, bahagia, penting)

    st.subheader("📌 Hasil Rekomendasi")
    st.write(f"- Skor Akhir: {skor:.2f} (0–1)")

    # Threshold rekomendasi
    if skor >= 0.:
        st.success("✅ Rekomendasi: Anda dapat membeli barang ini.")
    else:
        st.error("❌ Rekomendasi: Sebaiknya tunda dulu pembelian.")
        st.info(f"💡 Agar aman secara finansial, sebaiknya punya uang minimal: Rp {format_rupiah(tabungan_minimal)}")

    # Peringatan non-hard-rule
    warnings = []
    if n_afford < 0.90:
        warnings.append("⚠️ Harga barang lebih dari 10% tabungan Anda.")
    if n_bahagia < 0.60:
        warnings.append("⚠️ Tingkat kebahagiaan Anda relatif rendah.")
    if n_penting < 0.60:
        warnings.append("⚠️ Tingkat kepentingan barang relatif rendah.")
    if (n_bahagia + n_penting)/2 < 0.65:
        warnings.append("⚠️ Skor psikologis gabungan rendah, pertimbangkan ulang keputusan pembelian.")

    if warnings:
        st.write("### ⚠️ Peringatan")
        for w in warnings:
            st.warning(w)

    # ---------------- Hasil Simulasi Tabungan ----------------
    st.subheader("📈 Simulasi Tabungan")
    persen_tercapai = min(uang_sekarang / tabungan_minimal, 1.0)
    st.progress(persen_tercapai, text=f"Tercapai {persen_tercapai*100:.1f}% dari tabungan aman")
    st.write(f"💰 Tabungan sekarang: Rp {format_rupiah(uang_sekarang)}")
    st.write(f"🎯 Target tabungan aman: Rp {format_rupiah(tabungan_minimal)}")

    if tabungan_perbulan > 0:
        sisa = tabungan_minimal - uang_sekarang
        if sisa <= 0:
            st.success("✅ Tabungan Anda sudah mencukupi untuk kondisi aman.")
        else:
            bulan_diperlukan = -(-sisa // tabungan_perbulan)  # ceiling division
            st.info(f"Anda perlu menabung sekitar {bulan_diperlukan} bulan lagi untuk mencapai tabungan aman.")

            saldo = uang_sekarang
            for bulan in range(1, bulan_diperlukan + 1):
                saldo += tabungan_perbulan
                progress = min(saldo / tabungan_minimal, 1.0)
                st.progress(progress, text=f"Bulan {bulan}: Rp {format_rupiah(saldo)}")
    else:
        st.warning("⚠️ Masukkan jumlah tabungan per bulan untuk simulasi.")
