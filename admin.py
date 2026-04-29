"""
admin.py — Profesyonel Admin Paneli
Layout: Sol sabit menü + Sağ üst header + İçerik alanı
"""
import streamlit as st
import json
from datetime import datetime
from db import get_connection
from notifications import (
    kayit_onay_bildirimi, kayit_red_bildirimi, analiz_hazir_bildirimi
)


# ── CSS ──────────────────────────────────────────────────────────────────────
ADMIN_CSS = """
<style>
/* Genel sıfırlama */
[data-testid="stAppViewContainer"] {
    background: #0d1117 !important;
}
[data-testid="stSidebar"] {
    background: #010409 !important;
    border-right: 1px solid #21262d !important;
    min-width: 240px !important;
    max-width: 240px !important;
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }

/* Header */
.admin-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 14px 22px;
    margin-bottom: 24px;
}
.admin-header-left h2 {
    font-size: 20px;
    font-weight: 600;
    color: #e6edf3;
    margin: 0 0 2px;
}
.admin-header-left p {
    font-size: 13px;
    color: #7d8590;
    margin: 0;
}
.admin-header-right {
    display: flex;
    align-items: center;
    gap: 16px;
}
.admin-clock {
    text-align: right;
}
.admin-clock .time {
    font-size: 22px;
    font-weight: 700;
    color: #d4a847;
    line-height: 1;
}
.admin-clock .date {
    font-size: 12px;
    color: #7d8590;
    margin-top: 2px;
}

/* Menü öğeleri */
.menu-section {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #484f58 !important;
    padding: 16px 12px 6px;
}
.menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 12px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: #7d8590 !important;
    margin-bottom: 2px;
    transition: all .15s;
    text-decoration: none;
}
.menu-item:hover {
    background: #161b22;
    color: #e6edf3 !important;
}
.menu-item.active {
    background: #1f2937;
    color: #e6edf3 !important;
    border-left: 3px solid #d4a847;
}
.menu-badge {
    margin-left: auto;
    background: #da3633;
    color: #fff !important;
    font-size: 11px;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 10px;
    min-width: 20px;
    text-align: center;
}
.menu-badge-gold {
    background: #d4a847 !important;
    color: #000 !important;
}

/* Metrik kartlar */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 24px;
}
@media(max-width:900px){ .metric-grid { grid-template-columns: 1fr 1fr; } }
.metric-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}
.metric-card.gold::before  { background: #d4a847; }
.metric-card.green::before { background: #3fb950; }
.metric-card.blue::before  { background: #58a6ff; }
.metric-card.red::before   { background: #f85149; }
.metric-label {
    font-size: 12px;
    color: #7d8590;
    text-transform: uppercase;
    letter-spacing: .5px;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: #e6edf3;
    line-height: 1;
    margin-bottom: 6px;
}
.metric-sub {
    font-size: 12px;
    color: #484f58;
}

/* Tablo */
.admin-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.admin-table th {
    background: #161b22;
    color: #7d8590;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .5px;
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid #21262d;
}
.admin-table td {
    padding: 12px 14px;
    border-bottom: 1px solid #161b22;
    color: #e6edf3;
    vertical-align: middle;
}
.admin-table tr:hover td { background: #161b22; }

/* Durum badge */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.badge-yellow  { background: rgba(212,168,71,.15); color: #d4a847; }
.badge-green   { background: rgba(63,185,80,.15);  color: #3fb950; }
.badge-red     { background: rgba(248,81,73,.15);  color: #f85149; }
.badge-blue    { background: rgba(88,166,255,.15); color: #58a6ff; }
.badge-gray    { background: rgba(125,133,144,.15);color: #7d8590; }

/* Kart */
.admin-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 16px;
}
.admin-card-title {
    font-size: 14px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #21262d;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Kullanıcı satırı */
.user-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 0;
    border-bottom: 1px solid #21262d;
}
.user-info { display: flex; align-items: center; gap: 12px; }
.user-avatar {
    width: 38px; height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, #d4a847, #b8860b);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 700; color: #000;
    flex-shrink: 0;
}
.user-name { font-size: 14px; font-weight: 500; color: #e6edf3; }
.user-email { font-size: 12px; color: #7d8590; margin-top: 2px; }
.user-actions { display: flex; gap: 8px; }

/* Logo alanı */
.admin-logo {
    padding: 20px 16px 16px;
    border-bottom: 1px solid #21262d;
    margin-bottom: 8px;
}
.admin-logo-text {
    font-size: 16px;
    font-weight: 700;
    color: #d4a847 !important;
    letter-spacing: -.3px;
}
.admin-logo-sub {
    font-size: 11px;
    color: #484f58 !important;
    margin-top: 2px;
}

/* Analiz düzenleme */
.analiz-meta {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin-bottom: 16px;
    padding: 14px 16px;
    background: #0d1117;
    border-radius: 8px;
    font-size: 13px;
    color: #7d8590;
}
.analiz-meta strong { color: #e6edf3; }
</style>
"""


def durum_badge(durum: str) -> str:
    mapping = {
        "beklemede":              '<span class="badge badge-yellow">⏳ Beklemede</span>',
        "aktif":                  '<span class="badge badge-green">✅ Aktif</span>',
        "pasif":                  '<span class="badge badge-gray">⏸ Pasif</span>',
        "engelli":                '<span class="badge badge-red">🚫 Engelli</span>',
        "taslak":                 '<span class="badge badge-blue">📝 Taslak</span>',
        "admin_inceleme":         '<span class="badge badge-yellow">👁 İnceleniyor</span>',
        "onaylandi":              '<span class="badge badge-green">✅ Onaylandı</span>',
        "kullaniciya_gonderildi": '<span class="badge badge-green">📨 Gönderildi</span>',
        "reddedildi":             '<span class="badge badge-red">❌ Reddedildi</span>',
        "isleniyor":              '<span class="badge badge-blue">⚙️ İşleniyor</span>',
    }
    return mapping.get(durum, f'<span class="badge badge-gray">{durum}</span>')


def istatistik_getir() -> dict:
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        stats = {}
        sorgular = {
            "bekleyen_uye":    "SELECT COUNT(*) AS s FROM wellness_users WHERE durum='beklemede' AND rol='user'",
            "aktif_uye":       "SELECT COUNT(*) AS s FROM wellness_users WHERE durum='aktif'",
            "toplam_uye":      "SELECT COUNT(*) AS s FROM wellness_users WHERE rol='user'",
            "bekleyen_analiz": "SELECT COUNT(*) AS s FROM wellness_analyses WHERE durum IN ('taslak','admin_inceleme')",
            "gonderilen":      "SELECT COUNT(*) AS s FROM wellness_analyses WHERE durum='kullaniciya_gonderildi'",
            "bugun_kayit":     "SELECT COUNT(*) AS s FROM wellness_users WHERE DATE(kayit_tarihi)=CURDATE()",
        }
        for k, q in sorgular.items():
            cursor.execute(q)
            stats[k] = cursor.fetchone()["s"]
        cursor.close(); conn.close()
        return stats
    except Exception:
        return {}


def kullanici_getir_by_id(user_id: int) -> dict | None:
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM wellness_users WHERE id=%s", (user_id,))
        u = cursor.fetchone()
        cursor.close(); conn.close()
        return u
    except Exception:
        return None


# ── MENÜ TANIMLARI ───────────────────────────────────────────────────────────
MENU_ITEMS = [
    {"id": "dashboard",       "icon": "📊", "label": "Dashboard"},
    {"id": "bekleyen_uyeler", "icon": "⏳", "label": "Bekleyen Üyeler",  "badge_key": "bekleyen_uye"},
    {"id": "uyeler",          "icon": "👥", "label": "Tüm Üyeler"},
    {"id": "analiz_kuyrugu",  "icon": "🔬", "label": "Analiz Kuyruğu",  "badge_key": "bekleyen_analiz"},
    {"id": "tum_analizler",   "icon": "📋", "label": "Tüm Analizler"},
]


# ── ANA FONKSİYON ─────────────────────────────────────────────────────────────
def show_admin_panel():
    st.markdown(ADMIN_CSS, unsafe_allow_html=True)

    # Session state
    if "admin_menu" not in st.session_state:
        st.session_state.admin_menu = "dashboard"
    if "admin_analiz_id" not in st.session_state:
        st.session_state.admin_analiz_id = None

    stats = istatistik_getir()

    # ── SOL MENÜ (sidebar) ────────────────────────────────────────────────────
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="admin-logo">
            <div class="admin-logo-text">🌿 Wellness</div>
            <div class="admin-logo-sub">Admin Paneli</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="menu-section">YÖNETİM</div>', unsafe_allow_html=True)

        for item in MENU_ITEMS:
            badge_val = stats.get(item.get("badge_key",""), 0)
            badge_html = ""
            if badge_val > 0:
                badge_html = f'<span class="menu-badge">{badge_val}</span>'
            is_active = st.session_state.admin_menu == item["id"]
            active_cls = "active" if is_active else ""

            if st.button(
                f"{item['icon']}  {item['label']}" + (f"  ({badge_val})" if badge_val > 0 else ""),
                key=f"menu_{item['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.admin_menu = item["id"]
                st.session_state.admin_analiz_id = None
                st.rerun()

        st.divider()
        st.markdown('<div class="menu-section">HESAP</div>', unsafe_allow_html=True)

        if st.button("📋  Kullanıcı Moduna Geç", use_container_width=True):
            st.session_state.page = "app"
            st.rerun()

        if st.button("🚪  Çıkış Yap", use_container_width=True):
            from auth import logout
            logout()
            st.rerun()

        # Alt bilgi
        st.markdown("""
        <div style="position:fixed;bottom:16px;left:0;width:240px;
                    padding:0 16px;font-size:11px;color:#484f58;text-align:center">
            Wellness Admin v2.0
        </div>
        """, unsafe_allow_html=True)

    # ── ÜST HEADER ───────────────────────────────────────────────────────────
    simdi = datetime.now()
    sayfa_baslik = {
        "dashboard":       ("📊 Dashboard", "Genel bakış ve istatistikler"),
        "bekleyen_uyeler": ("⏳ Bekleyen Üyeler", "Onay bekleyen kayıtları yönetin"),
        "uyeler":          ("👥 Tüm Üyeler", "Kullanıcı yönetimi"),
        "analiz_kuyrugu":  ("🔬 Analiz Kuyruğu", "İnceleme bekleyen analizleri yönetin"),
        "tum_analizler":   ("📋 Tüm Analizler", "Geçmiş analiz kayıtları"),
    }
    baslik, alt_baslik = sayfa_baslik.get(
        st.session_state.admin_menu, ("Admin", "")
    )

    st.markdown(f"""
    <div class="admin-header">
        <div class="admin-header-left">
            <h2>{baslik}</h2>
            <p>{alt_baslik}</p>
        </div>
        <div class="admin-header-right">
            <div class="admin-clock">
                <div class="time">{simdi.strftime('%H:%M')}</div>
                <div class="date">{simdi.strftime('%d %B %Y, %A')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SAYFA İÇERİĞİ ────────────────────────────────────────────────────────
    menu = st.session_state.admin_menu

    if menu == "dashboard":
        _sayfa_dashboard(stats)
    elif menu == "bekleyen_uyeler":
        _sayfa_bekleyen_uyeler(stats)
    elif menu == "uyeler":
        _sayfa_uyeler()
    elif menu == "analiz_kuyrugu":
        _sayfa_analiz_kuyrugu()
    elif menu == "tum_analizler":
        _sayfa_tum_analizler()


# ══════════════════════════════════════════════════════════════════════════════
# SAYFALAR
# ══════════════════════════════════════════════════════════════════════════════

def _sayfa_dashboard(stats: dict):
    # Metrik kartlar
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card gold">
            <div class="metric-label">Aktif Üye</div>
            <div class="metric-value">{stats.get('aktif_uye', 0)}</div>
            <div class="metric-sub">Toplam: {stats.get('toplam_uye', 0)}</div>
        </div>
        <div class="metric-card red">
            <div class="metric-label">Onay Bekleyen</div>
            <div class="metric-value">{stats.get('bekleyen_uye', 0)}</div>
            <div class="metric-sub">Üye kaydı</div>
        </div>
        <div class="metric-card blue">
            <div class="metric-label">Bekleyen Analiz</div>
            <div class="metric-value">{stats.get('bekleyen_analiz', 0)}</div>
            <div class="metric-sub">İnceleme kuyruğu</div>
        </div>
        <div class="metric-card green">
            <div class="metric-label">Gönderilen Analiz</div>
            <div class="metric-value">{stats.get('gonderilen', 0)}</div>
            <div class="metric-sub">Bugün kayıt: {stats.get('bugun_kayit', 0)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Son kayıtlar + Son analizler
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="admin-card"><div class="admin-card-title">👥 Son Kayıtlar</div>', unsafe_allow_html=True)
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT ad_soyad, email, durum, kayit_tarihi
                FROM wellness_users WHERE rol='user'
                ORDER BY kayit_tarihi DESC LIMIT 6
            """)
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            for r in rows:
                tarih = str(r["kayit_tarihi"])[:10]
                st.markdown(f"""
                <div class="user-row">
                    <div class="user-info">
                        <div class="user-avatar">{r['ad_soyad'][0].upper()}</div>
                        <div>
                            <div class="user-name">{r['ad_soyad']}</div>
                            <div class="user-email">{r['email']}</div>
                        </div>
                    </div>
                    <div style="text-align:right">
                        {durum_badge(r['durum'])}
                        <div style="font-size:11px;color:#484f58;margin-top:4px">{tarih}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(str(e))
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="admin-card"><div class="admin-card-title">🔬 Son Analizler</div>', unsafe_allow_html=True)
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.ad_soyad, a.durum, a.olusturma_tarihi
                FROM wellness_analyses a
                JOIN wellness_users u ON u.id = a.user_id
                ORDER BY a.olusturma_tarihi DESC LIMIT 6
            """)
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            for r in rows:
                tarih = str(r["olusturma_tarihi"])[:16]
                st.markdown(f"""
                <div class="user-row">
                    <div class="user-info">
                        <div class="user-avatar" style="background:linear-gradient(135deg,#1f6feb,#388bfd)">
                            {r['ad_soyad'][0].upper()}
                        </div>
                        <div>
                            <div class="user-name">{r['ad_soyad']}</div>
                            <div class="user-email">{tarih}</div>
                        </div>
                    </div>
                    {durum_badge(r['durum'])}
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(str(e))
        st.markdown('</div>', unsafe_allow_html=True)

    # Son 7 gün grafiği
    st.markdown('<div class="admin-card"><div class="admin-card-title">📈 Son 7 Günlük Kayıt & Analiz</div>', unsafe_allow_html=True)
    try:
        import pandas as pd
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DATE(kayit_tarihi) AS gun, COUNT(*) AS kayit
            FROM wellness_users
            WHERE kayit_tarihi >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(kayit_tarihi) ORDER BY gun
        """)
        kayit_rows = cursor.fetchall()
        cursor.execute("""
            SELECT DATE(olusturma_tarihi) AS gun, COUNT(*) AS analiz
            FROM wellness_analyses
            WHERE olusturma_tarihi >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(olusturma_tarihi) ORDER BY gun
        """)
        analiz_rows = cursor.fetchall()
        cursor.close(); conn.close()

        if kayit_rows or analiz_rows:
            df_k = pd.DataFrame(kayit_rows) if kayit_rows else pd.DataFrame(columns=["gun","kayit"])
            df_a = pd.DataFrame(analiz_rows) if analiz_rows else pd.DataFrame(columns=["gun","analiz"])
            df_k["gun"] = df_k["gun"].astype(str)
            df_a["gun"] = df_a["gun"].astype(str)
            df = df_k.merge(df_a, on="gun", how="outer").fillna(0)
            df = df.set_index("gun")
            st.bar_chart(df)
        else:
            st.info("Henüz yeterli veri yok.")
    except Exception as e:
        st.error(str(e))
    st.markdown('</div>', unsafe_allow_html=True)


def _sayfa_bekleyen_uyeler(stats: dict):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, ad_soyad, email, kayit_tarihi
            FROM wellness_users
            WHERE durum='beklemede' AND rol='user'
            ORDER BY kayit_tarihi ASC
        """)
        bekleyenler = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception as e:
        st.error(str(e)); return

    if not bekleyenler:
        st.success("✅ Onay bekleyen üye yok. Harika!")
        return

    st.markdown(f"""
    <div style="background:rgba(248,81,73,.08);border:1px solid rgba(248,81,73,.25);
                border-radius:10px;padding:12px 18px;margin-bottom:20px;font-size:14px;color:#f85149">
        ⚠️ <strong>{len(bekleyenler)} üye</strong> onayınızı bekliyor
    </div>
    """, unsafe_allow_html=True)

    for u in bekleyenler:
        tarih = str(u["kayit_tarihi"])[:16]
        with st.expander(f"👤 {u['ad_soyad']}  —  {u['email']}  —  {tarih}"):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                neden = st.text_input(
                    "Red gerekçesi (opsiyonel)",
                    key=f"neden_{u['id']}",
                    placeholder="Sadece reddederken doldurun"
                )
            with c2:
                if st.button("✅ Onayla", key=f"onayla_{u['id']}",
                             use_container_width=True, type="primary"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE wellness_users
                        SET durum='aktif', onay_tarihi=%s WHERE id=%s
                    """, (datetime.now(), u["id"]))
                    conn.commit(); cursor.close(); conn.close()
                    kayit_onay_bildirimi(u["id"], u["ad_soyad"], u["email"])
                    st.success(f"✅ {u['ad_soyad']} onaylandı.")
                    st.rerun()
            with c3:
                if st.button("❌ Reddet", key=f"reddet_{u['id']}",
                             use_container_width=True):
                    neden_val = st.session_state.get(f"neden_{u['id']}", "")
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE wellness_users
                        SET durum='pasif', admin_notu=%s WHERE id=%s
                    """, (neden_val, u["id"]))
                    conn.commit(); cursor.close(); conn.close()
                    kayit_red_bildirimi(u["id"], u["ad_soyad"], u["email"], neden_val)
                    st.warning(f"❌ {u['ad_soyad']} reddedildi.")
                    st.rerun()


def _sayfa_uyeler():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.id, u.ad_soyad, u.email, u.durum, u.rol,
                   u.kayit_tarihi, u.onay_tarihi,
                   COUNT(DISTINCT f.id) AS form_sayi,
                   COUNT(DISTINCT a.id) AS analiz_sayi
            FROM wellness_users u
            LEFT JOIN wellness_forms    f ON f.user_id=u.id
            LEFT JOIN wellness_analyses a ON a.user_id=u.id
            GROUP BY u.id ORDER BY u.kayit_tarihi DESC
        """)
        users = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception as e:
        st.error(str(e)); return

    if not users:
        st.info("Henüz üye yok."); return

    # Filtre
    c1, c2 = st.columns([2, 1])
    with c1:
        arama = st.text_input("🔍 İsim veya e-posta ara", placeholder="Ada...")
    with c2:
        filtre = st.selectbox("Durum", ["Tümü","beklemede","aktif","pasif","engelli"])

    filtrelenmis = [
        u for u in users
        if (not arama or arama.lower() in u["ad_soyad"].lower() or arama.lower() in u["email"].lower())
        and (filtre == "Tümü" or u["durum"] == filtre)
    ]

    st.markdown(f"**{len(filtrelenmis)}** kullanıcı listeleniyor")
    st.divider()

    for u in filtrelenmis:
        tarih = str(u["kayit_tarihi"])[:10]
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
        with col1:
            st.markdown(f"""
            <div class="user-info">
                <div class="user-avatar">{u['ad_soyad'][0].upper()}</div>
                <div>
                    <div class="user-name">{u['ad_soyad']}
                        {'<span style="font-size:11px;color:#d4a847;margin-left:6px">👑 Admin</span>' if u['rol']=='admin' else ''}
                    </div>
                    <div class="user-email">{u['email']}</div>
                    <div class="user-email">Kayıt: {tarih} | Form: {u['form_sayi']} | Analiz: {u['analiz_sayi']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(durum_badge(u["durum"]), unsafe_allow_html=True)
        with col3:
            if u["durum"] != "aktif" and st.button("✅", key=f"aktif_{u['id']}", help="Aktif et"):
                _durum_guncelle(u["id"], "aktif")
                st.rerun()
        with col4:
            if u["durum"] == "aktif" and st.button("⏸", key=f"pasif_{u['id']}", help="Pasif et"):
                _durum_guncelle(u["id"], "pasif")
                st.rerun()
        with col5:
            if u["rol"] != "admin" and st.button("🚫 Engelle", key=f"engel_{u['id']}", use_container_width=True):
                _durum_guncelle(u["id"], "engelli")
                st.rerun()
        st.markdown("<hr style='border-color:#21262d;margin:6px 0'>", unsafe_allow_html=True)


def _durum_guncelle(user_id: int, durum: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE wellness_users SET durum=%s WHERE id=%s", (durum, user_id))
    conn.commit(); cursor.close(); conn.close()


def _sayfa_analiz_kuyrugu():
    # Eğer belirli bir analiz seçildiyse detay göster
    if st.session_state.admin_analiz_id:
        _analiz_detay(st.session_state.admin_analiz_id)
        return

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.id, u.ad_soyad, u.email, a.durum,
                   a.olusturma_tarihi, f.id AS form_id, a.user_id
            FROM wellness_analyses a
            JOIN wellness_users u ON u.id=a.user_id
            JOIN wellness_forms  f ON f.id=a.form_id
            WHERE a.durum IN ('taslak','admin_inceleme')
            ORDER BY a.olusturma_tarihi ASC
        """)
        kuyruk = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception as e:
        st.error(str(e)); return

    if not kuyruk:
        st.success("✅ Bekleyen analiz yok!")
        return

    st.markdown(f"""
    <div style="background:rgba(88,166,255,.08);border:1px solid rgba(88,166,255,.25);
                border-radius:10px;padding:12px 18px;margin-bottom:20px;font-size:14px;color:#58a6ff">
        📋 <strong>{len(kuyruk)} analiz</strong> inceleme bekliyor
    </div>
    """, unsafe_allow_html=True)

    for item in kuyruk:
        tarih = str(item["olusturma_tarihi"])[:16]
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.markdown(f"""
            <div class="user-info" style="padding:10px 0">
                <div class="user-avatar" style="background:linear-gradient(135deg,#1f6feb,#388bfd)">
                    {item['ad_soyad'][0].upper()}
                </div>
                <div>
                    <div class="user-name">{item['ad_soyad']}</div>
                    <div class="user-email">{item['email']} · {tarih}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(durum_badge(item["durum"]), unsafe_allow_html=True)
        with col3:
            if st.button("📝 İncele", key=f"incele_{item['id']}",
                         use_container_width=True, type="primary"):
                st.session_state.admin_analiz_id = item["id"]
                st.rerun()
        st.markdown("<hr style='border-color:#21262d;margin:2px 0'>", unsafe_allow_html=True)


def _analiz_detay(analiz_id: int):
    if st.button("← Kuyruğa Dön", use_container_width=False):
        st.session_state.admin_analiz_id = None
        st.rerun()

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, u.ad_soyad, u.email, f.form_json, f.id AS form_id
            FROM wellness_analyses a
            JOIN wellness_users u ON u.id=a.user_id
            JOIN wellness_forms  f ON f.id=a.form_id
            WHERE a.id=%s
        """, (analiz_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
    except Exception as e:
        st.error(str(e)); return

    if not row:
        st.error("Analiz bulunamadı."); return

    # Meta bilgi
    st.markdown(f"""
    <div class="analiz-meta">
        <div>👤 <strong>{row['ad_soyad']}</strong></div>
        <div>📧 {row['email']}</div>
        <div>📅 {str(row['olusturma_tarihi'])[:16]}</div>
        <div>{durum_badge(row['durum'])}</div>
    </div>
    """, unsafe_allow_html=True)

    # Form özeti
    with st.expander("📋 Kullanıcı Form Verilerini Göster"):
        try:
            fd = json.loads(row["form_json"])
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                **Profil**
                - Yaş: {fd.get('yas','—')} | Cinsiyet: {fd.get('cinsiyet','—')}
                - Boy: {fd.get('boy','—')} cm | Kilo: {fd.get('kilo','—')} kg
                - Bel: {fd.get('bel','—')} cm
                - Kronik: {fd.get('kronik','Yok')}
                """)
            with col2:
                st.markdown(f"""
                **Beslenme**
                - Diyet: {fd.get('diet','—')}
                - Su: {fd.get('su','—')} L/gün
                - Protein: {fd.get('protein','—')}
                - Balık: {fd.get('balik','—')}
                """)
            with col3:
                goaller = fd.get('goaller', {})
                top3 = sorted(goaller.items(), key=lambda x: -int(x[1]))[:3]
                st.markdown("**Top Hedefler**")
                for g, v in top3:
                    st.markdown(f"- {g}: {'⭐' * int(v)}")
                semptomlar = fd.get('semptomlar', [])
                if semptomlar:
                    st.markdown(f"**Semptomlar:** {', '.join(semptomlar[:3])}")
        except Exception:
            st.json(row["form_json"])

    st.divider()

    # Analiz düzenleme
    st.markdown("#### 🤖 Claude Taslak Analizi")
    st.caption("Aşağıdaki metni inceleyip gerekirse düzenleyin, ardından onaylayıp gönderin.")

    mevcut = row.get("admin_duzenleme") or row.get("analiz_metni", "")
    duzenlenmis = st.text_area(
        "Analiz metni:",
        value=mevcut,
        height=500,
        key=f"analiz_edit_{analiz_id}"
    )

    st.divider()
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("💾 Taslak Kaydet", use_container_width=True):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE wellness_analyses
                SET admin_duzenleme=%s, durum='admin_inceleme', admin_id=%s
                WHERE id=%s
            """, (duzenlenmis, st.session_state.user_id, analiz_id))
            conn.commit(); cursor.close(); conn.close()
            st.success("💾 Taslak kaydedildi.")
            st.rerun()

    with c2:
        if st.button("📨 Onayla & Gönder", use_container_width=True, type="primary"):
            son_metin = duzenlenmis or mevcut
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE wellness_analyses
                SET admin_duzenleme=%s, durum='kullaniciya_gonderildi',
                    admin_id=%s, onay_tarihi=%s, gonderim_tarihi=%s
                WHERE id=%s
            """, (son_metin, st.session_state.user_id,
                  datetime.now(), datetime.now(), analiz_id))
            cursor.execute(
                "UPDATE wellness_forms SET durum='onaylandi' WHERE id=%s",
                (row["form_id"],)
            )
            conn.commit(); cursor.close(); conn.close()

            user = kullanici_getir_by_id(row["user_id"])
            if user:
                analiz_hazir_bildirimi(
                    user["id"], user["ad_soyad"], user["email"], analiz_id
                )
            st.success("✅ Analiz onaylandı ve kullanıcıya gönderildi!")
            st.session_state.admin_analiz_id = None
            st.rerun()

    with c3:
        if st.button("🗑️ Reddet", use_container_width=True):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE wellness_analyses SET durum='reddedildi' WHERE id=%s",
                (analiz_id,)
            )
            cursor.execute(
                "UPDATE wellness_forms SET durum='reddedildi' WHERE id=%s",
                (row["form_id"],)
            )
            conn.commit(); cursor.close(); conn.close()
            st.warning("❌ Analiz reddedildi.")
            st.session_state.admin_analiz_id = None
            st.rerun()


def _sayfa_tum_analizler():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.id, u.ad_soyad, u.email, a.durum,
                   a.olusturma_tarihi, a.gonderim_tarihi
            FROM wellness_analyses a
            JOIN wellness_users u ON u.id=a.user_id
            ORDER BY a.olusturma_tarihi DESC LIMIT 100
        """)
        rows = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception as e:
        st.error(str(e)); return

    if not rows:
        st.info("Henüz analiz yok."); return

    # Filtre
    c1, c2 = st.columns([3, 1])
    with c1:
        arama = st.text_input("🔍 Kullanıcı ara", placeholder="Ada...")
    with c2:
        filtre = st.selectbox("Durum", ["Tümü", "taslak", "admin_inceleme",
                                         "kullaniciya_gonderildi", "reddedildi"])

    filtrelenmis = [
        r for r in rows
        if (not arama or arama.lower() in r["ad_soyad"].lower()
            or arama.lower() in r["email"].lower())
        and (filtre == "Tümü" or r["durum"] == filtre)
    ]

    st.markdown(f"**{len(filtrelenmis)}** analiz")
    st.divider()

    for r in filtrelenmis:
        tarih = str(r["olusturma_tarihi"])[:16]
        gonderim = str(r["gonderim_tarihi"])[:16] if r["gonderim_tarihi"] else "—"
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            st.markdown(f"""
            <div class="user-info" style="padding:8px 0">
                <div class="user-avatar" style="background:linear-gradient(135deg,#2ea043,#56d364)">
                    {r['ad_soyad'][0].upper()}
                </div>
                <div>
                    <div class="user-name">{r['ad_soyad']}</div>
                    <div class="user-email">{r['email']} · {tarih}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(durum_badge(r["durum"]), unsafe_allow_html=True)
        with col3:
            st.caption(f"📨 {gonderim}")
        with col4:
            if st.button("🔍 Gör", key=f"goruntule_all_{r['id']}", use_container_width=True):
                st.session_state.admin_analiz_id = r["id"]
                st.session_state.admin_menu = "analiz_kuyrugu"
                st.rerun()
        st.markdown("<hr style='border-color:#21262d;margin:2px 0'>", unsafe_allow_html=True)
