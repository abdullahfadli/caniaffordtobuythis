from __future__ import print_function
from streamlit_option_menu import option_menu
import os.path
import base64
import re
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta

# ===================== Konfigurasi Halaman =====================
st.set_page_config(page_title="Finance App", layout="wide")

# ===================== Navbar =====================
selected = option_menu(
    menu_title=None,
    options=["Home", "Finance Tracker", "Can I Afford To Buy This?", "About Me"],
    icons=["house", "coin", "wallet2", "person"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#070631"},
        "icon": {"color": "white", "font-size": "20px"},
        "nav-link": {
            "font-size": "17px",
            "text-align": "center",
            "margin": "0px",
            "--hover-color": "#302B79",
            "white-space": "nowrap",  # cegah teks turun ke baris kedua
        },
        "nav-link-selected": {
            "background-color": "#19145B",
            "color": "white",
            "white-space": "nowrap",  # tetap 1 baris
        },
    }
)


# ===================== Halaman Home =====================
if selected == "Home":
    st.title("🏠 Selamat Datang di Finance App")
    st.write(
        "Finance App adalah sistem yang membantu Anda melacak dan menganalisis kondisi keuangan pribadi secara mudah dan cepat."
    )

    st.subheader("Fitur yang tersedia:")
    
    st.markdown("#### 1. Finance Tracker")
    st.write(
        "- Melacak semua transaksi keuangan yang masuk maupun keluar dari akun Gmail Anda."
        " Data transaksi akan diambil secara otomatis, difilter berdasarkan pengirim dan rentang tanggal."
    )
    st.write(
        "- Menyajikan ringkasan keuangan berupa total pendapatan, total pengeluaran, dan saldo saat ini."
    )
    st.write(
        "- Menampilkan grafik visualisasi transaksi berupa diagram batang, pie chart kategori transaksi, "
        "dan tren pengeluaran harian untuk memudahkan analisis."
    )

    st.markdown("#### 2. Can I Afford To Buy This?")
    st.write(
        "- Membantu Anda mengevaluasi apakah Anda mampu membeli suatu barang berdasarkan kondisi finansial dan psikologis."
    )
    st.write(
        "- Mempertimbangkan faktor seperti uang yang dimiliki saat ini, harga barang, tingkat kebahagiaan, dan kepentingan barang."
    )
    st.write(
        "- Memberikan rekomendasi dengan skor akhir dan peringatan jika pembelian dianggap kurang aman."
    )
    st.write("- Menyediakan simulasi tabungan bulanan untuk memperkirakan kapan target tabungan aman dapat tercapai.")

    st.subheader("Cara Menggunakan Aplikasi:")
    st.write("1. Pilih fitur yang ingin digunakan melalui menu navigasi di atas.")
    st.write("2. Untuk 'Finance Tracker', pilih rentang tanggal dan pengirim email untuk menampilkan transaksi.")
    st.write("3. Untuk 'Can I Afford To Buy This?', masukkan kondisi finansial, psikologis, dan tabungan per bulan (opsional), lalu klik 'Lihat Rekomendasi'.")


# ===================== Halaman Finance Tracker =====================
elif selected == "Finance Tracker":
    # ===================== Konfigurasi =====================
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    ALLOWED_SENDERS = [
        "noreply.livin@bankmandiri.co.id",
        "bca@bca.co.id"
    ]

    # ===================== Helper =====================
    def get_service():
        creds = None
        try:
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
        except Exception as e:
            if os.path.exists('token.json'):
                os.remove('token.json')
            st.warning("⚠️ Token Gmail kadaluarsa atau dicabut. Silakan login ulang.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def extract_email_text(msg):
        parts = msg.get("payload", {}).get("parts", [])
        text = ""
        if not parts:
            data = msg['payload']['body'].get('data', '')
            text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part['body'].get('data', '')
                    text += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part.get("mimeType") == "text/html":
                    data = part['body'].get('data', '')
                    html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(html, "html.parser")
                    text += soup.get_text()
        return text

    def normalize_amount(amount_str):
        if "," in amount_str and "." in amount_str and amount_str.find(",") < amount_str.find("."):
            amount_str = amount_str.replace(",", "")
        else:
            amount_str = amount_str.replace(".", "").replace(",", ".")
        return float(amount_str)

    def format_rupiah(amount):
        return f"Rp {amount:,.0f}".replace(",", ".")

    # ===================== Ambil transaksi =====================
    @st.cache_data(ttl=300)
    def get_transactions_from_gmail(selected_senders, start_date, end_date, max_results=200):
        service = get_service()
        
        query_senders = " OR ".join([f"from:{sender}" for sender in selected_senders])
        query_dates = f"after:{start_date.strftime('%Y/%m/%d')} before:{(end_date+timedelta(days=1)).strftime('%Y/%m/%d')}"
        query = f"({query_senders}) {query_dates}"

        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()

        messages = results.get('messages', [])
        transactions = []

        for msg_item in messages:
            txt = service.users().messages().get(userId='me', id=msg_item['id']).execute()
            headers = txt.get("payload", {}).get("headers", [])
            sender = next((h["value"] for h in headers if h["name"].lower()=="from"), "")
            date_header = next((h["value"] for h in headers if h["name"].lower()=="date"), "")
            subject = next((h["value"] for h in headers if h["name"].lower()=="subject"), "")

            text = extract_email_text(txt).replace("\xa0", " ").replace("\t", " ")

            amount_match = re.search(r'(?:Rp|IDR)\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', text, re.IGNORECASE)
            if not amount_match:
                continue
            try:
                amount = normalize_amount(amount_match.group(1))
            except:
                continue

            search_text = (subject + " " + text).lower()
            if re.search(r'\b(masuk|diterima|transfer masuk|deposit|top up)\b', search_text):
                tipe = "Pendapatan"
            elif re.search(r'\b(keluar|pembayaran|berhasil dibayar|transfer keluar|purchase|withdrawal|transaction|pembelian|tagihan|transfer berhasil|penarikan|qris|top-up)\b', search_text):
                tipe = "Pengeluaran"
            else:
                tipe = "Tidak diketahui"

            transactions.append({
                "tanggal": parsedate_to_datetime(date_header),
                "tipe": tipe,
                "amount": amount,
                "jumlah transaksi": format_rupiah(amount),
                "pengirim": sender
            })

        df = pd.DataFrame(transactions)
        if not df.empty:
            df = df.sort_values(by="tanggal", ascending=False)
        return df

    # ===================== Streamlit UI =====================
    st.title("💰 Finance Tracker")
    st.markdown("Pantau transaksi keuangan Anda dengan cepat dan rapi.")

    # --- Filter UI ---
    with st.container():
        st.subheader("🔎 Filter Data")
        col_date, col_sender, col_button = st.columns([3,4,1])

        today = datetime.today().date()
        min_allowed = today - timedelta(days=365)

        with col_date:
            date_range = st.date_input(
                "Rentang Tanggal",
                value=(today - timedelta(days=30), today),
                min_value=min_allowed,
                max_value=today
            )

        with col_sender:
            selected_senders = st.multiselect(
                "Pilih Pengirim",
                options=ALLOWED_SENDERS,
                default=[]
            )

        with col_button:
            apply_filter = st.button("Terapkan Filter")

    # --- Ambil data hanya setelah filter ditekan ---
    df_filtered = pd.DataFrame()
    if apply_filter:
        if not selected_senders:
            st.warning("⚠️ Silakan pilih minimal satu pengirim.")
        else:
            start_date, end_date = date_range
            with st.spinner("Mengambil data transaksi dari Gmail..."):
                df_filtered = get_transactions_from_gmail(selected_senders, start_date, end_date)

            if df_filtered.empty:
                st.info("Tidak ada transaksi pada rentang tanggal & pengirim yang dipilih.")
            else:
                df_filtered['tanggal'] = df_filtered['tanggal'].dt.strftime('%d/%m/%Y')

                def color_tipe(val):
                    if val == "Pendapatan":
                        return "color: green"
                    elif val == "Pengeluaran":
                        return "color: red"
                    return ""

                styled_df = df_filtered[['tanggal','tipe','jumlah transaksi','pengirim']].style \
                    .applymap(color_tipe, subset=['tipe']) \
                    .set_table_styles([{'selector': 'th','props': [('text-align', 'center'),('font-weight', 'bold')]}])

                st.subheader("📊 Data Transaksi")
                st.dataframe(styled_df, use_container_width=True)

                # ===================== Ringkasan Keuangan =====================
                st.subheader("Ringkasan Keuangan")
                total_pendapatan = df_filtered[df_filtered['tipe']=="Pendapatan"]['amount'].sum()
                total_pengeluaran = df_filtered[df_filtered['tipe']=="Pengeluaran"]['amount'].sum()
                saldo = total_pendapatan - total_pengeluaran

                # Tampilkan dalam 3 kolom sejajar
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Pendapatan", format_rupiah(total_pendapatan))
                col2.metric("Total Pengeluaran", format_rupiah(total_pengeluaran))
                col3.metric("Saldo", format_rupiah(saldo))

                # ===================== Grafik =====================
                st.subheader("📈 Grafik Keuangan")

                # Buat 3 kolom untuk menampung masing-masing grafik
                col1, col2, col3 = st.columns(3)

                # ================= Grafik Seragam =================
                # Atur kolom supaya ketiga grafik sejajar
                col1, col2, col3 = st.columns([1, 1, 1])

                # Grafik 1: Bar Pendapatan & Pengeluaran
                with col1:
                    fig, ax = plt.subplots(figsize=(4,3))
                    fig.patch.set_facecolor("#1f1f1f")  # gelap tapi netral
                    ax.set_facecolor("#1f1f1f")
                    ax.bar(['Pendapatan', 'Pengeluaran'], [total_pendapatan, total_pengeluaran], color=["#285A2A", '#621A15'])
                    ax.set_ylabel("Jumlah (Rp)", color='white')
                    ax.set_title("Pendapatan vs Pengeluaran", color='white')
                    ax.tick_params(colors='white', labelsize=10)
                    ax.grid(True, linestyle='--', alpha=0.3, color='white')
                    for spine in ax.spines.values():
                        spine.set_visible(False)
                    st.pyplot(fig, clear_figure=False)

                # Grafik 2: Pie tipe transaksi
                with col2:
                    tipe_counts = df_filtered['tipe'].value_counts()
                    fig2, ax2 = plt.subplots(figsize=(4,3))
                    fig2.patch.set_facecolor("#1f1f1f")
                    ax2.set_facecolor("#1f1f1f")
                    wedges, texts, autotexts = ax2.pie(
                        tipe_counts, labels=tipe_counts.index, autopct='%1.1f%%', startangle=90,
                        colors=["#621A15",'#285A2A','#2196F3'],
                        textprops={'color':'white', 'fontsize':10}
                    )
                    ax2.axis('equal')
                    ax2.set_title("Distribusi Tipe Transaksi", color='white')
                    st.pyplot(fig2, clear_figure=True)

                # Grafik 3: Line chart pengeluaran harian
                with col3:
                    pengeluaran_df = df_filtered[df_filtered['tipe'] == "Pengeluaran"].copy()
                    if not pengeluaran_df.empty:
                        pengeluaran_df['tanggal'] = pd.to_datetime(pengeluaran_df['tanggal'], dayfirst=True, errors='coerce')
                        pengeluaran_df = pengeluaran_df.dropna(subset=['tanggal'])
                        pengeluaran_daily = pengeluaran_df.groupby(pengeluaran_df['tanggal'].dt.date)['amount'].sum().reset_index()

                        fig3, ax3 = plt.subplots(figsize=(4,3))
                        fig3.patch.set_facecolor("#1f1f1f")
                        ax3.set_facecolor("#1f1f1f")
                        ax3.plot(pengeluaran_daily['tanggal'], pengeluaran_daily['amount'], marker='o', linestyle='-', color='#621A15', linewidth=2)
                        ax3.set_xlabel("Tanggal", color='white')
                        ax3.set_ylabel("Jumlah (Rp)", color='white')
                        ax3.set_title("Pengeluaran Harian", color='white')
                        ax3.tick_params(axis='x', colors='white', rotation=45)
                        ax3.tick_params(axis='y', colors='white')
                        ax3.grid(True, linestyle='--', alpha=0.3, color='white')
                        for spine in ax3.spines.values():
                            spine.set_visible(False)
                        st.pyplot(fig3, clear_figure=True)
                    else:
                        st.info("Tidak ada data pengeluaran untuk periode ini.")


# ===================== Halaman Can I Afford To Buy This =====================
elif selected == "Can I Afford To Buy This?":
    st.title("❓ Can I Afford To Buy This?")

    with st.container():
        st.subheader("Input Kondisi Finansial")
        uang_str = st.text_input("Uang yang Dimiliki Sekarang (Rp)", value="")
        harga_str = st.text_input("Harga Barang yang Ingin Dibeli (Rp)", value="")

        st.subheader("Input Kondisi Psikologis")
        bahagia = st.slider("Tingkat Kebahagiaan Jika Membeli\n0 = Biasa saja, 100 = Sangat bahagia", 0, 100, 0)
        penting = st.slider("Tingkat Kepentingan Barang\n0 = Biasa saja, 100 = Sangat penting", 0, 100, 0)

        st.subheader("Simulasi Tabungan")
        tabungan_perbulan_str = st.text_input("Jumlah menabung per bulan dalam rupiah (Optional)", value="")

        # ---------------- Helper Functions ----------------
        def format_rupiah(value):
            return f"{value:,}".replace(",", ".")

        def parse_rupiah(text):
            try:
                return int(text.replace(".", "").strip())
            except:
                return 0

        def saw_rekomendasi(uang_sekarang, harga_barang, bahagia, penting):
            if uang_sekarang > 0:
                affordability = harga_barang / uang_sekarang
            else:
                affordability = 1e9

            n_afford = min(1 / affordability, 1)
            n_bahagia = bahagia / 100
            n_penting = penting / 100

            bobot_afford = 0.6
            bobot_bahagia = 0.15
            bobot_penting = 0.25

            skor = n_afford * bobot_afford + n_bahagia * bobot_bahagia + n_penting * bobot_penting
            tabungan_minimal = harga_barang * 10

            return skor, n_afford, n_bahagia, n_penting, tabungan_minimal

        # ================= Hasil Rekomendasi =================
        if st.button("🔍 Lihat Rekomendasi"):
            uang_sekarang = parse_rupiah(uang_str)
            harga_barang = parse_rupiah(harga_str)
            tabungan_perbulan = parse_rupiah(tabungan_perbulan_str)

            skor, n_afford, n_bahagia, n_penting, tabungan_minimal = saw_rekomendasi(uang_sekarang, harga_barang, bahagia, penting)

            st.subheader("📌 Hasil Rekomendasi")
            st.write(f"- Skor Akhir: {skor:.2f} (0–1)")

            if skor >= 0.75:
                st.success("✅ Rekomendasi: Anda dapat membeli barang ini.")
            else:
                st.error("❌ Rekomendasi: Sebaiknya tunda dulu pembelian.")
                st.info(f"💡 Agar aman secara finansial, sebaiknya punya uang minimal: Rp {format_rupiah(tabungan_minimal)}")

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
                    bulan_diperlukan = -(-sisa // tabungan_perbulan)
                    st.info(f"Anda perlu menabung sekitar {bulan_diperlukan} bulan lagi untuk mencapai tabungan aman.")

                    saldo = uang_sekarang
                    for bulan in range(1, bulan_diperlukan + 1):
                        saldo += tabungan_perbulan
                        progress = min(saldo / tabungan_minimal, 1.0)
                        st.progress(progress, text=f"Bulan {bulan}: Rp {format_rupiah(saldo)}")
            else:
                st.warning("⚠️ Masukkan jumlah tabungan per bulan untuk simulasi.")

# ===================== Halaman About Me =====================
elif selected == "About Me":
    st.title("👤 About Me")

    # Buat dua kolom: kiri (teks), kanan (gambar)
    col1, col2 = st.columns([4, 1])

    with col1:
        st.subheader("Tentang Saya")
        st.markdown("""
- **Nama:** Abdullah Fadli Nurazza  
- **Pendidikan:** Mahasiswa Sistem Informasi, Universitas Islam Negeri Jakarta
- **Lokasi:** Jakarta, Indonesia  
        """)

        st.subheader("Minat & Keahlian")
        st.markdown("""
- Data Science Enthusiast  
- Analisis data & visualisasi data 
- Business Development
        """)

        st.subheader("Kontak & Media Sosial")
        st.markdown("""
- LinkedIn: [linkedin.com/abdullah-fadli-nurazza](https://www.linkedin.com/in/abdullah-fadli-nurazza)  
- Email: **abdullahfadli444@gmail.com**
        """)

    with col2:
        profil_image_url = "https://media.licdn.com/dms/image/v2/D5635AQGFYH5mfzhqJg/profile-framedphoto-shrink_200_200/B56ZkTPKAbHAAk-/0/1756964364633?e=1758200400&v=beta&t=vlm-6kwr1MKt3azCKSQ6HDHGUwvDE8bXJsecUL2Somw"
        st.image(profil_image_url, width=220, caption="Abdullah Fadli Nurazza")