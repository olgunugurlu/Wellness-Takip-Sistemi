"""
notifications.py — Sistem içi ve e-posta bildirim modülü
"""
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from db import get_connection


# ── SİSTEM İÇİ BİLDİRİM ─────────────────────────────────────────────────────
def bildirim_ekle(user_id: int, tip: str, baslik: str, mesaj: str):
    """Veritabanına bildirim kaydeder."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO wellness_bildirimler (user_id, tip, baslik, mesaj)
            VALUES (%s, %s, %s, %s)
        """, (user_id, tip, baslik, mesaj))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Bildirim eklenemedi: {e}")


def bildirimleri_getir(user_id: int, sadece_okunmamis: bool = False) -> list:
    """Kullanıcının bildirimlerini getirir."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        if sadece_okunmamis:
            cursor.execute("""
                SELECT * FROM wellness_bildirimler
                WHERE user_id = %s AND okundu = 0
                ORDER BY tarih DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT * FROM wellness_bildirimler
                WHERE user_id = %s
                ORDER BY tarih DESC LIMIT 20
            """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception:
        return []


def bildirimi_okundu_isaretle(bildirim_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE wellness_bildirimler SET okundu=1 WHERE id=%s", (bildirim_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass


def tum_bildirimleri_oku(user_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE wellness_bildirimler SET okundu=1 WHERE user_id=%s", (user_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass


def okunmamis_sayi(user_id: int) -> int:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM wellness_bildirimler WHERE user_id=%s AND okundu=0",
            (user_id,)
        )
        sayi = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return sayi
    except Exception:
        return 0


# ── E-POSTA ──────────────────────────────────────────────────────────────────
def eposta_gonder(alici_email: str, alici_ad: str, konu: str, icerik_html: str) -> bool:
    """SMTP ile e-posta gönderir. secrets.toml'daki [email] bölümünü kullanır."""
    try:
        cfg = st.secrets.get("email", {})
        if not cfg:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = konu
        msg["From"]    = f"{cfg.get('gonderici_ad','Wellness Sistemi')} <{cfg['gonderici_email']}>"
        msg["To"]      = f"{alici_ad} <{alici_email}>"

        html_part = MIMEText(icerik_html, "html", "utf-8")
        msg.attach(html_part)

        port = int(cfg.get("smtp_port", 587))
        if port == 465:
            with smtplib.SMTP_SSL(cfg["smtp_host"], port) as server:
                server.login(cfg["gonderici_email"], cfg["smtp_sifre"])
                server.sendmail(cfg["gonderici_email"], alici_email, msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], port) as server:
                server.ehlo()
                server.starttls()
                server.login(cfg["gonderici_email"], cfg["smtp_sifre"])
                server.sendmail(cfg["gonderici_email"], alici_email, msg.as_string())
        return True
    except Exception as e:
        print(f"E-posta gönderilemedi: {e}")
        return False


def eposta_sablonu(ad: str, baslik: str, icerik: str) -> str:
    """Temel HTML e-posta şablonu."""
    return f"""
    <html><body style="font-family:Calibri,Arial,sans-serif;background:#f5f2ed;margin:0;padding:20px">
    <div style="max-width:600px;margin:auto;background:#fff;border-radius:16px;overflow:hidden;
                box-shadow:0 4px 20px rgba(0,0,0,.08)">
        <div style="background:linear-gradient(135deg,#1a1714,#2d2620);padding:32px;text-align:center">
            <h1 style="color:#d4a847;font-size:24px;margin:0">🌿 Wellness Analiz</h1>
        </div>
        <div style="padding:32px">
            <p style="color:#1a1714;font-size:16px">Merhaba <strong>{ad}</strong>,</p>
            <h2 style="color:#1a1714;font-size:20px;border-bottom:2px solid #d4a847;
                       padding-bottom:8px">{baslik}</h2>
            <div style="color:#444;font-size:15px;line-height:1.7">{icerik}</div>
        </div>
        <div style="background:#f9f6f1;padding:20px;text-align:center;font-size:12px;color:#888">
            Bu e-posta otomatik olarak gönderilmiştir. Sorularınız için yöneticinize başvurun.<br>
            <em>Bu platform tıbbi tavsiye sunmamaktadır.</em>
        </div>
    </div>
    </body></html>
    """


# ── HAZIR BİLDİRİM FONKSİYONLARI ────────────────────────────────────────────
def kayit_bekleme_bildirimi(user_id: int, ad: str, email: str):
    """Kayıt sonrası kullanıcıya bekleme bildirimi gönderir."""
    bildirim_ekle(
        user_id, "bilgi",
        "Kaydınız alındı",
        "Hesabınız admin onayı bekliyor. Onaylandığında size bildirim gelecek."
    )
    eposta_gonder(email, ad,
        "Wellness Sistemi — Kaydınız Alındı",
        eposta_sablonu(ad, "Kaydınız Alındı ✓",
            """Wellness Analiz Sistemine kaydınız başarıyla alındı.<br><br>
            Hesabınız şu an <strong>admin onayı</strong> beklemektedir.
            Onaylandığında e-posta ile bilgilendirileceksiniz.<br><br>
            Teşekkür ederiz."""
        )
    )


def kayit_onay_bildirimi(user_id: int, ad: str, email: str):
    """Admin onayladığında kullanıcıya bildirim gönderir."""
    bildirim_ekle(
        user_id, "kayit_onaylandi",
        "Hesabınız Onaylandı! 🎉",
        "Hesabınız aktif edildi. Artık giriş yaparak wellness formunuzu doldurabilirsiniz."
    )
    eposta_gonder(email, ad,
        "Wellness Sistemi — Hesabınız Onaylandı",
        eposta_sablonu(ad, "Hesabınız Onaylandı 🎉",
            """Harika haber! Hesabınız admin tarafından onaylandı.<br><br>
            Artık sisteme giriş yaparak <strong>kişisel wellness formunuzu</strong> 
            doldurabilir ve analizinizi talep edebilirsiniz.<br><br>
            <a href="#" style="background:#d4a847;color:#000;padding:12px 24px;
               border-radius:8px;text-decoration:none;font-weight:bold">
               Sisteme Giriş Yap →
            </a>"""
        )
    )


def kayit_red_bildirimi(user_id: int, ad: str, email: str, neden: str = ""):
    """Admin reddettiğinde kullanıcıya bildirim gönderir."""
    bildirim_ekle(
        user_id, "kayit_reddedildi",
        "Hesap Başvurunuz Hakkında",
        f"Hesap başvurunuz şu an onaylanamadı. {neden}"
    )
    eposta_gonder(email, ad,
        "Wellness Sistemi — Hesap Başvurunuz",
        eposta_sablonu(ad, "Hesap Başvurunuz Hakkında",
            f"""Hesap başvurunuzu incelediğimiz için teşekkür ederiz.<br><br>
            Maalesef şu an başvurunuzu onaylayamıyoruz.
            {"<br><br><strong>Neden:</strong> " + neden if neden else ""}<br><br>
            Daha fazla bilgi için lütfen bizimle iletişime geçin."""
        )
    )


def analiz_hazir_bildirimi(user_id: int, ad: str, email: str, analiz_id: int):
    """Admin analizi onayladığında kullanıcıya bildirim gönderir."""
    bildirim_ekle(
        user_id, "analiz_hazir",
        "Wellness Analiziniz Hazır! 🌿",
        "Kişisel wellness ve takviye analiziniz hazırlandı. Sisteme giriş yaparak görüntüleyebilirsiniz."
    )
    eposta_gonder(email, ad,
        "Wellness Sistemi — Analiziniz Hazır",
        eposta_sablonu(ad, "Wellness Analiziniz Hazır 🌿",
            """Kişisel wellness ve takviye analiziniz uzman incelemesinden geçerek hazırlandı.<br><br>
            Analiz sonuçlarınızı görüntülemek için sisteme giriş yapın.<br><br>
            <a href="#" style="background:#d4a847;color:#000;padding:12px 24px;
               border-radius:8px;text-decoration:none;font-weight:bold">
               Analizimi Görüntüle →
            </a><br><br>
            <em style="font-size:13px;color:#888">
            Bu analiz genel bilgilendirme amaçlıdır ve tıbbi tavsiye niteliği taşımaz.
            </em>"""
        )
    )
