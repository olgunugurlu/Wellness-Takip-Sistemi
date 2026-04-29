import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import datetime

st.set_page_config(page_title="MySQL Bağlantı Testi", page_icon="🗄️", layout="centered")

st.title("🗄️ MySQL Bağlantı Testi")
st.caption("Veritabanı bağlantısını ve temel işlemleri test eder.")

# ── BAĞLANTI BİLGİLERİ ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔌 Bağlantı Bilgileri")
    host     = st.text_input("Host / IP",     placeholder="94.73.151.154")
    database = st.text_input("Veritabanı",    placeholder="u1927296_olgundb")
    user     = st.text_input("Kullanıcı adı", placeholder="u1927296_olgundb")
    password = st.text_input("Parola",        type="password", placeholder="")
    port     = st.number_input("Port", value=3306, min_value=1, max_value=65535)
    st.divider()
    st.caption("Bilgiler yalnızca bu oturumda kullanılır, kaydedilmez.")

# ── BAĞLANTI FONKSİYONU ──────────────────────────────────────────────────────
def get_connection():
    return mysql.connector.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=int(port),
        connection_timeout=10
    )

# ── 1. BAĞLANTI TESTİ ────────────────────────────────────────────────────────
st.subheader("1️⃣ Bağlantı Testi")

if st.button("🔌 Bağlantıyı Test Et", type="primary", use_container_width=True):
    if not all([host, database, user, password]):
        st.warning("Lütfen sol menüden tüm bağlantı bilgilerini girin.")
    else:
        try:
            conn = get_connection()
            if conn.is_connected():
                info = conn.get_server_info()
                st.success(f"✅ Bağlantı başarılı! MySQL versiyon: **{info}**")
                cursor = conn.cursor()
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                st.info(f"📂 Aktif veritabanı: **{db_name}**")
                cursor.close()
                conn.close()
        except Error as e:
            st.error(f"❌ Bağlantı hatası: {e}")
            if "10061" in str(e) or "timed out" in str(e).lower():
                st.warning("💡 cPanel → Remote MySQL'den bu IP'ye erişim izni verin.")
            elif "Access denied" in str(e):
                st.warning("💡 Kullanıcı adı veya parola hatalı.")

st.divider()

# ── 2. TABLO OLUŞTUR ─────────────────────────────────────────────────────────
st.subheader("2️⃣ Test Tablosu Oluştur")
st.caption("Bağlantı çalışıyorsa test için basit bir tablo oluşturur.")

if st.button("📋 Tabloyu Oluştur", use_container_width=True):
    if not all([host, database, user, password]):
        st.warning("Önce bağlantı bilgilerini girin.")
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wellness_test_kayitlar (
                    id       INT AUTO_INCREMENT PRIMARY KEY,
                    isim     VARCHAR(100) NOT NULL,
                    mesaj    TEXT,
                    tarih    DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            st.success("✅ `wellness_test_kayitlar` tablosu hazır (yoksa oluşturuldu).")
            cursor.close()
            conn.close()
        except Error as e:
            st.error(f"❌ Hata: {e}")

st.divider()

# ── 3. KAYIT EKLE ────────────────────────────────────────────────────────────
st.subheader("3️⃣ Kayıt Ekle")

with st.form("kayit_form"):
    isim  = st.text_input("İsim", placeholder="Ada Öztürk")
    mesaj = st.text_area("Mesaj", placeholder="Test mesajı...", height=80)
    submitted = st.form_submit_button("💾 Kaydet", use_container_width=True)

if submitted:
    if not all([host, database, user, password]):
        st.warning("Önce bağlantı bilgilerini girin.")
    elif not isim:
        st.warning("İsim alanı boş olamaz.")
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO wellness_test_kayitlar (isim, mesaj) VALUES (%s, %s)",
                (isim, mesaj)
            )
            conn.commit()
            st.success(f"✅ Kayıt eklendi! (ID: {cursor.lastrowid})")
            cursor.close()
            conn.close()
        except Error as e:
            st.error(f"❌ Hata: {e}")

st.divider()

# ── 4. KAYITLARI LİSTELE ─────────────────────────────────────────────────────
st.subheader("4️⃣ Kayıtları Listele")

if st.button("🔍 Kayıtları Getir", use_container_width=True):
    if not all([host, database, user, password]):
        st.warning("Önce bağlantı bilgilerini girin.")
    else:
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM wellness_test_kayitlar ORDER BY tarih DESC LIMIT 20")
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            if rows:
                st.success(f"✅ {len(rows)} kayıt bulundu.")
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("Henüz kayıt yok. Önce bir kayıt ekleyin.")
        except Error as e:
            st.error(f"❌ Hata: {e}")
            if "doesn't exist" in str(e):
                st.warning("💡 Önce '📋 Tabloyu Oluştur' butonuna basın.")

st.divider()

# ── 5. TABLOYU TEMİZLE ───────────────────────────────────────────────────────
st.subheader("5️⃣ Temizlik")

col1, col2 = st.columns(2)
with col1:
    if st.button("🗑️ Tüm Kayıtları Sil", use_container_width=True):
        if not all([host, database, user, password]):
            st.warning("Önce bağlantı bilgilerini girin.")
        else:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM wellness_test_kayitlar")
                conn.commit()
                affected = cursor.rowcount
                st.success(f"✅ {affected} kayıt silindi.")
                cursor.close()
                conn.close()
            except Error as e:
                st.error(f"❌ Hata: {e}")

with col2:
    if st.button("💣 Tabloyu Tamamen Sil", use_container_width=True):
        if not all([host, database, user, password]):
            st.warning("Önce bağlantı bilgilerini girin.")
        else:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS wellness_test_kayitlar")
                conn.commit()
                st.success("✅ Tablo silindi.")
                cursor.close()
                conn.close()
            except Error as e:
                st.error(f"❌ Hata: {e}")
