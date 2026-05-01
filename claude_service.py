import anthropic
import streamlit as st
import json
import re

GOALS = [
    "Enerji & vitalite", "Uyku kalitesi", "Stres yönetimi",
    "Kas & güç", "Eklem sağlığı", "Karaciğer & detoks",
    "Sağlıklı yaşlanma", "Odak & bilişsel performans",
    "Bağırsak & sindirim", "Kilo yönetimi",
    "Hormonal denge", "Bağışıklık"
]

SYMPTOMS = [
    "Kronik yorgunluk", "Uyku bölünmesi", "Beyin sisi",
    "Eklem / sabah tutukluğu", "Bel / boyun ağrısı", "Sindirim şikayeti",
    "Ruh hali dalgalanması", "Kilo vermede zorluk",
    "Saç dökülmesi", "Cilt sorunları", "Uyuşma / çarpıntı", "Sık hastalanma"
]

SUPPS = [
    "Magnezyum", "D Vitamini", "Omega-3", "Kreatin", "Kolajen",
    "Probiyotik", "B12 / B Kompleks", "Çinko", "Ashwagandha",
    "C Vitamini", "CoQ10", "Demir", "Melatonin", "Diğer"
]

LABS = [
    "Vitamin D (ng/mL)", "B12 (pg/mL)", "Ferritin (ng/mL)",
    "HbA1c (%)", "ALT / AST (U/L)", "Lipid — LDL/HDL",
    "TSH (μIU/mL)", "CRP (mg/L)", "Homosistein", "Testosteron / Östrojen"
]

ZAMAN_EMOJIS = {
    "sabah": "🌅", "öğle": "☀️", "akşam": "🌆",
    "gece": "🌙", "antrenman": "💪"
}

ONCELIK_RENK = {
    "high":   ("#f85149", "rgba(248,81,73,.12)"),
    "medium": ("#d4a847", "rgba(212,168,71,.12)"),
    "low":    ("#3fb950", "rgba(63,185,80,.12)"),
}


# ── SISTEM PROMPTU ────────────────────────────────────────────────────────────
SISTEM_PROMPTU = """Sen, yapay zekâ destekli kişiselleştirilmiş sağlık, performans ve yaşam tarzı optimizasyon sistemi içinde çalışan ileri seviye bir analiz motorusun.

Rolün: Deneyimli bir fonksiyonel tıp uzmanı, performans koçu, beslenme danışmanı ve egzersiz planlayıcısı gibi davranmak; ancak asla tıbbi teşhis koymamak ve doktor yerine geçmemektir.

TEMEL KURALLAR:
- Tıbbi teşhis koyma
- Hastalık ismi üzerinden kesin yargı verme
- İlaç önerme
- Abartılı veya gereksiz supplement önerme
- Önce yaşam tarzını optimize et, supplement en son gelir
- Minimalist yaklaşım kullan (minimum etkili doz)
- Bilimsel, sade ve uygulanabilir öneriler ver
- Riskli durumlarda kullanıcıyı doktora yönlendir

SİSTEM AMACI: Kullanıcının verdiği verileri analiz ederek:
- sağlık risklerini belirlemek
- yaşam kalitesini artırmak
- sürdürülebilir alışkanlıklar oluşturmak
- gereksiz karmaşıklığı ortadan kaldırmak

SUPPLEMENT KURALI: Sadece gerçekten gerekli olanları öner. Maksimum 3-5 supplement.

SON KURAL: Amaç mükemmel plan değil, sürdürülebilir plan üretmektir."""


def build_prompt(data: dict) -> str:
    top5 = sorted(
        data.get("goaller", {}).items(),
        key=lambda x: -int(x[1])
    )[:5]
    top5_str = ", ".join([f"{k} ({v}/5)" for k, v in top5])
    symp = data.get("semptomlar", [])
    takv = data.get("takviyeler", {})
    lab  = data.get("lab", {})

    # BKI hesapla
    bki_str = "—"
    try:
        boy  = float(data.get("boy", 0))
        kilo = float(data.get("kilo", 0))
        if boy and kilo:
            bki = round(kilo / ((boy / 100) ** 2), 1)
            bki_str = f"{bki}"
    except Exception:
        pass

    kullanici_json = json.dumps({
        "demografik": {
            "isim":     data.get("isim", "—"),
            "yas":      data.get("yas", "—"),
            "cinsiyet": data.get("cinsiyet", "—"),
            "boy_cm":   data.get("boy", "—"),
            "kilo_kg":  data.get("kilo", "—"),
            "bki":      bki_str,
            "bel_cm":   data.get("bel", "—"),
        },
        "yasam_tarzi": {
            "meslek_aktivite": data.get("meslek", "—"),
            "haftalik_egzersiz": data.get("egzersiz", "—"),
            "egzersiz_turu":   data.get("egztur", "—"),
            "uyku_suresi":     data.get("uyku", "—"),
            "kronik_hastalik_ilac": data.get("kronik", "Yok"),
        },
        "beslenme": {
            "diyet_tipi":    data.get("diet", "—"),
            "ogun_sayisi":   data.get("ogun", "—"),
            "su_litre":      data.get("su", "—"),
            "kahve_fincan":  data.get("kahve", "—"),
            "balik_haftalik": data.get("balik", "—"),
            "alkol":         data.get("alkol", "—"),
            "protein_yeterliligi": data.get("protein", "—"),
            "sebze_meyve_porsiyon": data.get("sebze", "—"),
            "seker_islenmis": data.get("seker", "—"),
            "fermente_gida": data.get("fermente", "—"),
            "alerji_intolerans": data.get("alerji", "Yok"),
        },
        "semptomlar": symp if symp else ["Belirtilen semptom yok"],
        "hedefler": {k: f"{v}/5" for k, v in top5},
        "mevcut_takviyeler": takv if takv else {},
        "laboratuvar": lab if lab else {},
        "ek_notlar": data.get("notlar", "—"),
    }, ensure_ascii=False, indent=2)

    return f"""{SISTEM_PROMPTU}

---

## KULLANICI VERİLERİ (JSON)

{kullanici_json}

---

## ANALİZ TALİMATLARI

Yukarıdaki verileri analiz ederek YALNIZCA aşağıdaki iki bölümü üret:

---

## BÖLÜM 1 — ANALİZ METNİ

Markdown formatında, şu başlıkları kullan:

## Genel Durum
Kısa, net profil özeti. Güçlü yönler ve dikkat gerektiren alanlar.

## Öncelikler
En kritik 3-5 geliştirilmesi gereken alan (uyku, beslenme, stres, hareket, metabolik risk).

## Beslenme Analizi
Protein yeterliliği, lif alımı, işlenmiş gıda, su tüketimi. Basit ve uygulanabilir öneriler.

## Egzersiz Planı
Kullanıcının seviyesine göre haftalık plan. Kardiyo + kuvvet + mobilite dengesi. Süre: 20-40 dk. Haftada 3-4 gün.

## Uyku Optimizasyonu
Uyku süresi, kalite, ekran kullanımı, rutin önerileri.

## Stres ve Zihinsel Durum
Stres kaynakları, mental yorgunluk, basit teknikler.

## Supplement Planı
Sadece gerçekten gerekli olanlar (maks 3-5). Her biri için: neden, doz, ne zaman.

## Risk Uyarıları
Ciddi belirti veya kronik hastalık varsa: "Bu konuda bir sağlık profesyoneline danışmanız önerilir."

## 3 Aylık Gelişim Stratejisi
- İlk 2 hafta (kısa vadeli)
- 1. ay (orta vadeli)
- 3. ay (uzun vadeli)

## Günlük Rutin
Sabah / Öğle / Akşam / Gece şeklinde basit rutin.

---

## BÖLÜM 2 — JSON

Analiz metninin HEMEN arkasına, başka açıklama eklemeden şu JSON bloğunu yaz:

```json
{{
  "supplements": [
    {{
      "name": "Takviye Adı",
      "reason": "Kısa gerekçe (1 cümle)",
      "dosage": "Doz miktarı",
      "timing": "sabah/öğle/akşam/gece",
      "priority": "high/medium/low"
    }}
  ],
  "exercise_plan": {{
    "level": "beginner/intermediate/advanced",
    "weekly_plan": {{
      "Pazartesi": "Aktivite açıklaması",
      "Salı": "Aktivite açıklaması",
      "Çarşamba": "Dinlenme veya mobilite",
      "Perşembe": "Aktivite açıklaması",
      "Cuma": "Aktivite açıklaması",
      "Cumartesi": "Hafif aktivite",
      "Pazar": "Tam dinlenme"
    }}
  }},
  "priorities": ["Öncelik 1", "Öncelik 2", "Öncelik 3"],
  "risk_level": "low/medium/high",
  "risk_notes": "Risk varsa açıklama, yoksa boş string"
}}
```"""


def parse_response(full_text: str) -> tuple:
    """Analiz metnini ve JSON verisini ayırır.
    Farklı Claude çıktı formatlarını destekler."""

    # 1. Standart ```json ... ``` bloğu
    json_match = re.search(r'```json\s*(.*?)\s*```', full_text, re.DOTALL)
    if json_match:
        analiz_metni = full_text[:json_match.start()].strip()
        analiz_metni = re.sub(r'##\s*BÖLÜM 2.*$', '', analiz_metni, flags=re.MULTILINE | re.DOTALL).strip()
        analiz_metni = re.sub(r'---\s*$', '', analiz_metni, flags=re.MULTILINE).strip()
        try:
            structured = json.loads(json_match.group(1))
            return analiz_metni, structured
        except json.JSONDecodeError:
            pass

    # 2. ``` ... ``` (json etiketi olmadan)
    json_match2 = re.search(r'```\s*(\{.*?\})\s*```', full_text, re.DOTALL)
    if json_match2:
        analiz_metni = full_text[:json_match2.start()].strip()
        analiz_metni = re.sub(r'##\s*BÖLÜM 2.*$', '', analiz_metni, flags=re.MULTILINE | re.DOTALL).strip()
        try:
            structured = json.loads(json_match2.group(1))
            return analiz_metni, structured
        except json.JSONDecodeError:
            pass

    # 3. BÖLÜM 2 başlığından sonra JSON ara
    bolum2 = re.search(r'##\s*BÖLÜM 2.*?$(.*)', full_text, re.DOTALL | re.MULTILINE)
    if bolum2:
        icerik = bolum2.group(1).strip()
        analiz_metni = full_text[:bolum2.start()].strip()
        obj_match = re.search(r'(\{.*\})', icerik, re.DOTALL)
        if obj_match:
            try:
                structured = json.loads(obj_match.group(1))
                return analiz_metni, structured
            except json.JSONDecodeError:
                pass

    # 4. Temizle ve döndür
    temiz = re.sub(r'##\s*BÖLÜM 2.*', '', full_text, flags=re.DOTALL).strip()
    temiz = re.sub(r'```json.*?```', '', temiz, flags=re.DOTALL).strip()
    return temiz, None


def stream_analysis(data: dict):
    """Claude API'ye istek atar, streaming ile yanıt döner."""
    client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
    with client.messages.stream(
        model="claude-opus-4-5",
        max_tokens=6000,
        messages=[{"role": "user", "content": build_prompt(data)}]
    ) as stream:
        for text in stream.text_stream:
            yield text


def render_supplement_cards(structured: dict):
    """Yeni JSON yapısına göre takviye kartları, egzersiz planı ve öncelikleri render eder."""

    supplements  = structured.get("supplements", [])
    exercise     = structured.get("exercise_plan", {})
    priorities   = structured.get("priorities", [])
    risk_level   = structured.get("risk_level", "low")
    risk_notes   = structured.get("risk_notes", "")

    # ── ÖNCELİKLER ───────────────────────────────────────────────────────────
    if priorities:
        st.markdown("## 🎯 Öncelikli Gelişim Alanları")
        cols = st.columns(len(priorities))
        for i, p in enumerate(priorities):
            with cols[i]:
                st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
            padding:14px 16px;text-align:center">
  <div style="font-size:24px;margin-bottom:6px">{['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣'][i] if i < 5 else '🔹'}</div>
  <div style="font-size:13px;font-weight:600;color:#e6edf3">{p}</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── TAKVİYE KARTLARI ─────────────────────────────────────────────────────
    if supplements:
        st.markdown("## 💊 Supplement Planı")
        st.caption("Önce yaşam tarzı, supplement en son. Maksimum etkili minimum doz.")

        # Önceliğe göre sırala
        oncelik_sira = {"high": 0, "medium": 1, "low": 2}
        supps_sorted = sorted(supplements, key=lambda x: oncelik_sira.get(x.get("priority","low"), 2))

        cols = st.columns(2)
        for i, s in enumerate(supps_sorted):
            with cols[i % 2]:
                priority = s.get("priority", "low")
                renk, bg  = ONCELIK_RENK.get(priority, ONCELIK_RENK["low"])
                oncelik_label = {"high": "Yüksek Öncelik", "medium": "Orta Öncelik", "low": "Düşük Öncelik"}.get(priority, "")
                zaman = s.get("timing", "").lower()
                zaman_emoji = ZAMAN_EMOJIS.get(zaman, "⏰")

                st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-left:4px solid {renk};
            border-radius:12px;padding:16px 18px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
    <strong style="font-size:15px;color:#e6edf3">💊 {s.get('name','')}</strong>
    <span style="background:{bg};color:{renk};font-size:11px;font-weight:600;
                 padding:3px 10px;border-radius:20px">{oncelik_label}</span>
  </div>
  <p style="color:#7d8590;font-size:13px;line-height:1.55;margin:0 0 12px">{s.get('reason','')}</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
    <div style="background:#0d1117;border-radius:8px;padding:8px 10px">
      <div style="font-size:10px;color:#7d8590;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Doz</div>
      <div style="font-size:13px;font-weight:600;color:#e6edf3">{s.get('dosage','—')}</div>
    </div>
    <div style="background:#0d1117;border-radius:8px;padding:8px 10px">
      <div style="font-size:10px;color:#7d8590;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Ne Zaman</div>
      <div style="font-size:13px;font-weight:600;color:#e6edf3">{zaman_emoji} {zaman.capitalize()}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── EGZERSİZ PLANI ────────────────────────────────────────────────────────
    weekly = exercise.get("weekly_plan", {})
    level  = exercise.get("level", "")
    if weekly:
        level_label = {"beginner": "🟢 Başlangıç", "intermediate": "🟡 Orta", "advanced": "🔴 İleri"}.get(level, level)
        st.markdown(f"## 🏃 Haftalık Egzersiz Planı  <small style='font-size:13px;color:#7d8590'>{level_label}</small>", unsafe_allow_html=True)

        gun_emojis = {"Pazartesi":"💪","Salı":"🧘","Çarşamba":"🚶","Perşembe":"💪","Cuma":"🔥","Cumartesi":"🌿","Pazar":"😴"}
        for gun, aktivite in weekly.items():
            emoji = gun_emojis.get(gun, "📅")
            dinlenme = "dinlenme" in aktivite.lower() or "rest" in aktivite.lower()
            bg = "#0d1117" if dinlenme else "#161b22"
            border_color = "#30363d" if dinlenme else "#3fb950"
            text_color = "#484f58" if dinlenme else "#e6edf3"
            st.markdown(f"""
<div style="background:{bg};border:1px solid {border_color};border-radius:10px;
            padding:10px 16px;margin-bottom:6px;display:flex;align-items:center;gap:12px">
  <span style="font-size:20px;flex-shrink:0">{emoji}</span>
  <div>
    <span style="font-size:12px;font-weight:600;color:#7d8590;text-transform:uppercase;
                 letter-spacing:.5px">{gun}</span>
    <div style="font-size:14px;color:{text_color};margin-top:2px">{aktivite}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── RİSK SEVİYESİ ─────────────────────────────────────────────────────────
    if risk_level in ("medium", "high") and risk_notes:
        renk = "#f85149" if risk_level == "high" else "#d4a847"
        bg   = "rgba(248,81,73,.06)" if risk_level == "high" else "rgba(212,168,71,.06)"
        border = "rgba(248,81,73,.25)" if risk_level == "high" else "rgba(212,168,71,.25)"
        icon = "🚨" if risk_level == "high" else "⚠️"
        st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:12px;
            padding:16px 20px;margin-top:1rem">
  <div style="font-size:14px;font-weight:600;color:{renk};margin-bottom:8px">{icon} Risk Uyarısı</div>
  <div style="font-size:13px;color:#7d8590;line-height:1.65">{risk_notes}</div>
</div>
""", unsafe_allow_html=True)