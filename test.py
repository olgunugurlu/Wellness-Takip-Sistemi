import streamlit as st
import smtplib

# Basit Test Butonu
if st.button("SMTP Bağlantısını Test Et"):
    try:
        cfg = st.secrets["email"]
        server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])
        server.starttls()
        server.login(cfg["gonderici_email"], cfg["smtp_sifre"])
        st.success("✅ Bağlantı ve Giriş Başarılı!")
        server.quit()
    except Exception as e:
        st.error(f"❌ Bağlantı Hatası: {e}")