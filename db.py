import mysql.connector
from mysql.connector import Error
import streamlit as st


def get_connection():
    cfg = st.secrets["mysql"]
    return mysql.connector.connect(
        host=cfg["host"],
        database=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
        port=int(cfg.get("port", 3306)),
        connection_timeout=15,
        autocommit=False
    )


def init_db():
    """Tüm tabloları oluşturur (yoksa)."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── KULLANICILAR ─────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wellness_users (
            id                  INT AUTO_INCREMENT PRIMARY KEY,
            ad_soyad            VARCHAR(100) NOT NULL,
            email               VARCHAR(150) NOT NULL UNIQUE,
            password_hash       VARCHAR(255) NOT NULL,
            rol                 ENUM('user','admin') DEFAULT 'user',
            durum               ENUM('beklemede','aktif','pasif','engelli') DEFAULT 'beklemede',
            sartlar_kabul       TINYINT(1) DEFAULT 0,
            sartlar_kabul_tarih DATETIME NULL,
            admin_notu          TEXT NULL,
            kayit_tarihi        DATETIME DEFAULT CURRENT_TIMESTAMP,
            onay_tarihi         DATETIME NULL
        )
    """)

    # ── FORMLAR ──────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wellness_forms (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            user_id      INT NOT NULL,
            form_json    LONGTEXT NOT NULL,
            durum        ENUM('beklemede','isleniyor','onaylandi','reddedildi') DEFAULT 'beklemede',
            tarih        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES wellness_users(id) ON DELETE CASCADE
        )
    """)

    # ── ANALİZLER ────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wellness_analyses (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            form_id          INT NOT NULL,
            user_id          INT NOT NULL,
            analiz_metni     LONGTEXT NOT NULL,
            admin_duzenleme  LONGTEXT NULL,
            durum            ENUM('taslak','admin_inceleme','onaylandi','kullaniciya_gonderildi') DEFAULT 'taslak',
            admin_id         INT NULL,
            olusturma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
            onay_tarihi      DATETIME NULL,
            gonderim_tarihi  DATETIME NULL,
            FOREIGN KEY (form_id) REFERENCES wellness_forms(id)  ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES wellness_users(id)  ON DELETE CASCADE
        )
    """)

    # ── BİLDİRİMLER ──────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wellness_bildirimler (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            user_id      INT NOT NULL,
            tip          ENUM('analiz_hazir','kayit_onaylandi','kayit_reddedildi','bilgi') DEFAULT 'bilgi',
            baslik       VARCHAR(200) NOT NULL,
            mesaj        TEXT NOT NULL,
            okundu       TINYINT(1) DEFAULT 0,
            tarih        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES wellness_users(id) ON DELETE CASCADE
        )
    """)

    # ── OTURUMLAR ──────────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wellness_sessions (
            id           VARCHAR(64) PRIMARY KEY,
            user_id      INT NOT NULL,
            son_aktivite DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            olusturma    DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES wellness_users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
