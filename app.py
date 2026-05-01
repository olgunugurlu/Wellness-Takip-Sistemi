import streamlit as st
import json
from datetime import datetime

st.set_page_config(
    page_title="Wellness Analiz",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

from db             import get_connection, init_db
from auth           import register_user, login_user, set_session, logout, is_logged_in, is_admin, restore_session
from claude_service import stream_analysis, parse_response, render_supplement_cards, GOALS, SYMPTOMS, SUPPS, LABS
from admin          import show_admin_panel
from ethics         import kullanim_sartlari_goster, risk_analizi, risk_uyarisi_goster, analiz_dil_uyarisi, YASAL_UYARI_HTML
from notifications  import (
    bildirim_ekle, bildirimleri_getir, okunmamis_sayi,
    tum_bildirimleri_oku, bildirimi_okundu_isaretle,
    kayit_bekleme_bildirimi
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"]{background-color:#0d1117;color:#e6edf3}
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#0d1117 0%,#161b22 60%,#0d1117 100%)}
.hero{text-align:center;padding:2.5rem 1rem 1.5rem}
.hero-badge{display:inline-block;background:rgba(212,168,71,.12);border:1px solid rgba(212,168,71,.3);
  color:#d4a847;font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;
  padding:4px 14px;border-radius:100px;margin-bottom:1rem}
.hero h1{font-size:2.2rem;font-weight:700;
  background:linear-gradient(135deg,#e6edf3 0%,#d4a847 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin:0 0 .5rem;line-height:1.2}
.hero p{color:#7d8590;font-size:15px;max-width:420px;margin:0 auto;line-height:1.6}
.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:1.5rem;margin-bottom:1rem}
.card-title{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#d4a847;margin-bottom:1rem}
.p-wrap{display:flex;align-items:center;justify-content:center;margin-bottom:.4rem}
.p-dot{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:600;flex-shrink:0;border:1.5px solid #30363d;background:#1c2333;color:#7d8590}
.p-dot.active{background:rgba(88,166,255,.2);border-color:#58a6ff;color:#58a6ff}
.p-dot.done{background:rgba(63,185,80,.2);border-color:#3fb950;color:#3fb950}
.p-line{flex:1;max-width:56px;height:1px;background:#30363d}
.p-line.done{background:#3fb950}
.p-labels{display:flex;justify-content:space-between;max-width:340px;margin:0 auto 1.5rem;font-size:11px;color:#7d8590}
.notif-dot{display:inline-block;background:#f85149;color:#fff;border-radius:50%;
  width:18px;height:18px;font-size:10px;font-weight:700;text-align:center;line-height:18px;margin-left:6px}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stDecoration"]{display:none}
</style>
""", unsafe_allow_html=True)

# ── VERİTABANI BAŞLAT ────────────────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"Veritabanı başlatılamadı: {e}")
    st.stop()

# ── OTURUMU GERİ YÜKLE (sayfa yenilenince çalışır) ───────────────────────────
if not st.session_state.get("logged_in", False):
    restore_session()

# ── SESSION STATE ─────────────────────────────────────────────────────────────
defaults = {
    "logged_in":False,"user_id":None,"user_name":"",
    "user_email":"","user_rol":"user",
    "step":1,"form_data":{},"analysis_result":None,
    "page":"login","goruntulenen_analiz_id":None
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── YARDIMCILAR ───────────────────────────────────────────────────────────────
def progress_bar(current):
    labels = ["Profil","Hedefler","Beslenme","Takviye","Analiz"]
    dots = ""
    for i,_ in enumerate(labels):
        n=i+1
        cls="done" if n<current else ("active" if n==current else "")
        icon="✓" if n<current else str(n)
        dots+=f'<div class="p-dot {cls}">{icon}</div>'
        if i<len(labels)-1:
            dots+=f'<div class="p-line {"done" if n<current else ""}"></div>'
    lbls="".join(f"<span>{l}</span>" for l in labels)
    st.markdown(f'<div class="p-wrap">{dots}</div><div class="p-labels">{lbls}</div>',
                unsafe_allow_html=True)


def save_form(form_data:dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO wellness_forms (user_id, form_json, durum) VALUES (%s,%s,'isleniyor')",
        (st.session_state.user_id, json.dumps(form_data, ensure_ascii=False))
    )
    form_id = cursor.lastrowid
    conn.commit(); cursor.close(); conn.close()
    return form_id


def _metin_temizle(metin: str) -> str:
    """JSON bloğunu ve BÖLÜM 2 başlığını metinden temizler — sadece analiz metnini saklar."""
    import re
    metin = re.sub(r'```json.*?```', '', metin, flags=re.DOTALL)
    metin = re.sub(r'```.*?```', '', metin, flags=re.DOTALL)
    metin = re.sub(r'##\s*BÖLÜM 2.*', '', metin, flags=re.DOTALL)
    metin = re.sub(r'---\s*$', '', metin, flags=re.MULTILINE)
    return metin.strip()


def save_analysis_draft(form_id:int, analiz_metni:str) -> int:
    """Analiz metnini ve JSON yapısını ayrı kolonlara kaydeder."""
    import re as _re
    # JSON bloğunu bul ve ayır
    json_str = None
    json_match = _re.search(r'```json\s*(.*?)\s*```', analiz_metni, _re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()

    # Analiz metnini temizle
    temiz_metin = _metin_temizle(analiz_metni)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wellness_analyses
            (form_id, user_id, analiz_metni, analiz_json, durum)
        VALUES (%s,%s,%s,%s,'taslak')
    """, (form_id, st.session_state.user_id, temiz_metin, json_str))
    analiz_id = cursor.lastrowid
    conn.commit(); cursor.close(); conn.close()
    return analiz_id


def get_user_analyses():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.id, a.durum, a.olusturma_tarihi, a.gonderim_tarihi,
               LEFT(COALESCE(a.admin_duzenleme, a.analiz_metni),120) AS ozet
        FROM wellness_analyses a
        WHERE a.user_id = %s
        ORDER BY a.olusturma_tarihi DESC
        LIMIT 15
    """, (st.session_state.user_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


def get_analiz_metni(analiz_id:int) -> dict | None:
    """Analiz metnini ve JSON yapısını veritabanından okur.
    Admin tüm analizleri görebilir, kullanıcı sadece kendi analizini."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    if st.session_state.get("user_rol") == "admin":
        cursor.execute("""
            SELECT COALESCE(admin_duzenleme, analiz_metni) AS metin,
                   analiz_json, durum
            FROM wellness_analyses WHERE id=%s
        """, (analiz_id,))
    else:
        cursor.execute("""
            SELECT COALESCE(admin_duzenleme, analiz_metni) AS metin,
                   analiz_json, durum
            FROM wellness_analyses WHERE id=%s AND user_id=%s
        """, (analiz_id, st.session_state.user_id))
    row = cursor.fetchone()
    if row:
        for alan in ["metin", "analiz_json"]:
            v = row.get(alan)
            if v and isinstance(v, (bytes, bytearray)):
                row[alan] = v.decode("utf-8", errors="replace")
    cursor.close(); conn.close()
    return row


def render_analiz_metni(metin: str):
    """Uzun analiz metnini bölümlere ayırarak render eder.
    Streamlit tek seferinde çok uzun markdown kesebilir — bu fonksiyon bunu önler."""
    import re

    # Önce BÖLÜM 2 ve JSON bloğunu temizle (parse_response zaten ayırıyor ama emin olmak için)
    metin = re.sub(r'## BÖLÜM 2.*', '', metin, flags=re.DOTALL).strip()
    metin = re.sub(r'```json.*?```', '', metin, flags=re.DOTALL).strip()

    # ## ve ### başlıklarına göre böl
    bolumler = re.split(r'(?=^#{2,3} )', metin, flags=re.MULTILINE)

    for bolum in bolumler:
        bolum = bolum.strip()
        if not bolum:
            continue
        # Her bölümü ayrı container içinde render et
        with st.container():
            # 4000 karakterden uzunsa tekrar böl (satır bazında)
            if len(bolum) > 4000:
                satirlar = bolum.split('\n')
                parcalar = []
                parca = []
                uzunluk = 0
                for satir in satirlar:
                    parca.append(satir)
                    uzunluk += len(satir)
                    if uzunluk > 3000:
                        parcalar.append('\n'.join(parca))
                        parca = []
                        uzunluk = 0
                if parca:
                    parcalar.append('\n'.join(parca))
                for p in parcalar:
                    if p.strip():
                        st.markdown(p)
            else:
                st.markdown(bolum)


# ════════════════════════════════════════════════════════════════════════════
# GİRİŞ YAPILMAMIŞ
# ════════════════════════════════════════════════════════════════════════════
if not is_logged_in():
    st.markdown("""
    <div class="hero">
        <div class="hero-badge">Yapay Zeka Destekli</div>
        <h1>Wellness & Takviye<br>Analiz Sistemi</h1>
        <p>Kişisel sağlık profilinizi girin, uzman destekli beslenme ve takviye planınızı alın.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 Giriş Yap","📝 Kayıt Ol"])

    with tab_login:
        with st.form("login_form"):
            email    = st.text_input("E-posta", placeholder="ada@example.com")
            password = st.text_input("Parola", type="password")
            submit   = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")
        if submit:
            ok, msg, user = login_user(email, password)
            if ok:
                set_session(user)
                st.session_state.page = "admin" if user["rol"]=="admin" else "app"
                st.success(msg); st.rerun()
            else:
                st.error(msg)

    with tab_register:
        with st.form("register_form"):
            ad_soyad = st.text_input("Ad Soyad", placeholder="Ada Öztürk")
            email_r  = st.text_input("E-posta",  placeholder="ada@example.com")
            pass_r   = st.text_input("Parola",   type="password")
            pass_r2  = st.text_input("Parola (tekrar)", type="password")
            submit_r = st.form_submit_button("Kayıt Ol", use_container_width=True, type="primary")

        sartlar_ok = kullanim_sartlari_goster()

        if submit_r:
            if not all([ad_soyad, email_r, pass_r, pass_r2]):
                st.warning("Tüm alanları doldurun.")
            elif pass_r != pass_r2:
                st.error("Parolalar eşleşmiyor.")
            elif len(pass_r) < 6:
                st.error("Parola en az 6 karakter olmalı.")
            elif not sartlar_ok:
                st.error("Kullanım şartlarını kabul etmelisiniz.")
            else:
                ok, msg, user_id = register_user(ad_soyad, email_r, pass_r, sartlar_kabul=True)
                if ok:
                    kayit_bekleme_bildirimi(user_id, ad_soyad, email_r)
                    st.success("✅ Kaydınız alındı! Admin onayı bekleniyor. Onaylandığında e-posta ile bilgilendirileceksiniz.")
                else:
                    st.error(msg)

# ════════════════════════════════════════════════════════════════════════════
# GİRİŞ YAPILMIŞ
# ════════════════════════════════════════════════════════════════════════════
else:
    uid = st.session_state.user_id

    # ── SİDEBAR ──────────────────────────────────────────────────────────────
    with st.sidebar:
        okunmamis = okunmamis_sayi(uid)
        notif_html = (f'<span class="notif-dot">{okunmamis}</span>' if okunmamis > 0 else "")
        st.markdown(f"### 👤 {st.session_state.user_name}{notif_html}",
                    unsafe_allow_html=True)
        st.caption(st.session_state.user_email)
        st.divider()

        if is_admin():
            if st.button("🛡️ Admin Paneli", use_container_width=True):
                st.session_state.page="admin"; st.rerun()
            if st.button("📋 Forma Dön", use_container_width=True):
                st.session_state.page="app"; st.rerun()
            st.divider()

        # Bildirimler
        st.markdown("#### 🔔 Bildirimler")
        bildirimler = bildirimleri_getir(uid)
        if bildirimler:
            if okunmamis > 0:
                if st.button("Tümünü okundu işaretle", use_container_width=True):
                    tum_bildirimleri_oku(uid); st.rerun()
            for b in bildirimler[:5]:
                okundu_stil = "" if b["okundu"] else "font-weight:600;"
                tip_emoji = {
                    "analiz_hazir":"🌿","kayit_onaylandi":"✅",
                    "kayit_reddedildi":"❌","bilgi":"ℹ️"
                }.get(b["tip"],"📬")
                with st.expander(f"{tip_emoji} {b['baslik']}", expanded=not b["okundu"]):
                    st.write(b["mesaj"])
                    st.caption(str(b["tarih"])[:16])
                    if not b["okundu"]:
                        bildirimi_okundu_isaretle(b["id"])
                    # Analiz hazırsa direkt görüntüle butonu
                    if b["tip"] == "analiz_hazir":
                        if st.button("Analizi Görüntüle", key=f"notif_analiz_{b['id']}"):
                            st.session_state.page="analizlerim"; st.rerun()
        else:
            st.caption("Henüz bildirim yok.")

        st.divider()

        # Geçmiş analizler
        st.markdown("#### 📜 Analizlerim")
        analizler = get_user_analyses()
        durum_etiket = {
            "taslak":"📝 Hazırlanıyor",
            "admin_inceleme":"👁️ İnceleniyor",
            "onaylandi":"✅ Onaylandı",
            "kullaniciya_gonderildi":"📨 Hazır",
        }
        if analizler:
            for a in analizler:
                etiket = durum_etiket.get(a["durum"], a["durum"])
                tarih  = str(a["olusturma_tarihi"])[:10]
                with st.expander(f"{etiket} — {tarih}"):
                    st.caption(str(a["ozet"])+"...")
                    if a["durum"] == "kullaniciya_gonderildi":
                        if st.button("Görüntüle", key=f"goruntule_{a['id']}"):
                            st.session_state.goruntulenen_analiz_id = a["id"]
                            st.session_state.page = "analiz_goruntule"
                            st.rerun()
                    else:
                        st.info(etiket)
        else:
            st.caption("Henüz analiz yok.")

        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            logout(); st.rerun()

    # ── ADMIN PANELİ ─────────────────────────────────────────────────────────
    if st.session_state.page == "admin" and is_admin():
        show_admin_panel()
        st.stop()

    # ── ANALİZ GÖRÜNTÜLE ─────────────────────────────────────────────────────
    if st.session_state.page == "analiz_goruntule":
        analiz_id = st.session_state.goruntulenen_analiz_id
        row = get_analiz_metni(analiz_id)
        # Debug: JSON kolonu var mı?
        if row:
            json_var = bool(row.get("analiz_json"))
            json_uzunluk = len(row.get("analiz_json") or "")
            st.caption(f"🔍 Debug: analiz_id={analiz_id} | json_var={json_var} | json_uzunluk={json_uzunluk}")
        if row:
            st.markdown("""
            <div class="hero">
                <div class="hero-badge">Wellness Analiziniz</div>
                <h1>Kişisel Planınız</h1>
            </div>
            """, unsafe_allow_html=True)
            # analiz_json kolonundan oku
            takviye_data = None
            analiz_metni = row.get("metin", "")

            analiz_json_str = row.get("analiz_json")
            if analiz_json_str:
                try:
                    raw_json = json.loads(analiz_json_str)
                    from claude_service import _normalize_json
                    takviye_data = _normalize_json(raw_json)
                except Exception as e:
                    st.warning(f"JSON parse hatası: {e}")
                    takviye_data = None

            # analiz_json yoksa veya parse olmadıysa metinden dene
            if takviye_data is None and analiz_metni:
                try:
                    _, takviye_data = parse_response(analiz_metni)
                except Exception:
                    takviye_data = None

            render_analiz_metni(analiz_metni)
            st.divider()
            if takviye_data:
                render_supplement_cards(takviye_data)
            else:
                st.info("Takviye kartları yüklenemedi. Yeni bir analiz talebi oluşturun.")
            st.markdown(YASAL_UYARI_HTML, unsafe_allow_html=True)
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "📄 Raporu İndir",
                    data=row["metin"],
                    file_name=f"wellness_analiz_{analiz_id}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with c2:
                if st.button("← Yeni Form Doldur", use_container_width=True):
                    st.session_state.page="app"
                    st.session_state.step=1
                    st.session_state.form_data={}
                    st.session_state.analysis_result=None
                    st.rerun()
        else:
            st.error("Analiz bulunamadı.")
            if st.button("← Geri"):
                st.session_state.page="app"; st.rerun()
        st.stop()

    # ── ANA UYGULAMA ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero">
        <div class="hero-badge">Yapay Zeka + Uzman Destekli</div>
        <h1>Wellness & Takviye<br>Analiz Sistemi</h1>
    </div>
    """, unsafe_allow_html=True)

    progress_bar(st.session_state.step)

    # ── ADIM 1: PROFİL ───────────────────────────────────────────────────────
    if st.session_state.step == 1:
        st.markdown("### 👤 Temel Profil")
        fd = st.session_state.form_data

        st.markdown('<div class="card"><div class="card-title">Kimlik & Ölçümler</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            isim     = st.text_input("Ad soyad", value=fd.get("isim",st.session_state.user_name))
            cinsiyet = st.selectbox("Cinsiyet",["","Kadın","Erkek","Belirtmek istemiyorum"],
                                    index=["","Kadın","Erkek","Belirtmek istemiyorum"].index(fd.get("cinsiyet","")))
            boy      = st.number_input("Boy (cm)",100,250,int(fd.get("boy",170)))
        with c2:
            yas  = st.number_input("Yaş",10,110,int(fd.get("yas",30)))
            kilo = st.number_input("Kilo (kg)",30,250,int(fd.get("kilo",70)))
            bel  = st.number_input("Bel çevresi (cm)",40,200,int(fd.get("bel",80)))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">Yaşam Tarzı</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        meslek_opts = ["","Tam masa başı (7+ saat)","Karma (yarı oturma)","Fiziksel / Ayakta","Ağır fiziksel iş"]
        egz_opts    = ["","Hiç yapmıyorum","Haftada 1-2 gün","Haftada 3-4 gün","Haftada 5+ gün"]
        egztur_opts = ["Yok","Yürüyüş / Koşu","Ağırlık antrenmanı","Karma (güç + kardiyo)","Yoga / Pilates","Spor"]
        uyku_opts   = ["","5 saatten az","5-6 saat","6-7 saat","7-8 saat","8+ saat"]
        with c1:
            meslek   = st.selectbox("Günlük aktivite",meslek_opts,index=meslek_opts.index(fd.get("meslek","")))
            egzersiz = st.selectbox("Haftalık egzersiz",egz_opts,index=egz_opts.index(fd.get("egzersiz","")))
        with c2:
            egztur = st.selectbox("Egzersiz türü",egztur_opts,index=egztur_opts.index(fd.get("egztur","Yok")))
            uyku   = st.selectbox("Uyku süresi",uyku_opts,index=uyku_opts.index(fd.get("uyku","")))
        kronik = st.text_input("Kronik hastalık / kullanılan ilaçlar",value=fd.get("kronik",""),placeholder="Yoksa boş bırakın")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Devam → Hedefler", type="primary", use_container_width=True):
            st.session_state.form_data.update({
                "isim":isim,"yas":yas,"cinsiyet":cinsiyet,"boy":boy,
                "kilo":kilo,"bel":bel,"meslek":meslek,"egzersiz":egzersiz,
                "egztur":egztur,"uyku":uyku,"kronik":kronik
            })
            st.session_state.step=2; st.rerun()

    # ── ADIM 2: HEDEFLER ─────────────────────────────────────────────────────
    elif st.session_state.step == 2:
        st.markdown("### 🎯 Hedefler & Şikayetler")
        st.markdown('<div class="card"><div class="card-title">Hedef Öncelikleri (1=düşük · 5=kritik)</div>', unsafe_allow_html=True)
        prev_goals = st.session_state.form_data.get("goaller",{})
        goaller = {}
        for goal in GOALS:
            goaller[goal] = st.slider(goal,1,5,int(prev_goals.get(goal,3)),key=f"g_{goal}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">Mevcut Semptomlar</div>', unsafe_allow_html=True)
        prev_symp = st.session_state.form_data.get("semptomlar",[])
        semptomlar = []
        cols = st.columns(2)
        for i,symp in enumerate(SYMPTOMS):
            with cols[i%2]:
                if st.checkbox(symp,value=(symp in prev_symp),key=f"s_{symp}"):
                    semptomlar.append(symp)
        st.markdown('</div>', unsafe_allow_html=True)

        c1,c2 = st.columns(2)
        with c1:
            if st.button("← Geri",use_container_width=True):
                st.session_state.step=1; st.rerun()
        with c2:
            if st.button("Devam → Beslenme",type="primary",use_container_width=True):
                st.session_state.form_data.update({"goaller":goaller,"semptomlar":semptomlar})
                st.session_state.step=3; st.rerun()

    # ── ADIM 3: BESLENME ─────────────────────────────────────────────────────
    elif st.session_state.step == 3:
        st.markdown("### 🥗 Beslenme Profili")
        fd = st.session_state.form_data

        diet_opts  = ["","Karma / Standart","Akdeniz diyeti","Vegan","Vejetaryen","Ketojenik","Aralıklı oruç (IF)","Yüksek proteinli","Glütensiz"]
        ogun_opts  = ["","1-2 öğün","3 öğün","4-5 öğün","Düzensiz"]
        balik_opts = ["","Hiç yemiyorum","Haftada 1","Haftada 2-3","Haftada 4+"]
        alkol_opts = ["","İçmiyorum","Nadir (ayda 1-2)","Haftalık (1-3 kadeh)","Düzenli (4+/hafta)"]
        prot_opts  = ["","Yetersiz","Orta","Yeterli","Yüksek (takip ediyorum)"]
        sebze_opts = ["","0-1 porsiyon","2-3 porsiyon","4-5 porsiyon","5+ porsiyon"]
        seker_opts = ["","Yüksek — neredeyse her gün","Orta — haftada birkaç kez","Düşük — nadiren","Tüketmiyorum"]
        ferm_opts  = ["","Hiç tüketmiyorum","Nadiren","Haftada birkaç kez","Her gün"]

        st.markdown('<div class="card"><div class="card-title">Diyet Örüntüsü</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            diet  = st.selectbox("Diyet tipi",diet_opts,index=diet_opts.index(fd.get("diet","")))
            su    = st.number_input("Günlük su (litre)",0.5,10.0,float(fd.get("su",1.5)),0.5)
            balik = st.selectbox("Haftalık balık",balik_opts,index=balik_opts.index(fd.get("balik","")))
        with c2:
            ogun  = st.selectbox("Günlük öğün",ogun_opts,index=ogun_opts.index(fd.get("ogun","")))
            kahve = st.number_input("Günlük kahve (fincan)",0,15,int(fd.get("kahve",2)))
            alkol = st.selectbox("Alkol",alkol_opts,index=alkol_opts.index(fd.get("alkol","")))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">Besin Grupları</div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            protein  = st.selectbox("Protein yeterliliği",prot_opts,index=prot_opts.index(fd.get("protein","")))
            seker    = st.selectbox("Şeker & işlenmiş gıda",seker_opts,index=seker_opts.index(fd.get("seker","")))
        with c2:
            sebze    = st.selectbox("Sebze-meyve (porsiyon/gün)",sebze_opts,index=sebze_opts.index(fd.get("sebze","")))
            fermente = st.selectbox("Fermente gıda",ferm_opts,index=ferm_opts.index(fd.get("fermente","")))
        alerji = st.text_input("Besin alerjisi / intoleransı",value=fd.get("alerji",""),placeholder="Yoksa boş bırakın")
        notlar = st.text_area("Ek notlar",value=fd.get("notlar",""),height=90,placeholder="Beklentiler, özel durum, doktor tavsiyeleri...")
        st.markdown('</div>', unsafe_allow_html=True)

        c1,c2 = st.columns(2)
        with c1:
            if st.button("← Geri",use_container_width=True):
                st.session_state.step=2; st.rerun()
        with c2:
            if st.button("Devam → Takviyeler",type="primary",use_container_width=True):
                st.session_state.form_data.update({
                    "diet":diet,"ogun":ogun,"su":su,"kahve":kahve,
                    "balik":balik,"alkol":alkol,"protein":protein,
                    "sebze":sebze,"seker":seker,"fermente":fermente,
                    "alerji":alerji,"notlar":notlar
                })
                st.session_state.step=4; st.rerun()

    # ── ADIM 4: TAKVİYELER & LAB ─────────────────────────────────────────────
    elif st.session_state.step == 4:
        st.markdown("### 💊 Takviyeler & Laboratuvar")
        fd = st.session_state.form_data

        st.markdown('<div class="card"><div class="card-title">Kullanılan Takviyeler — doz / marka / sıklık</div>', unsafe_allow_html=True)
        takviyeler = {}
        prev_takv = fd.get("takviyeler",{})
        c1,c2 = st.columns(2)
        for i,sup in enumerate(SUPPS):
            with (c1 if i%2==0 else c2):
                v = st.text_input(sup,value=prev_takv.get(sup,""),placeholder="Doz / marka / sıklık",key=f"sp_{sup}")
                if v: takviyeler[sup]=v
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">🔬 Laboratuvar Değerleri — İsteğe Bağlı</div>', unsafe_allow_html=True)
        st.caption("Girilirse analiz çok daha hassas olur.")
        lab = {}
        prev_lab = fd.get("lab",{})
        c1,c2 = st.columns(2)
        for i,lbl in enumerate(LABS):
            with (c1 if i%2==0 else c2):
                v = st.text_input(lbl,value=prev_lab.get(lbl,""),placeholder="—",key=f"lb_{lbl}")
                if v: lab[lbl]=v
        st.markdown('</div>', unsafe_allow_html=True)

        c1,c2 = st.columns(2)
        with c1:
            if st.button("← Geri",use_container_width=True):
                st.session_state.step=3; st.rerun()
        with c2:
            if st.button("Devam → Analiz",type="primary",use_container_width=True):
                st.session_state.form_data.update({"takviyeler":takviyeler,"lab":lab})
                st.session_state.step=5; st.rerun()

    # ── ADIM 5: ANALİZ ───────────────────────────────────────────────────────
    elif st.session_state.step == 5:
        st.markdown("### ✨ Analiz Talebi")
        fd = st.session_state.form_data

        if not st.session_state.analysis_result:
            # Risk filtresi
            risk = risk_analizi(fd)
            devam = risk_uyarisi_goster(risk)

            if devam:
                analiz_dil_uyarisi()

                st.markdown("""
                <div class="card">
                <div class="card-title">Nasıl çalışır?</div>
                <ol style="color:#7d8590;font-size:14px;line-height:2;padding-left:20px">
                <li>Formunuz gönderilir ve yapay zeka taslak analizi oluşturur</li>
                <li>Uzman (admin) taslağı inceler ve gerekirse düzenler</li>
                <li>Onaylanan analiz size bildirilir — e-posta + sistem bildirimi</li>
                <li>Analizinizi sol menüden görüntüleyebilirsiniz</li>
                </ol>
                </div>
                """, unsafe_allow_html=True)

                c1,c2 = st.columns(2)
                with c1:
                    if st.button("← Geri",use_container_width=True):
                        st.session_state.step=4; st.rerun()
                with c2:
                    analiz_btn = st.button("📤 Analiz Talebi Gönder",
                                           type="primary", use_container_width=True)
                    if risk["seviye"]=="orta" and not st.session_state.get("risk_onay",False):
                        analiz_btn=False

                    if analiz_btn:
                        try:
                            with st.spinner("Taslak analiz oluşturuluyor, lütfen bekleyin..."):
                                # Form kaydet
                                form_id = save_form(fd)
                                # Claude analiz
                                placeholder = st.empty()
                                full_text=""
                                for chunk in stream_analysis(fd):
                                    full_text+=chunk
                                    placeholder.markdown(full_text+"▌")
                                placeholder.empty()
                                # Taslak kaydet
                                save_analysis_draft(form_id, full_text)
                            st.session_state.analysis_result = full_text
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")
            else:
                if st.button("← Geri",use_container_width=True):
                    st.session_state.step=4; st.rerun()

        else:
            # Gönderim onayı ekranı
            st.success("✅ Analiz talebiniz alındı!")
            st.markdown("""
            <div class="card">
            <div style="text-align:center;padding:1rem 0">
                <div style="font-size:48px;margin-bottom:12px">🌿</div>
                <div style="font-size:18px;font-weight:600;color:#e6edf3;margin-bottom:8px">
                    Taslak analiziniz oluşturuldu
                </div>
                <div style="font-size:14px;color:#7d8590;line-height:1.7;max-width:400px;margin:0 auto">
                    Uzman incelemesinden geçtikten sonra analiziniz onaylanacak 
                    ve size <strong style="color:#d4a847">e-posta + sistem bildirimi</strong> 
                    ile haber verilecek.<br><br>
                    Ortalama inceleme süresi: <strong style="color:#3fb950">24-48 saat</strong>
                </div>
            </div>
            </div>
            """, unsafe_allow_html=True)

            c1,c2 = st.columns(2)
            with c1:
                if st.button("🔄 Yeni Form Doldur",use_container_width=True):
                    st.session_state.step=1
                    st.session_state.form_data={}
                    st.session_state.analysis_result=None
                    st.rerun()
            with c2:
                if st.button("📜 Analizlerimi Gör",use_container_width=True):
                    st.info("Analizlerinize sol menüden ulaşabilirsiniz.")