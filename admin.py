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
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.id, u.ad_soyad, u.email, u.durum, u.rol,
                       u.kayit_tarihi,
                       COUNT(DISTINCT f.id) AS form_sayi,
                       COUNT(DISTINCT a.id) AS analiz_sayi
                FROM wellness_users u
                LEFT JOIN wellness_forms    f ON f.user_id = u.id
                LEFT JOIN wellness_analyses a ON a.user_id = u.id
                GROUP BY u.id
                ORDER BY u.kayit_tarihi DESC
            """)
            users = cursor.fetchall()
            cursor.close(); conn.close()

            if not users:
                st.info("Henüz üye yok.")
            else:
                import pandas as pd
                df = pd.DataFrame(users)
                df["kayit_tarihi"] = df["kayit_tarihi"].astype(str).str[:16]
                df["durum"] = df["durum"].apply(lambda x: f"{durum_renk(x)} {x}")
                df.columns = ["ID","Ad Soyad","E-posta","Durum","Rol",
                              "Kayıt","Form","Analiz"]
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("#### Üye İşlemleri")
                uid = st.number_input("Kullanıcı ID", min_value=1, step=1, key="uid_islem")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("✅ Aktif Et", use_container_width=True):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE wellness_users SET durum='aktif' WHERE id=%s", (uid,)
                        )
                        conn.commit(); conn.close()
                        st.success("Aktif edildi."); st.rerun()
                with c2:
                    if st.button("⏸️ Pasif Et", use_container_width=True):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE wellness_users SET durum='pasif' WHERE id=%s", (uid,)
                        )
                        conn.commit(); conn.close()
                        st.warning("Pasif edildi."); st.rerun()
                with c3:
                    if st.button("🚫 Engelle", use_container_width=True):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE wellness_users SET durum='engelli' WHERE id=%s", (uid,)
                        )
                        conn.commit(); conn.close()
                        st.error("Engellendi."); st.rerun()
                with c4:
                    if st.button("👑 Admin Yap", use_container_width=True):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE wellness_users SET rol='admin' WHERE id=%s", (uid,)
                        )
                        conn.commit(); conn.close()
                        st.success("Admin yapıldı."); st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

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
                            SELECT id, analiz_metni, admin_duzenleme
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
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.id, u.ad_soyad, u.email, a.durum,
                       a.olusturma_tarihi, a.gonderim_tarihi,
                       LEFT(COALESCE(a.admin_duzenleme, a.analiz_metni), 100) AS ozet
                FROM wellness_analyses a
                JOIN wellness_users u ON u.id = a.user_id
                ORDER BY a.olusturma_tarihi DESC
                LIMIT 50
            """)
            rows = cursor.fetchall()
            cursor.close(); conn.close()

            if rows:
                import pandas as pd
                df = pd.DataFrame(rows)
                df["durum"] = df["durum"].apply(lambda x: f"{durum_renk(x)} {x}")
                df["olusturma_tarihi"] = df["olusturma_tarihi"].astype(str).str[:16]
                df["gonderim_tarihi"] = df["gonderim_tarihi"].astype(str).str[:16]
                df.columns = ["ID","Kullanıcı","E-posta","Durum",
                              "Oluşturma","Gönderim","Özet"]
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.divider()
                aid = st.number_input("Analiz ID (detay)", min_value=1, step=1)
                if st.button("🔍 Analizi Göster"):
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT COALESCE(admin_duzenleme, analiz_metni) AS metin
                        FROM wellness_analyses WHERE id=%s
                    """, (aid,))
                    row = cursor.fetchone()
                    conn.close()
                    if row:
                        metin = row["metin"]
                        if isinstance(metin, (bytes, bytearray)):
                            metin = metin.decode("utf-8", errors="replace")
                        _render_metin(metin)
                    else:
                        st.warning("Bulunamadı.")
            else:
                st.info("Henüz analiz yok.")
        except Exception as e:
            st.error(f"Hata: {e}")


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