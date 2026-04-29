import anthropic
import streamlit as st
import json
import re
from ethics import prompt_etik_eki


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
    "sabah": "🌅",
    "öğle": "☀️",
    "akşam": "🌆",
    "gece": "🌙",
    "antrenman": "💪"
}


def build_prompt(data: dict) -> str:
    top5 = sorted(
        data.get("goaller", {}).items(),
        key=lambda x: -int(x[1])
    )[:5]
    top5_str = ", ".join([f"{k} ({v}/5)" for k, v in top5])
    symp = data.get("semptomlar", [])
    takv = data.get("takviyeler", {})
    lab  = data.get("lab", {})

    return f"""Sen deneyimli bir fonksiyonel tıp ve nutrisyon uzmanısın. Aşağıdaki kişisel verileri inceleyerek kapsamlı, kişiye özel bir wellness ve takviye planı oluştur.

## Kişi Profili
İsim: {data.get('isim','—')} | Yaş: {data.get('yas','—')} | Cinsiyet: {data.get('cinsiyet','—')}
Boy: {data.get('boy','—')} cm | Kilo: {data.get('kilo','—')} kg | Bel: {data.get('bel','—')} cm
Aktivite: {data.get('meslek','—')} | Egzersiz: {data.get('egzersiz','—')} ({data.get('egztur','—')})
Uyku: {data.get('uyku','—')} | Kronik/İlaç: {data.get('kronik','Yok')}

## Öncelikli Hedefler
{top5_str}

## Semptomlar
{', '.join(symp) if symp else 'Belirtilen semptom yok'}

## Beslenme
Diyet: {data.get('diet','—')} | Öğün: {data.get('ogun','—')} | Su: {data.get('su','—')} L/gün
Balık: {data.get('balik','—')} | Protein: {data.get('protein','—')} | Sebze-meyve: {data.get('sebze','—')} porsiyon
Şeker/işlenmiş: {data.get('seker','—')} | Fermente: {data.get('fermente','—')}
Kahve: {data.get('kahve','—')}/gün | Alkol: {data.get('alkol','—')} | Alerji: {data.get('alerji','Yok')}

## Mevcut Takviyeler
{', '.join([f"{k}: {v}" for k,v in takv.items()]) if takv else 'Yok'}

## Laboratuvar Değerleri
{', '.join([f"{k}: {v}" for k,v in lab.items()]) if lab else 'Girilmedi'}

## Ek Notlar
{data.get('notlar','—')}

---
Türkçe, profesyonel analiz hazırla. YANIT İKİ BÖLÜMDEN OLUŞMALI:

## BÖLÜM 1: ANALİZ METNİ

### 1. Genel Değerlendirme
Profil özeti, güçlü yönler, dikkat gerektiren alanlar.

### 2. Beslenme Önerileri
Hedefe ve profile göre 5-7 somut, uygulanabilir tavsiye.

### 3. Takviye Planı (Özet)
Her takviye için tek satır özet.

### 4. Yaşam Tarzı Önerileri
Uyku, stres, egzersiz optimizasyonu için 3-4 öneri.

### 5. 3 Aylık Yol Haritası
1. ay — temel, 2. ay — derinleştirme, 3. ay — optimizasyon.

### 6. Dikkat Edilmesi Gerekenler
Profile özgü riskler, kaçınılması gerekenler, önerilen lab testleri.

---

## BÖLÜM 2: TAKVİYE KARTLARI (JSON)

Analiz metninin HEMEN ARKASINA bu JSON bloğunu ekle. Başka açıklama ekleme.

```json
{{
  "takviyeler": [
    {{
      "isim": "Magnezyum Bisglisinat",
      "emoji": "💊",
      "neden": "Kısa gerekçe 1-2 cümle",
      "doz": "400mg",
      "zaman": "gece",
      "marka_onerisi": "Now Foods / Solaray",
      "sure": "Sürekli kullanım",
      "oncelik": 1
    }}
  ],
  "gunluk_program": [
    {{"zaman": "sabah", "takviyeler": ["D3+K2", "Omega-3"]}},
    {{"zaman": "öğle",  "takviyeler": ["Kolajen"]}},
    {{"zaman": "akşam", "takviyeler": ["Çinko", "Omega-3"]}},
    {{"zaman": "gece",  "takviyeler": ["Magnezyum"]}}
  ],
  "lab_onerileri": ["Vitamin D", "Testosteron", "CRP"],
  "uyari": "Kısa önemli uyarı cümlesi."
}}
```"""


def parse_response(full_text: str) -> tuple:
    """Analiz metnini ve JSON takviye kartlarını ayırır."""
    json_match = re.search(r'```json\s*(.*?)\s*```', full_text, re.DOTALL)
    if json_match:
        analiz_metni = full_text[:json_match.start()].strip()
        try:
            takviye_data = json.loads(json_match.group(1))
            return analiz_metni, takviye_data
        except json.JSONDecodeError:
            return full_text, None
    return full_text, None


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


def render_supplement_cards(takviye_data: dict):
    """Takviye kartlarını Streamlit ile görsel olarak gösterir."""

    takviyeler = takviye_data.get("takviyeler", [])
    gunluk     = takviye_data.get("gunluk_program", [])
    lab_oner   = takviye_data.get("lab_onerileri", [])
    uyari      = takviye_data.get("uyari", "")

    # ── TAKVİYE KARTLARI ─────────────────────────────────────────────────
    st.markdown("## 💊 Kişisel Takviye Planı")
    takviyeler_sorted = sorted(takviyeler, key=lambda x: x.get("oncelik", 99))

    cols = st.columns(2)
    for i, t in enumerate(takviyeler_sorted):
        with cols[i % 2]:
            zaman_emoji = ZAMAN_EMOJIS.get(t.get("zaman", "").lower(), "⏰")
            st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-left:4px solid #d4a847;
            border-radius:12px;padding:16px 18px;margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
    <div>
      <span style="font-size:20px">{t.get('emoji','💊')}</span>
      <strong style="font-size:15px;color:#e6edf3;margin-left:8px">{t.get('isim','')}</strong>
    </div>
    <span style="background:#d4a84720;color:#d4a847;font-size:11px;font-weight:600;
                 padding:3px 10px;border-radius:20px">#{t.get('oncelik','')}</span>
  </div>
  <p style="color:#7d8590;font-size:13px;line-height:1.55;margin:0 0 12px">{t.get('neden','')}</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
    <div style="background:#0d1117;border-radius:8px;padding:8px 10px">
      <div style="font-size:10px;color:#7d8590;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Doz</div>
      <div style="font-size:13px;font-weight:600;color:#e6edf3">{t.get('doz','—')}</div>
    </div>
    <div style="background:#0d1117;border-radius:8px;padding:8px 10px">
      <div style="font-size:10px;color:#7d8590;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Zaman</div>
      <div style="font-size:13px;font-weight:600;color:#e6edf3">{zaman_emoji} {t.get('zaman','—').capitalize()}</div>
    </div>
    <div style="background:#0d1117;border-radius:8px;padding:8px 10px">
      <div style="font-size:10px;color:#7d8590;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Marka</div>
      <div style="font-size:13px;color:#58a6ff">{t.get('marka_onerisi','—')}</div>
    </div>
    <div style="background:#0d1117;border-radius:8px;padding:8px 10px">
      <div style="font-size:10px;color:#7d8590;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px">Süre</div>
      <div style="font-size:13px;color:#3fb950">{t.get('sure','—')}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── GÜNLÜK PROGRAM ────────────────────────────────────────────────────
    if gunluk:
        st.markdown("## 🗓️ Günlük Takviye Programı")
        prog_cols = st.columns(len(gunluk))
        for i, blok in enumerate(gunluk):
            zaman = blok.get("zaman", "")
            emoji = ZAMAN_EMOJIS.get(zaman.lower(), "⏰")
            items = blok.get("takviyeler", [])
            with prog_cols[i]:
                items_html = "".join([
                    f'<div style="background:#0d1117;border-radius:6px;padding:6px 10px;'
                    f'margin-bottom:5px;font-size:12px;color:#e6edf3">{item}</div>'
                    for item in items
                ])
                st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
            padding:16px;text-align:center;height:100%">
  <div style="font-size:24px;margin-bottom:4px">{emoji}</div>
  <div style="font-size:11px;font-weight:600;text-transform:uppercase;
              letter-spacing:1px;color:#d4a847;margin-bottom:12px">{zaman.capitalize()}</div>
  {items_html}
</div>
""", unsafe_allow_html=True)

    # ── LAB ÖNERİLERİ ─────────────────────────────────────────────────────
    if lab_oner:
        st.markdown("## 🔬 Önerilen Laboratuvar Testleri")
        lab_html = "".join([
            f'<span style="background:#1c2333;border:1px solid #30363d;border-radius:20px;'
            f'padding:5px 14px;margin:4px;display:inline-block;font-size:13px;color:#58a6ff">'
            f'🧪 {l}</span>'
            for l in lab_oner
        ])
        st.markdown(f'<div style="line-height:2.8">{lab_html}</div>', unsafe_allow_html=True)

    # ── UYARI ─────────────────────────────────────────────────────────────
    if uyari:
        st.markdown(f"""
<div style="background:rgba(248,81,73,.06);border:1px solid rgba(248,81,73,.2);
            border-radius:10px;padding:14px 18px;font-size:13px;
            color:#7d8590;margin-top:1rem;line-height:1.6">
⚠️ <strong style="color:#f85149">Önemli Not:</strong> {uyari}
</div>
""", unsafe_allow_html=True)
