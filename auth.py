import hashlib
import secrets
import streamlit as st
from db import get_connection
from datetime import datetime


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── OTURUM YÖNETİMİ ──────────────────────────────────────────────────────────
def oturum_olustur(user_id: int) -> str:
    """Veritabanında oturum kaydı oluşturur, token döner."""
    token = secrets.token_hex(32)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Kullanıcının eski oturumlarını ve 7 günden eski tüm oturumları temizle
        cursor.execute("""
            DELETE FROM wellness_sessions
            WHERE user_id = %s OR son_aktivite < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (user_id,))
        cursor.execute(
            "INSERT INTO wellness_sessions (id, user_id) VALUES (%s, %s)",
            (token, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Oturum oluşturulamadı: {e}")
    return token


def oturum_dogrula(token: str):
    """Token geçerliyse kullanıcı bilgilerini döner, yoksa None."""
    if not token:
        return None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.* FROM wellness_sessions s
            JOIN wellness_users u ON u.id = s.user_id
            WHERE s.id = %s
              AND s.son_aktivite > DATE_SUB(NOW(), INTERVAL 7 DAY)
              AND u.durum = 'aktif'
        """, (token,))
        user = cursor.fetchone()
        if user:
            cursor.execute(
                "UPDATE wellness_sessions SET son_aktivite = NOW() WHERE id = %s",
                (token,)
            )
            conn.commit()
        cursor.close()
        conn.close()
        return user
    except Exception:
        return None


def oturum_sil(token: str):
    """Oturumu veritabanından siler."""
    if not token:
        return
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wellness_sessions WHERE id = %s", (token,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass


# ── KAYIT / GİRİŞ ─────────────────────────────────────────────────────────────
def register_user(ad_soyad: str, email: str, password: str, sartlar_kabul: bool = False) -> tuple:
    if not sartlar_kabul:
        return False, "Kullanım şartlarını kabul etmeniz gerekmektedir.", None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM wellness_users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False, "Bu e-posta adresi zaten kayıtlı.", None

        cursor.execute("""
            INSERT INTO wellness_users
                (ad_soyad, email, password_hash, sartlar_kabul, sartlar_kabul_tarih, durum)
            VALUES (%s, %s, %s, 1, %s, 'beklemede')
        """, (ad_soyad, email, hash_password(password), datetime.now()))
        user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Kayıt başarılı!", user_id
    except Exception as e:
        return False, f"Hata: {e}", None


def login_user(email: str, password: str) -> tuple:
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM wellness_users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return False, "E-posta bulunamadı.", None
        if user["password_hash"] != hash_password(password):
            return False, "Parola hatalı.", None
        if user["durum"] == "beklemede":
            return False, "⏳ Hesabınız admin onayı bekliyor. Onaylandığında bildirim alacaksınız.", None
        if user["durum"] in ("pasif", "engelli"):
            return False, "❌ Hesabınız aktif değil. Lütfen yönetici ile iletişime geçin.", None

        return True, "Giriş başarılı!", user
    except Exception as e:
        return False, f"Hata: {e}", None


# ── SESSION STATE ─────────────────────────────────────────────────────────────
def set_session(user: dict):
    """Giriş sonrası oturum açar, token oluşturur ve URL'e yazar."""
    token = oturum_olustur(user["id"])
    st.session_state.token      = token
    st.session_state.logged_in  = True
    st.session_state.user_id    = user["id"]
    st.session_state.user_name  = user["ad_soyad"]
    st.session_state.user_email = user["email"]
    st.session_state.user_rol   = user["rol"]
    # Token'ı URL query param olarak sakla (sayfa yenilenince de kalır)
    st.query_params["sid"] = token


def restore_session() -> bool:
    """Sayfa yenilenince URL'deki token ile oturumu geri yükler."""
    # Önce URL'den, sonra session_state'ten token al
    token = st.query_params.get("sid", "") or st.session_state.get("token", "")
    if not token:
        return False

    user = oturum_dogrula(token)
    if not user:
        # Geçersiz token temizle
        try:
            del st.query_params["sid"]
        except Exception:
            pass
        return False

    st.session_state.token      = token
    st.session_state.logged_in  = True
    st.session_state.user_id    = user["id"]
    st.session_state.user_name  = user["ad_soyad"]
    st.session_state.user_email = user["email"]
    st.session_state.user_rol   = user["rol"]
    return True


def logout():
    """Oturumu kapatır, token'ı siler."""
    token = st.session_state.get("token", "")
    oturum_sil(token)
    try:
        del st.query_params["sid"]
    except Exception:
        pass
    for key in ["token", "logged_in", "user_id", "user_name", "user_email",
                "user_rol", "step", "form_data", "analysis_result", "page",
                "admin_menu", "admin_analiz_id", "goruntulenen_analiz_id"]:
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def is_admin() -> bool:
    return st.session_state.get("user_rol") == "admin"
