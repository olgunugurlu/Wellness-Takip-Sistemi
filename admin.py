"""
admin.py — Admin paneli
Sekmeler: İstatistikler | Bekleyen Üyeler | Tüm Üyeler | Analiz Kuyruğu | Tüm Analizler
"""
import streamlit as st
import json
import re
from datetime import datetime
from db import get_connection
from notifications import (
    kayit_onay_bildirimi, kayit_red_bildirimi, analiz_hazir_bildirimi
)


def _metin_temizle(metin: str) -> str:
    """Kaydedilmeden önce JSON bloğunu ve BÖLÜM 2 başlığını metinden temizler."""
    # ```json ... ``` bloğunu sil
    metin = re.sub(r'```json.*?```', '', metin, flags=re.DOTALL)
    # Düz ``` ... ``` bloğunu sil
    metin = re.sub(r'```.*?```', '', metin, flags=re.DOTALL)
    # BÖLÜM 2 başlığı ve sonrasını sil
    metin = re.sub(r'##\s*BÖLÜM 2.*', '', metin, flags=re.DOTALL)
    # Sondaki --- çizgilerini temizle
    metin = re.sub(r'---\s*$', '', metin, flags=re.MULTILINE)
    return metin.strip()


def _render_metin(metin: str):
    """Uzun analiz metnini bölümlere ayırarak render eder."""
    # JSON bloğunu ve BÖLÜM 2 başlığını temizle
    metin = re.sub(r'## BÖLÜM 2.*', '', metin, flags=re.DOTALL).strip()
    metin = re.sub(r'```json.*?```', '', metin, flags=re.DOTALL).strip()

    bolumler = re.split(r'(?=^#{2,3} )', metin, flags=re.MULTILINE)
    for bolum in bolumler:
        bolum = bolum.strip()
        if not bolum:
            continue
        with st.container():
            if len(bolum) > 4000:
                satirlar = bolum.split('\n')
                parca = []
                uzunluk = 0
                for satir in satirlar:
                    parca.append(satir)
                    uzunluk += len(satir)
                    if uzunluk > 3000:
                        if '\n'.join(parca).strip():
                            st.markdown('\n'.join(parca))
                        parca = []
                        uzunluk = 0
                if parca and '\n'.join(parca).strip():
                    st.markdown('\n'.join(parca))
            else:
                st.markdown(bolum)


# ── YARDIMCI ─────────────────────────────────────────────────────────────────
def durum_renk(durum: str) -> str:
    return {
        "beklemede":           "🟡",
        "aktif":               "🟢",
        "pasif":               "⚪",
        "engelli":             "🔴",
        "taslak":              "📝",
        "admin_inceleme":      "👁️",
        "onaylandi":           "✅",
        "kullaniciya_gonderildi": "📨",
        "reddedildi":          "❌",
        "isleniyor":           "⚙️",
    }.get(durum, "❓")


def kullanici_getir(user_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM wellness_users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    return user


# ── ANA PANEL ────────────────────────────────────────────────────────────────
def show_admin_panel():
    # ── ÜST MENÜ ─────────────────────────────────────────────────────────────
    col_baslik, col_butonlar = st.columns([3, 1])
    with col_baslik:
        st.markdown("## 🛡️ Admin Paneli")
    with col_butonlar:
        st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
        if st.button("📋 Forma Geç", use_container_width=True):
            st.session_state.page = "app"
            st.rerun()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            from auth import logout
            logout()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 İstatistikler",
        "⏳ Bekleyen Üyeler",
        "👥 Tüm Üyeler",
        "🔬 Analiz Kuyruğu",
        "📋 Tüm Analizler",
        "📧 E-posta Test",
    ])

    # ── TAB 1: İSTATİSTİKLER ─────────────────────────────────────────────────
    with tab1:
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT COUNT(*) AS s FROM wellness_users WHERE rol='user' AND durum='beklemede'")
            bekleyen_uye = cursor.fetchone()["s"]

            cursor.execute("SELECT COUNT(*) AS s FROM wellness_users WHERE durum='aktif'")
            aktif_uye = cursor.fetchone()["s"]

            cursor.execute("SELECT COUNT(*) AS s FROM wellness_analyses WHERE durum='taslak'")
            bekleyen_analiz = cursor.fetchone()["s"]

            cursor.execute("SELECT COUNT(*) AS s FROM wellness_analyses WHERE durum='kullaniciya_gonderildi'")
            gonderilen = cursor.fetchone()["s"]

            cursor.close(); conn.close()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("⏳ Onay Bekleyen Üye", bekleyen_uye,
                      delta="İşlem gerekli" if bekleyen_uye > 0 else None,
                      delta_color="inverse")
            c2.metric("✅ Aktif Üye", aktif_uye)
            c3.metric("🔬 Bekleyen Analiz", bekleyen_analiz,
                      delta="İşlem gerekli" if bekleyen_analiz > 0 else None,
                      delta_color="inverse")
            c4.metric("📨 Gönderilen Analiz", gonderilen)

            # Son 7 gün grafik
            st.divider()
            st.markdown("#### Son 7 Günlük Kayıt")
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DATE(kayit_tarihi) AS gun, COUNT(*) AS sayi
                FROM wellness_users
                WHERE kayit_tarihi >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(kayit_tarihi) ORDER BY gun
            """)
            rows = cursor.fetchall()
            cursor.close(); conn.close()
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows)
                df["gun"] = df["gun"].astype(str)
                st.bar_chart(df.set_index("gun")["sayi"])
            else:
                st.info("Henüz veri yok.")
        except Exception as e:
            st.error(f"Hata: {e}")

    # ── TAB 2: BEKLEYEN ÜYELER ────────────────────────────────────────────────
    with tab2:
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, ad_soyad, email, kayit_tarihi
                FROM wellness_users
                WHERE durum = 'beklemede' AND rol = 'user'
                ORDER BY kayit_tarihi ASC
            """)
            bekleyenler = cursor.fetchall()
            cursor.close(); conn.close()

            if not bekleyenler:
                st.success("Onay bekleyen üye yok.")
            else:
                st.warning(f"**{len(bekleyenler)}** üye onayınızı bekliyor.")

                for u in bekleyenler:
                    with st.expander(
                        f"⏳ {u['ad_soyad']} — {u['email']} "
                        f"({str(u['kayit_tarihi'])[:10]})"
                    ):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            neden = st.text_input(
                                "Red gerekçesi (opsiyonel)",
                                key=f"red_neden_{u['id']}",
                                placeholder="Sadece reddederken yazın"
                            )
                        with col2:
                            if st.button("✅ Onayla", key=f"onayla_{u['id']}",
                                         use_container_width=True, type="primary"):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE wellness_users
                                    SET durum='aktif', onay_tarihi=%s
                                    WHERE id=%s
                                """, (datetime.now(), u["id"]))
                                conn.commit()
                                cursor.close(); conn.close()
                                kayit_onay_bildirimi(u["id"], u["ad_soyad"], u["email"])
                                st.success(f"✅ {u['ad_soyad']} onaylandı.")
                                st.rerun()
                        with col3:
                            if st.button("❌ Reddet", key=f"reddet_{u['id']}",
                                         use_container_width=True):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE wellness_users
                                    SET durum='pasif', admin_notu=%s
                                    WHERE id=%s
                                """, (neden, u["id"]))
                                conn.commit()
                                cursor.close(); conn.close()
                                kayit_red_bildirimi(u["id"], u["ad_soyad"], u["email"], neden)
                                st.warning(f"❌ {u['ad_soyad']} reddedildi.")
                                st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    # ── TAB 3: TÜM ÜYELER ────────────────────────────────────────────────────
    with tab3:
        if "aktif_kullanici_id" not in st.session_state:
            st.session_state.aktif_kullanici_id = None

        if st.session_state.aktif_kullanici_id:
            _kullanici_detay_goster(st.session_state.aktif_kullanici_id)
        else:
            _tum_uyeler_listesi()

    # ── TAB 4: ANALİZ KUYRUĞU ────────────────────────────────────────────────
    with tab4:
        st.markdown("Burada Claude tarafından oluşturulan taslak analizleri inceleyip "
                    "düzenleyebilir ve kullanıcıya gönderebilirsiniz.")
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.id, u.ad_soyad, u.email, a.durum,
                       a.olusturma_tarihi, f.id AS form_id
                FROM wellness_analyses a
                JOIN wellness_users u ON u.id = a.user_id
                JOIN wellness_forms  f ON f.id = a.form_id
                WHERE a.durum IN ('taslak','admin_inceleme')
                ORDER BY a.olusturma_tarihi ASC
            """)
            kuyruk = cursor.fetchall()
            cursor.close(); conn.close()

            if not kuyruk:
                st.success("Bekleyen analiz yok. 🎉")
            else:
                st.info(f"**{len(kuyruk)}** analiz inceleme bekliyor.")

                for item in kuyruk:
                    with st.expander(
                        f"{durum_renk(item['durum'])} {item['ad_soyad']} — "
                        f"{str(item['olusturma_tarihi'])[:16]}"
                    ):
                        # Form verisini göster
                        conn = get_connection()
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute(
                            "SELECT form_json FROM wellness_forms WHERE id=%s",
                            (item["form_id"],)
                        )
                        form_row = cursor.fetchone()

                        # Analizi getir — buffered=True büyük metinler için
                        cursor.execute("""
                            SELECT id, analiz_metni, analiz_json, admin_duzenleme
                            FROM wellness_analyses WHERE id=%s
                        """, (item["id"],))
                        analiz_row = cursor.fetchone()
                        # bytes ise decode et
                        if analiz_row:
                            for alan in ["analiz_metni", "admin_duzenleme"]:
                                v = analiz_row.get(alan)
                                if v and isinstance(v, (bytes, bytearray)):
                                    analiz_row[alan] = v.decode("utf-8", errors="replace")
                        cursor.close(); conn.close()

                        # Form verisi özeti
                        if form_row:
                            try:
                                fd = json.loads(form_row["form_json"])
                                st.markdown(f"""
**Kullanıcı:** {fd.get('isim','—')} | **Yaş:** {fd.get('yas','—')} |
**Cinsiyet:** {fd.get('cinsiyet','—')} | **Kronik:** {fd.get('kronik','Yok')}
                                """)
                                with st.expander("📋 Form detaylarını göster"):
                                    st.json(fd)
                            except Exception:
                                pass

                        # Mevcut analiz metni
                        if analiz_row:
                            st.divider()
                            st.markdown("#### 🤖 Claude Taslak Analizi")

                            # Düzenleme alanı
                            mevcut = (analiz_row.get("admin_duzenleme")
                                      or analiz_row.get("analiz_metni", ""))
                            duzenlenmis = st.text_area(
                                "Analizi inceleyin ve gerekirse düzenleyin:",
                                value=mevcut,
                                height=400,
                                key=f"duzenle_{item['id']}"
                            )

                            c1, c2, c3 = st.columns(3)
                            with c1:
                                if st.button("💾 Taslak Kaydet",
                                             key=f"kaydet_{item['id']}",
                                             use_container_width=True):
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    temiz = _metin_temizle(duzenlenmis)
                                    cursor.execute("""
                                        UPDATE wellness_analyses
                                        SET admin_duzenleme=%s, durum='admin_inceleme',
                                            admin_id=%s
                                        WHERE id=%s
                                    """, (temiz,
                                          st.session_state.user_id,
                                          item["id"]))
                                    conn.commit()
                                    cursor.close(); conn.close()
                                    st.success("Taslak kaydedildi.")
                                    st.rerun()

                            with c2:
                                if st.button("📨 Onayla & Gönder",
                                             key=f"gonder_{item['id']}",
                                             type="primary",
                                             use_container_width=True):
                                    son_metin = _metin_temizle(duzenlenmis or mevcut)
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE wellness_analyses
                                        SET admin_duzenleme=%s,
                                            durum='kullaniciya_gonderildi',
                                            admin_id=%s,
                                            onay_tarihi=%s,
                                            gonderim_tarihi=%s
                                        WHERE id=%s
                                    """, (son_metin,
                                          st.session_state.user_id,
                                          datetime.now(), datetime.now(),
                                          item["id"]))
                                    # Formu da güncelle
                                    cursor.execute("""
                                        UPDATE wellness_forms SET durum='onaylandi'
                                        WHERE id=%s
                                    """, (item["form_id"],))
                                    conn.commit()
                                    cursor.close(); conn.close()

                                    # Kullanıcıyı bul ve bildir
                                    user = kullanici_getir(item.get("user_id") or
                                           _user_id_from_analiz(item["id"]))
                                    if user:
                                        analiz_hazir_bildirimi(
                                            user["id"], user["ad_soyad"],
                                            user["email"], item["id"]
                                        )
                                    st.success("✅ Analiz onaylandı ve kullanıcıya gönderildi!")
                                    st.rerun()

                            with c3:
                                if st.button("🗑️ Reddet",
                                             key=f"reddet_analiz_{item['id']}",
                                             use_container_width=True):
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE wellness_analyses SET durum='taslak'
                                        WHERE id=%s
                                    """, (item["id"],))
                                    cursor.execute("""
                                        UPDATE wellness_forms SET durum='reddedildi'
                                        WHERE id=%s
                                    """, (item["form_id"],))
                                    conn.commit()
                                    cursor.close(); conn.close()
                                    st.warning("Analiz reddedildi.")
                                    st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")
            import traceback
            st.code(traceback.format_exc())

    # ── TAB 5: TÜM ANALİZLER ─────────────────────────────────────────────────
    with tab5:
        if "aktif_analiz_id" not in st.session_state:
            st.session_state.aktif_analiz_id = None

        if st.session_state.aktif_analiz_id:
            _analiz_detay_goster(st.session_state.aktif_analiz_id)
        else:
            _tum_analizler_listesi()


    # ── TAB 6: E-POSTA TEST ──────────────────────────────────────────────────
    with tab6:
        st.markdown("#### 📧 E-posta Bağlantı Testi")
        st.caption("Mail ayarlarınızın doğru çalışıp çalışmadığını buradan test edebilirsiniz.")

        try:
            cfg = st.secrets.get("email", {})
            if cfg:
                st.success(f"✅ E-posta ayarları yüklendi")
                c1, c2 = st.columns(2)
                with c1:
                    st.code(f"""
Host : {cfg.get('smtp_host','?')}
Port : {cfg.get('smtp_port','?')}
Gönderici: {cfg.get('gonderici_email','?')}
                    """)
                with c2:
                    test_alici = st.text_input("Test e-postası gönderilecek adres",
                                               value=cfg.get('gonderici_email',''),
                                               key="test_mail_alici")
                    if st.button("📨 Test Maili Gönder", use_container_width=True, type="primary"):
                        from notifications import eposta_gonder, eposta_sablonu
                        sonuc = eposta_gonder(
                            test_alici, "Test Kullanıcı",
                            "Wellness Sistemi — Test E-postası",
                            eposta_sablonu("Test Kullanıcı", "E-posta Testi ✓",
                                "Bu e-posta Wellness Admin panelinden gönderilmiş bir test mesajıdır. "
                                "E-posta sisteminiz başarıyla çalışıyor!"
                            )
                        )
                        if sonuc:
                            st.success(f"✅ Test maili başarıyla gönderildi → {test_alici}")
            else:
                st.error("❌ E-posta ayarları bulunamadı.")
                st.info("""
Streamlit Cloud → Settings → Secrets bölümüne şunu ekleyin:

```toml
[email]
smtp_host       = "smtp-mail.outlook.com"
smtp_port       = 587
gonderici_email = "o_ugurlu@hotmail.com"
smtp_sifre      = "UYGULAMA_SIFRENIZ"
gonderici_ad    = "Wellness Analiz"
```

**Hotmail için uygulama şifresi:**
outlook.com → Güvenlik → İki adımlı doğrulama (açık olmalı) → Uygulama şifreleri → Yeni oluştur
                """)
        except Exception as e:
            st.error(f"Hata: {e}")


def _durum_guncelle(uid, durum):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE wellness_users SET durum=%s WHERE id=%s", (durum, uid))
    conn.commit(); cursor.close(); conn.close()


def _tum_uyeler_listesi():
    """Tüm üyeleri tıklanabilir kart listesi olarak gösterir."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            arama = st.text_input("🔍 İsim veya e-posta ara", key="uye_arama", placeholder="Ada...")
        with c2:
            filtre = st.selectbox("Durum", ["Tümü","aktif","beklemede","pasif","engelli"], key="uye_filtre")
        with c3:
            rol_f = st.selectbox("Rol", ["Tümü","user","admin"], key="uye_rol")

        where, params = [], []
        if arama:
            where.append("(u.ad_soyad LIKE %s OR u.email LIKE %s)")
            params.extend([f"%{arama}%", f"%{arama}%"])
        if filtre != "Tümü":
            where.append("u.durum=%s"); params.append(filtre)
        if rol_f != "Tümü":
            where.append("u.rol=%s"); params.append(rol_f)
        ws = "WHERE " + " AND ".join(where) if where else ""

        cursor.execute(f"""
            SELECT u.id, u.ad_soyad, u.email, u.durum, u.rol, u.kayit_tarihi,
                   COUNT(DISTINCT f.id) AS form_sayi,
                   COUNT(DISTINCT a.id) AS analiz_sayi
            FROM wellness_users u
            LEFT JOIN wellness_forms    f ON f.user_id = u.id
            LEFT JOIN wellness_analyses a ON a.user_id = u.id
            {ws}
            GROUP BY u.id
            ORDER BY u.kayit_tarihi DESC
        """, params)
        users = cursor.fetchall()
        cursor.close(); conn.close()

        if not users:
            st.info("Üye bulunamadı.")
            return

        st.caption(f"**{len(users)}** üye listeleniyor")
        st.divider()

        durum_renk_map = {
            "aktif":"#3fb950", "beklemede":"#d4a847",
            "pasif":"#7d8590", "engelli":"#f85149"
        }
        durum_icon_map = {
            "aktif":"✅", "beklemede":"⏳", "pasif":"⏸️", "engelli":"🚫"
        }

        for u in users:
            tarih = str(u["kayit_tarihi"])[:10]
            renk  = durum_renk_map.get(u["durum"], "#7d8590")
            icon  = durum_icon_map.get(u["durum"], "❓")

            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1, 1])
            with col1:
                rol_tag = " 👑" if u["rol"] == "admin" else ""
                st.markdown(f"**{u['ad_soyad']}**{rol_tag}")
                st.caption(f"{u['email']} · 📅 {tarih} · 📋 {u['form_sayi']} form · 🔬 {u['analiz_sayi']} analiz")
            with col2:
                st.caption(f"{icon} {u['durum']}")
            with col3:
                if u["durum"] != "aktif" and st.button("✅", key=f"uye_aktif_{u['id']}", help="Aktif et"):
                    _durum_guncelle(u["id"], "aktif")
                    kayit_onay_bildirimi(u["id"], u["ad_soyad"], u["email"])
                    st.rerun()
            with col4:
                if u["durum"] == "aktif" and st.button("⏸️", key=f"uye_pasif_{u['id']}", help="Pasif et"):
                    _durum_guncelle(u["id"], "pasif")
                    st.rerun()
            with col5:
                if st.button("👁 Detay", key=f"uye_detay_{u['id']}", use_container_width=True, type="primary"):
                    st.session_state.aktif_kullanici_id = u["id"]
                    st.rerun()

            st.markdown("<hr style='border-color:#21262d;margin:4px 0'>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Hata: {e}")


def _kullanici_detay_goster(uid: int):
    """Seçilen kullanıcının profil + analizlerini detay sayfasında gösterir."""
    if st.button("← Üye Listesine Dön", use_container_width=False):
        st.session_state.aktif_kullanici_id = None
        st.rerun()

    st.divider()

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Kullanıcı bilgileri
        cursor.execute("SELECT * FROM wellness_users WHERE id=%s", (uid,))
        u = cursor.fetchone()
        cursor.close(); conn.close()

        if not u:
            st.warning("Kullanıcı bulunamadı.")
            return

        # ── PROFİL KARTI ─────────────────────────────────────────────────────
        durum_etiket = {
            "aktif": "✅ Aktif", "beklemede": "⏳ Beklemede",
            "pasif": "⏸️ Pasif", "engelli": "🚫 Engelli"
        }
        rol_etiket = "👑 Admin" if u["rol"] == "admin" else "👤 Kullanıcı"

        st.markdown(f"## {u['ad_soyad']}  {rol_etiket}")
        c1, c2, c3 = st.columns(3)
        c1.metric("E-posta", u["email"])
        c2.metric("Durum", durum_etiket.get(u["durum"], u["durum"]))
        c3.metric("Kayıt Tarihi", str(u["kayit_tarihi"])[:10])
        if u.get("onay_tarihi"):
            st.caption(f"✅ Admin onay tarihi: {str(u['onay_tarihi'])[:10]}")

        # ── HIZLI İŞLEMLER ────────────────────────────────────────────────────
        st.markdown("**Kullanıcı İşlemleri**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if u["durum"] != "aktif" and st.button("✅ Aktif Et", use_container_width=True, type="primary"):
                _durum_guncelle(uid, "aktif")
                kayit_onay_bildirimi(uid, u["ad_soyad"], u["email"])
                st.success("Aktif edildi."); st.rerun()
        with c2:
            if u["durum"] == "aktif" and st.button("⏸️ Pasif Et", use_container_width=True):
                _durum_guncelle(uid, "pasif")
                st.warning("Pasif edildi."); st.rerun()
        with c3:
            if u["durum"] != "engelli" and st.button("🚫 Engelle", use_container_width=True):
                _durum_guncelle(uid, "engelli")
                st.error("Engellendi."); st.rerun()
        with c4:
            if u["rol"] != "admin" and st.button("👑 Admin Yap", use_container_width=True):
                conn2 = get_connection()
                cur2 = conn2.cursor()
                cur2.execute("UPDATE wellness_users SET rol='admin' WHERE id=%s", (uid,))
                conn2.commit(); cur2.close(); conn2.close()
                st.success("Admin yapıldı."); st.rerun()

        if u.get("admin_notu"):
            st.info(f"📝 Admin notu: {u['admin_notu']}")

        st.divider()

        # ── KULLANICININ ANALİZLERİ ────────────────────────────────────────────
        st.markdown("#### 🔬 Analizler")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.id, a.durum, a.olusturma_tarihi, a.gonderim_tarihi,
                   analiz_json IS NOT NULL AS json_var,
                   LEFT(COALESCE(a.admin_duzenleme, a.analiz_metni), 100) AS ozet
            FROM wellness_analyses a
            WHERE a.user_id = %s
            ORDER BY a.olusturma_tarihi DESC
        """, (uid,))
        analizler = cursor.fetchall()
        cursor.close(); conn.close()

        if not analizler:
            st.info("Bu kullanıcıya ait analiz yok.")
        else:
            durum_icon = {"taslak":"📝","admin_inceleme":"👁️",
                         "onaylandi":"✅","kullaniciya_gonderildi":"📨","reddedildi":"❌"}
            renk_map   = {"taslak":"#58a6ff","admin_inceleme":"#d4a847",
                         "onaylandi":"#3fb950","kullaniciya_gonderildi":"#3fb950","reddedildi":"#f85149"}

            for a in analizler:
                tarih  = str(a["olusturma_tarihi"])[:16]
                gonder = str(a["gonderim_tarihi"])[:16] if a["gonderim_tarihi"] else "—"
                icon   = durum_icon.get(a["durum"],"❓")
                ar     = renk_map.get(a["durum"],"#7d8590")
                jbadge = "🟢" if a["json_var"] else "🔴"

                c1, c2, c3, c4 = st.columns([4, 2, 0.5, 1])
                with c1:
                    st.markdown(f"**{str(a.get('ozet',''))[:80]}...**")
                    st.caption(f"📅 {tarih} · 📨 {gonder}")
                with c2:
                    st.caption(f"{icon} {a['durum'].replace('_',' ')}")
                with c3:
                    st.caption(jbadge)
                with c4:
                    if st.button("Görüntüle", key=f"kdet_analiz_{a['id']}", use_container_width=True, type="primary"):
                        st.session_state.aktif_analiz_id = a["id"]
                        st.session_state.admin_menu = "tum_analizler"
                        st.rerun()

                st.markdown("<hr style='border-color:#21262d;margin:4px 0'>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Hata: {e}")
        import traceback
        st.code(traceback.format_exc())


def _tum_analizler_listesi():
    """Tüm analizleri tıklanabilir kart listesi olarak gösterir."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Filtre ve arama
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            arama = st.text_input("🔍 Kullanıcı ara", placeholder="İsim veya e-posta...", key="analiz_arama")
        with c2:
            filtre = st.selectbox("Durum", ["Tümü","taslak","admin_inceleme",
                                            "kullaniciya_gonderildi","reddedildi"],
                                  key="analiz_filtre")
        with c3:
            limit = st.selectbox("Göster", [10, 25, 50, 100], key="analiz_limit")

        # Sorgu
        where = []
        params = []
        if arama:
            where.append("(u.ad_soyad LIKE %s OR u.email LIKE %s)")
            params.extend([f"%{arama}%", f"%{arama}%"])
        if filtre != "Tümü":
            where.append("a.durum = %s")
            params.append(filtre)
        where_sql = "WHERE " + " AND ".join(where) if where else ""

        cursor.execute(f"""
            SELECT a.id, u.ad_soyad, u.email, a.durum,
                   a.olusturma_tarihi, a.gonderim_tarihi,
                   analiz_json IS NOT NULL AS json_var,
                   LEFT(COALESCE(a.admin_duzenleme, a.analiz_metni), 80) AS ozet
            FROM wellness_analyses a
            JOIN wellness_users u ON u.id = a.user_id
            {where_sql}
            ORDER BY a.olusturma_tarihi DESC
            LIMIT %s
        """, params + [limit])
        rows = cursor.fetchall()
        cursor.close(); conn.close()

        if not rows:
            st.info("Analiz bulunamadı.")
            return

        st.caption(f"**{len(rows)}** analiz listeleniyor")
        st.divider()

        durum_icon = {
            "taslak": "📝",
            "admin_inceleme": "👁️",
            "onaylandi": "✅",
            "kullaniciya_gonderildi": "📨",
            "reddedildi": "❌",
        }
        durum_renk_map = {
            "taslak": "#58a6ff",
            "admin_inceleme": "#d4a847",
            "onaylandi": "#3fb950",
            "kullaniciya_gonderildi": "#3fb950",
            "reddedildi": "#f85149",
        }

        for row in rows:
            tarih = str(row["olusturma_tarihi"])[:16]
            gonderim = str(row["gonderim_tarihi"])[:16] if row["gonderim_tarihi"] else "—"
            durum = row["durum"]
            icon = durum_icon.get(durum, "❓")
            renk = durum_renk_map.get(durum, "#7d8590")
            json_badge = "🟢 JSON" if row["json_var"] else "🔴 JSON"

            col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 1, 1])
            with col1:
                st.markdown(f"""
<div style="padding:4px 0">
  <span style="font-size:14px;font-weight:600;color:#e6edf3">{row['ad_soyad']}</span>
  <span style="font-size:12px;color:#7d8590;margin-left:8px">{row['email']}</span>
  <br><span style="font-size:11px;color:#484f58">{str(row.get('ozet',''))[:70]}...</span>
</div>
""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
<div style="padding:4px 0;font-size:12px;color:#7d8590">
  📅 {tarih}<br>📨 {gonderim}
</div>
""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
<span style="background:rgba(0,0,0,.2);border:1px solid {renk};color:{renk};
             font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px">
  {icon} {durum.replace('_',' ')}
</span>
""", unsafe_allow_html=True)
            with col4:
                st.caption(json_badge)
            with col5:
                if st.button("Görüntüle", key=f"goruntule5_{row['id']}", use_container_width=True, type="primary"):
                    st.session_state.aktif_analiz_id = row["id"]
                    st.rerun()

            st.markdown("<hr style='border-color:#21262d;margin:4px 0'>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Hata: {e}")


def _analiz_detay_goster(aid: int):
    """Seçilen analizi tam ekran detay olarak gösterir."""
    if st.button("← Listeye Dön", use_container_width=False):
        st.session_state.aktif_analiz_id = None
        st.rerun()

    st.divider()

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("""
            SELECT a.id, COALESCE(a.admin_duzenleme, a.analiz_metni) AS metin,
                   a.analiz_json, a.durum, u.ad_soyad, u.email
            FROM wellness_analyses a
            JOIN wellness_users u ON u.id = a.user_id
            WHERE a.id = %s
        """, (aid,))
        row = cursor.fetchone()
        cursor.close(); conn.close()

        if not row:
            st.warning("Analiz bulunamadı.")
            return

        metin = row.get("metin","") or ""
        analiz_json_str = row.get("analiz_json")
        kullanici_adi = row.get("ad_soyad","Kullanici")

        if isinstance(metin, (bytes, bytearray)):
            metin = metin.decode("utf-8", errors="replace")
        if analiz_json_str and isinstance(analiz_json_str, (bytes, bytearray)):
            analiz_json_str = analiz_json_str.decode("utf-8", errors="replace")

        # Başlık
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"### 👤 {kullanici_adi} — {row['email']}")
            st.caption(f"Analiz ID: {aid} | Durum: {row['durum']}")
        with c2:
            # PDF butonu
            try:
                from pdf_export import analiz_pdf_olustur
                pdf_bytes = analiz_pdf_olustur(
                    analiz_metni=metin,
                    analiz_json_str=analiz_json_str,
                    kullanici_adi=kullanici_adi,
                )
                dosya_adi = f"wellness_{kullanici_adi.replace(' ','_').lower()}_{aid}.pdf"
                st.download_button(
                    label="📄 PDF İndir",
                    data=pdf_bytes,
                    file_name=dosya_adi,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            except Exception as e:
                st.error(f"PDF hatası: {e}")

        st.divider()

        # Analiz metni
        _render_metin(metin)
        st.divider()

        # Takviye kartları
        takviye_data = None
        if analiz_json_str:
            try:
                from claude_service import _normalize_json
                takviye_data = _normalize_json(json.loads(analiz_json_str))
            except Exception:
                pass
        if takviye_data is None:
            try:
                from claude_service import parse_response
                _, takviye_data = parse_response(metin)
            except Exception:
                pass
        if takviye_data:
            from claude_service import render_supplement_cards
            render_supplement_cards(takviye_data)

    except Exception as e:
        st.error(f"Hata: {e}")
        import traceback
        st.code(traceback.format_exc())


def _user_id_from_analiz(analiz_id: int) -> int | None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM wellness_analyses WHERE id=%s", (analiz_id,)
        )
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row[0] if row else None
    except Exception:
        return None
