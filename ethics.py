"""
ethics.py — Etik ve hukuki koruma katmanı

İçerik:
- Kullanım şartları metni
- Risk filtresi (yüksek riskli durumları tespit eder)
- Yasal uyarı gösterimi
- Dil rehberi (tavsiye → bilgi)
"""

import streamlit as st

# ── YÜKSEK RİSKLİ DURUMLAR ──────────────────────────────────────────────────
# Bu anahtar kelimeler formda tespit edilirse kullanıcı uyarılır
YUKSEK_RISK_DURUMLAR = {
    "kanser": "Onkoloji tedavisi gören bireyler için takviye kullanımı mutlaka onkolog onayı gerektirir.",
    "kemoterapi": "Kemoterapi sürecinde takviye etkileşimleri kritik önem taşır. Lütfen onkoloğunuza danışın.",
    "diyaliz": "Böbrek yetmezliği ve diyaliz hastalarında mineral ve vitamin dozları hekim tarafından belirlenmelidir.",
    "böbrek yetmezliği": "Böbrek hastalığında takviye metabolizması farklıdır. Mutlaka nefroloji uzmanına danışın.",
    "kalp yetmezliği": "Kalp yetmezliğinde bazı takviyeler kontrendike olabilir. Kardiyoloğunuza danışın.",
    "warfarin": "Warfarin ile pek çok takviye etkileşir (K vitamini, omega-3, sarımsak vb.). Hekiminizi bilgilendirin.",
    "kumadin": "Kan sulandırıcı ilaç kullanımında takviye seçimi hekim gözetiminde yapılmalıdır.",
    "epilepsi": "Epilepsi ilaçları ile bazı takviyeler etkileşebilir. Nöroloğunuza danışın.",
    "lityum": "Lityum kullanan bireylerde takviye seçimi psikiyatrist gözetiminde yapılmalıdır.",
    "hamile": "Gebelikte takviye kullanımı mutlaka kadın doğum uzmanı gözetiminde olmalıdır.",
    "hamilelik": "Gebelikte takviye kullanımı mutlaka kadın doğum uzmanı gözetiminde olmalıdır.",
    "emzirme": "Emzirme döneminde alınan takviyeler anne sütüne geçebilir. Hekim onayı alın.",
}

ORTA_RISK_DURUMLAR = {
    "diyabet": "Diyabet hastalarında kan şekerini etkileyen takviyeler (krom, magnezyum, alfa lipoik asit vb.) dikkatli kullanılmalıdır.",
    "hipertansiyon": "Tansiyon ilaçları bazı takviyelerle etkileşebilir. Kardiyoloğunuzu bilgilendirin.",
    "hipotiroidi": "Tiroid ilaçları ile bazı mineraller (demir, kalsiyum, çinko) emilim etkileşimine girebilir.",
    "hipertiroidi": "Tiroid hastalığında iyot içeren takviyelerden kaçının.",
    "crohn": "İnflamatuar bağırsak hastalıklarında bazı prebiyotikler semptomu kötüleştirebilir.",
    "kolit": "İnflamatuar bağırsak hastalıklarında takviye seçimi gastroenterolog gözetiminde yapılmalıdır.",
    "karaciğer": "Karaciğer hastalığında yağda çözünen vitaminler birikim yapabilir. Gastroenterolog onayı alın.",
    "osteoporoz": "Kemik yoğunluğunu etkileyen takviyeler (kalsiyum, D vitamini, K2) hekim önerisiyle alınmalıdır.",
}

# ── KULLANIM ŞARTLARI ────────────────────────────────────────────────────────
KULLANIM_SARTLARI = """
**KULLANIM ŞARTLARI VE SORUMLULUK REDDİ**

Bu platform, kullanıcılara beslenme ve takviye konusunda **genel bilgi** sunmak amacıyla tasarlanmıştır.

**Önemli Uyarılar:**

1. **Tıbbi Tavsiye Değildir:** Bu platform tarafından sunulan içerikler, 1219 sayılı Tababet ve Şuabatı San'atlarının Tarzı İcrasına Dair Kanun kapsamında tıbbi teşhis, tedavi veya reçete niteliği taşımamaktadır.

2. **Uzman Görüşü Zorunluluğu:** Herhangi bir takviye ürünü kullanmaya başlamadan önce, özellikle kronik bir hastalığınız veya düzenli kullandığınız ilaçlarınız varsa, mutlaka bir hekim veya eczacıya danışmanız gerekmektedir.

3. **Bireysel Sorumluluk:** Platform tarafından sunulan bilgileri kullanma kararı tamamen kullanıcıya aittir. Platform ve geliştiricileri, bu bilgilerin kullanımından doğabilecek herhangi bir sağlık sonucundan sorumlu tutulamaz.

4. **Bilgi Güncelliği:** Sunulan beslenme ve takviye bilgileri mevcut literatüre dayanmakla birlikte, tıp bilimi sürekli gelişmekte olup bu bilgiler zamanla değişebilir.

5. **Acil Durum:** Herhangi bir sağlık acilinde lütfen 112'yi arayın veya en yakın sağlık kuruluşuna başvurun.

6. **Yaş Sınırı:** Bu platform 18 yaş ve üzeri bireyler için tasarlanmıştır.

Bu şartları kabul ederek, platformun sunduğu bilgilerin tıbbi tavsiye olmadığını ve tüm sağlık kararlarınız için bir sağlık uzmanına danışacağınızı beyan etmiş olursunuz.
"""

# ── YASAL UYARI (analiz sonrası) ─────────────────────────────────────────────
YASAL_UYARI_HTML = """
<div style="
    background: linear-gradient(135deg, rgba(248,81,73,.06), rgba(248,81,73,.03));
    border: 1px solid rgba(248,81,73,.25);
    border-radius: 12px;
    padding: 18px 20px;
    margin-top: 1.5rem;
    line-height: 1.7;
">
    <div style="font-size:14px;font-weight:600;color:#f85149;margin-bottom:8px">
        ⚠️ Yasal Uyarı ve Sorumluluk Reddi
    </div>
    <div style="font-size:13px;color:#7d8590">
        Bu analiz yalnızca <strong style="color:#e6edf3">genel bilgilendirme</strong> amaçlıdır ve 
        <strong style="color:#e6edf3">tıbbi tavsiye, teşhis veya tedavi</strong> niteliği taşımamaktadır. 
        Sunulan bilgiler mevcut beslenme ve takviye literatürüne dayanmakta olup bireysel sağlık 
        durumunuza göre farklılık gösterebilir.<br><br>
        Herhangi bir takviye kullanmaya başlamadan önce, özellikle ilaç kullanıyorsanız veya 
        kronik bir hastalığınız varsa, mutlaka <strong style="color:#e6edf3">hekim veya eczacınıza</strong> danışınız.<br><br>
        <span style="font-size:12px">
        📞 Sağlık Bakanlığı ALO 182 | 🚨 Acil: 112
        </span>
    </div>
</div>
"""

# ── RİSK FİLTRESİ ────────────────────────────────────────────────────────────
def risk_analizi(form_data: dict) -> dict:
    """
    Form verilerini tarayarak risk seviyesini belirler.
    
    Returns:
        {
            "seviye": "yok" | "orta" | "yuksek",
            "mesajlar": [...],
            "devam_edilebilir": True | False
        }
    """
    mesajlar = []
    seviye = "yok"

    kronik = (form_data.get("kronik") or "").lower()
    notlar = (form_data.get("notlar") or "").lower()
    yas    = form_data.get("yas", 0)
    tarama_metni = kronik + " " + notlar

    # Yaş kontrolü
    try:
        if int(yas) < 18:
            return {
                "seviye": "yuksek",
                "mesajlar": ["Bu platform 18 yaş ve üzeri bireyler için tasarlanmıştır. Lütfen bir pediatrist veya aile hekimine başvurun."],
                "devam_edilebilir": False
            }
    except (ValueError, TypeError):
        pass

    # Yüksek risk taraması
    for anahtar, mesaj in YUKSEK_RISK_DURUMLAR.items():
        if anahtar in tarama_metni:
            mesajlar.append(mesaj)
            seviye = "yuksek"

    # Orta risk taraması (yüksek risk yoksa)
    if seviye != "yuksek":
        for anahtar, mesaj in ORTA_RISK_DURUMLAR.items():
            if anahtar in tarama_metni:
                mesajlar.append(mesaj)
                seviye = "orta"

    return {
        "seviye": seviye,
        "mesajlar": mesajlar,
        "devam_edilebilir": seviye != "yuksek"
    }


def risk_uyarisi_goster(risk: dict) -> bool:
    """
    Risk uyarısını ekranda gösterir.
    Returns: Kullanıcı devam etmek istiyor mu?
    """
    if risk["seviye"] == "yok":
        return True

    if risk["seviye"] == "yuksek":
        st.markdown("""
<div style="background:rgba(248,81,73,.1);border:1.5px solid #f85149;
            border-radius:12px;padding:20px 22px;margin-bottom:1rem">
    <div style="font-size:15px;font-weight:600;color:#f85149;margin-bottom:10px">
        🚨 Yüksek Risk Tespit Edildi
    </div>
""", unsafe_allow_html=True)
        for msg in risk["mesajlar"]:
            st.markdown(f"""
    <div style="font-size:13px;color:#e6edf3;margin-bottom:8px;
                padding:10px 14px;background:rgba(0,0,0,.3);border-radius:8px">
        ⚠️ {msg}
    </div>
""", unsafe_allow_html=True)
        st.markdown("""
    <div style="font-size:13px;color:#7d8590;margin-top:10px">
        Bu durumda genel takviye analizi yerine lütfen doğrudan bir sağlık uzmanına başvurun.
    </div>
</div>
""", unsafe_allow_html=True)
        st.error("Bu profil için otomatik analiz yapılamaz. Lütfen bir sağlık uzmanına başvurun.")
        return False

    # Orta risk
    st.markdown("""
<div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.4);
            border-radius:12px;padding:18px 20px;margin-bottom:1rem">
    <div style="font-size:14px;font-weight:600;color:#f5a623;margin-bottom:10px">
        ⚠️ Dikkat Gerektiren Durum Tespit Edildi
    </div>
""", unsafe_allow_html=True)
    for msg in risk["mesajlar"]:
        st.markdown(f"""
    <div style="font-size:13px;color:#e6edf3;margin-bottom:8px;
                padding:10px 14px;background:rgba(0,0,0,.2);border-radius:8px">
        • {msg}
    </div>
""", unsafe_allow_html=True)
    st.markdown("""
</div>
""", unsafe_allow_html=True)

    onay = st.checkbox(
        "Yukarıdaki uyarıları okudum ve anladım. Analizin yalnızca genel bilgi amaçlı olduğunu, "
        "sağlık kararlarım için hekimime danışacağımı kabul ediyorum.",
        key="risk_onay"
    )
    return onay


def kullanim_sartlari_goster() -> bool:
    """
    Kayıt formunda kullanım şartlarını gösterir.
    Returns: Kullanıcı kabul etti mi?
    """
    with st.expander("📋 Kullanım Şartları ve Sorumluluk Reddi (okumak için tıklayın)"):
        st.markdown(KULLANIM_SARTLARI)

    kabul = st.checkbox(
        "Kullanım şartlarını okudum, anladım ve kabul ediyorum. "
        "Bu platformun tıbbi tavsiye sunmadığını beyan ederim.",
        key="sartlar_kabul"
    )
    return kabul


def analiz_dil_uyarisi():
    """Analiz başlamadan önce kısa bilgi notu gösterir."""
    st.info(
        "ℹ️ Aşağıdaki analiz mevcut beslenme ve takviye literatürüne dayalı "
        "**genel bilgi** içermektedir. Tıbbi tavsiye, teşhis veya tedavi "
        "niteliği taşımamaktadır."
    )


def prompt_etik_eki() -> str:
    """Claude prompt'una eklenecek etik dil rehberi."""
    return """
## Önemli Dil ve Etik Kuralları

Yanıtında şu kurallara MUTLAKA uy:

1. **"Kullanın", "alın", "yapın" yerine** → "değerlendirilebilir", "literatürde önerilmektedir", "göz önünde bulundurulabilir", "araştırmaları desteklemektedir" gibi ifadeler kullan.

2. **Her takviye önerisinde** → "bir sağlık uzmanına danışarak" veya "hekim onayıyla" ifadesini ekle.

3. **Kronik hastalık veya ilaç kullanımı varsa** → ilgili takviyenin etkileşim riskini belirt ve mutlaka hekim onayı öner.

4. **Kesin sonuç vadetme** → "Bu takviye şikayetinizi kesinlikle giderir" gibi ifadeler kullanma. Bunun yerine "destekleyici olabilir", "katkı sağlayabilir" kullan.

5. **Analiz sonunda** → "Bu bilgiler genel amaçlıdır ve bireysel tıbbi tavsiye yerine geçmez. Lütfen bir sağlık uzmanına danışın." cümlesini ekle.

6. **Acil veya ciddi belirti varsa** → analizi bırak, direkt "lütfen bir hekime başvurun" de.
"""
