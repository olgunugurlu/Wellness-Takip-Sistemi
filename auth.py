import hashlib
import streamlit as st
from db import get_connection
from datetime import datetime


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(ad_soyad: str, email: str, password: str, sartlar_kabul: bool = False) -> tuple:
    if not sartlar_kabul:
        return False, "Kullanım şartlarını kabul etmeniz gerekmektedir."
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM wellness_users WHERE email = %s", (email,))
        if cursor.fetchone():
            return False, "Bu e-posta adresi zaten kayıtlı."

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


def set_session(user: dict):
    st.session_state.logged_in  = True
    st.session_state.user_id    = user["id"]
    st.session_state.user_name  = user["ad_soyad"]
    st.session_state.user_email = user["email"]
    st.session_state.user_rol   = user["rol"]


def logout():
    for key in ["logged_in","user_id","user_name","user_email","user_rol",
                "step","form_data","analysis_result","page"]:
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def is_admin() -> bool:
    return st.session_state.get("user_rol") == "admin"
