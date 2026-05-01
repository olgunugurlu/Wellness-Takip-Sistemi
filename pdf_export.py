"""
pdf_export.py — Wellness analiz raporunu PDF olarak üretir.
reportlab kullanır, Türkçe karakter desteği dahil.
"""
import io
import json
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── RENKLER ──────────────────────────────────────────────────────────────────
BRAND   = colors.HexColor('#2D5F3F')
ACCENT  = colors.HexColor('#D4A847')
DARK    = colors.HexColor('#1A1714')
GRAY    = colors.HexColor('#6B7280')
LGRAY   = colors.HexColor('#F3F4F6')
WHITE   = colors.white
RED     = colors.HexColor('#DC2626')
BLUE    = colors.HexColor('#1D4ED8')
GREEN   = colors.HexColor('#16A34A')


# ── STİLLER ──────────────────────────────────────────────────────────────────
def get_styles():
    base = getSampleStyleSheet()
    styles = {
        'title': ParagraphStyle('title', fontSize=22, textColor=BRAND,
                                fontName='Helvetica-Bold', spaceAfter=4,
                                alignment=TA_CENTER),
        'subtitle': ParagraphStyle('subtitle', fontSize=12, textColor=GRAY,
                                   fontName='Helvetica', spaceAfter=2,
                                   alignment=TA_CENTER),
        'h1': ParagraphStyle('h1', fontSize=14, textColor=WHITE,
                              fontName='Helvetica-Bold', spaceBefore=12,
                              spaceAfter=6, leftIndent=0,
                              backColor=BRAND, borderPad=6),
        'h2': ParagraphStyle('h2', fontSize=12, textColor=BRAND,
                              fontName='Helvetica-Bold', spaceBefore=10,
                              spaceAfter=4, borderPad=2),
        'body': ParagraphStyle('body', fontSize=10, textColor=DARK,
                               fontName='Helvetica', spaceAfter=4,
                               leading=15),
        'bullet': ParagraphStyle('bullet', fontSize=10, textColor=DARK,
                                 fontName='Helvetica', spaceAfter=3,
                                 leftIndent=14, leading=14),
        'caption': ParagraphStyle('caption', fontSize=9, textColor=GRAY,
                                  fontName='Helvetica-Oblique', spaceAfter=2),
        'disclaimer': ParagraphStyle('disclaimer', fontSize=8, textColor=GRAY,
                                     fontName='Helvetica-Oblique',
                                     alignment=TA_CENTER, spaceAfter=2),
        'tag_high':   ParagraphStyle('th', fontSize=9, textColor=RED,
                                     fontName='Helvetica-Bold'),
        'tag_medium': ParagraphStyle('tm', fontSize=9, textColor=ACCENT,
                                     fontName='Helvetica-Bold'),
        'tag_low':    ParagraphStyle('tl', fontSize=9, textColor=GREEN,
                                     fontName='Helvetica-Bold'),
    }
    return styles


# ── METİN TEMİZLEME ──────────────────────────────────────────────────────────
def temizle(metin: str) -> str:
    """Markdown sembollerini ve JSON bloklarını temizler."""
    if not metin:
        return ""
    metin = re.sub(r'```json.*?```', '', metin, flags=re.DOTALL)
    metin = re.sub(r'```.*?```', '', metin, flags=re.DOTALL)
    metin = re.sub(r'## BÖLÜM 2.*', '', metin, flags=re.DOTALL)
    metin = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', metin)
    metin = re.sub(r'\*(.+?)\*', r'<i>\1</i>', metin)
    # Emoji temizle (reportlab desteklemiyor)
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u017F\u00A0-\u00FF]', '', metin)
    return metin.strip()


def metin_to_paragraflar(metin: str, styles: dict) -> list:
    """Markdown metnini reportlab Paragraph listesine dönüştürür."""
    elems = []
    satirlar = metin.split('\n')
    i = 0
    while i < len(satirlar):
        satir = satirlar[i].strip()
        if not satir:
            i += 1
            continue

        if satir.startswith('## '):
            baslik = temizle(satir[3:])
            elems.append(Spacer(1, 0.3*cm))
            elems.append(Paragraph(f' {baslik}', styles['h1']))

        elif satir.startswith('### '):
            baslik = temizle(satir[4:])
            elems.append(Paragraph(baslik, styles['h2']))

        elif satir.startswith('# '):
            baslik = temizle(satir[2:])
            elems.append(Paragraph(baslik, styles['h2']))

        elif satir.startswith('- ') or satir.startswith('* '):
            icerik = temizle(satir[2:])
            if icerik:
                elems.append(Paragraph(f'• {icerik}', styles['bullet']))

        elif re.match(r'^\d+\.', satir):
            icerik = temizle(re.sub(r'^\d+\.\s*', '', satir))
            if icerik:
                num = re.match(r'^(\d+)\.', satir).group(1)
                elems.append(Paragraph(f'{num}. {icerik}', styles['bullet']))

        elif satir.startswith('---'):
            elems.append(HRFlowable(width='100%', thickness=0.5,
                                    color=LGRAY, spaceAfter=4))

        else:
            icerik = temizle(satir)
            if icerik:
                elems.append(Paragraph(icerik, styles['body']))

        i += 1
    return elems


# ── TAKVİYE TABLOSU ──────────────────────────────────────────────────────────
def supplement_tablosu(supplements: list, styles: dict) -> list:
    elems = []
    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph(' Supplement Plani', styles['h1']))
    elems.append(Paragraph('Once yasam tarzi, supplement en son. Maksimum etkili minimum doz.',
                            styles['caption']))
    elems.append(Spacer(1, 0.2*cm))

    oncelik_map = {'high': 'Yuksek', 'medium': 'Orta', 'low': 'Dusuk'}
    oncelik_renk = {'high': RED, 'medium': ACCENT, 'low': GREEN}

    header = [
        Paragraph('<b>Takviye</b>', ParagraphStyle('th', fontSize=10,
                  fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph('<b>Neden</b>', ParagraphStyle('th', fontSize=10,
                  fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph('<b>Doz</b>', ParagraphStyle('th', fontSize=10,
                  fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph('<b>Zaman</b>', ParagraphStyle('th', fontSize=10,
                  fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph('<b>Oncelik</b>', ParagraphStyle('th', fontSize=10,
                  fontName='Helvetica-Bold', textColor=WHITE)),
    ]
    rows = [header]

    for s in supplements:
        priority = s.get('priority', 'low')
        renk = oncelik_renk.get(priority, GREEN)
        label = oncelik_map.get(priority, priority)
        rows.append([
            Paragraph(s.get('name', ''), styles['body']),
            Paragraph(s.get('reason', ''), styles['body']),
            Paragraph(s.get('dosage', ''), styles['body']),
            Paragraph(s.get('timing', '').capitalize(), styles['body']),
            Paragraph(f'<b>{label}</b>',
                      ParagraphStyle('p', fontSize=9, fontName='Helvetica-Bold',
                                     textColor=renk)),
        ])

    col_w = [3.5*cm, 6*cm, 2.5*cm, 2.5*cm, 2*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), BRAND),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LGRAY]),
        ('GRID',        (0,0), (-1,-1), 0.3, colors.HexColor('#E5E7EB')),
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING',(0,0), (-1,-1), 6),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
    ]))
    elems.append(t)
    return elems


# ── EGZERSİZ PLANI TABLOSU ───────────────────────────────────────────────────
def egzersiz_tablosu(exercise: dict, styles: dict) -> list:
    elems = []
    weekly = exercise.get('weekly_plan', {})
    level  = exercise.get('level', '')
    if not weekly:
        return elems

    level_map = {'beginner': 'Baslangic', 'intermediate': 'Orta', 'advanced': 'Ileri'}
    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph(f' Haftalik Egzersiz Plani — {level_map.get(level, level)}',
                            styles['h1']))
    elems.append(Spacer(1, 0.2*cm))

    header = [
        Paragraph('<b>Gun</b>', ParagraphStyle('th', fontSize=10,
                  fontName='Helvetica-Bold', textColor=WHITE)),
        Paragraph('<b>Antrenman</b>', ParagraphStyle('th', fontSize=10,
                  fontName='Helvetica-Bold', textColor=WHITE)),
    ]
    rows = [header]
    for gun, aktivite in weekly.items():
        dinlenme = 'dinlenme' in aktivite.lower()
        bg = colors.HexColor('#F9FAFB') if dinlenme else WHITE
        rows.append([
            Paragraph(gun, styles['body']),
            Paragraph(aktivite, styles['body']),
        ])

    t = Table(rows, colWidths=[3.5*cm, 13*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,0), BRAND),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LGRAY]),
        ('GRID',         (0,0), (-1,-1), 0.3, colors.HexColor('#E5E7EB')),
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING',   (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
    ]))
    elems.append(t)
    return elems


# ── ANA PDF OLUŞTURMA FONKSİYONU ─────────────────────────────────────────────
def analiz_pdf_olustur(
    analiz_metni: str,
    analiz_json_str: str | None,
    kullanici_adi: str = "Kullanici",
    tarih: str | None = None
) -> bytes:
    """
    Analiz metni ve JSON'dan PDF oluşturur, bytes olarak döner.
    Streamlit'te st.download_button ile kullanım için tasarlandı.
    """
    buffer = io.BytesIO()
    tarih = tarih or datetime.now().strftime('%d.%m.%Y')

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        leftMargin=1.8*cm,
        rightMargin=1.8*cm,
        title=f'Wellness Analizi — {kullanici_adi}',
        author='Wellness Analiz Sistemi',
    )

    styles = get_styles()
    story  = []

    # ── KAPAK ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('WELLNESS ANALIZ RAPORU', styles['title']))
    story.append(Paragraph(kullanici_adi, styles['subtitle']))
    story.append(Paragraph(tarih, styles['caption']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT,
                            spaceBefore=6, spaceAfter=10))

    # ── ANALİZ METNİ ─────────────────────────────────────────────────────────
    if analiz_metni:
        story += metin_to_paragraflar(analiz_metni, styles)

    # ── JSON BÖLÜMÜ ───────────────────────────────────────────────────────────
    if analiz_json_str:
        try:
            data = json.loads(analiz_json_str)
            # Normalize et
            supplements = data.get('supplements', data.get('takviyeler', []))
            if supplements and 'isim' in (supplements[0] if supplements else {}):
                # Eski format dönüştür
                oncelik_map = {1: 'high', 2: 'medium', 3: 'low'}
                supplements = [{
                    'name': s.get('isim', ''),
                    'reason': s.get('neden', ''),
                    'dosage': s.get('doz', ''),
                    'timing': s.get('zaman', ''),
                    'priority': oncelik_map.get(int(s.get('oncelik', 2)), 'medium'),
                } for s in supplements]

            exercise = data.get('exercise_plan', {})
            priorities = data.get('priorities', [])
            risk_notes = data.get('risk_notes', '')

            # Öncelikler
            if priorities:
                story.append(Spacer(1, 0.3*cm))
                story.append(Paragraph(' Oncelik Alanlari', styles['h1']))
                for i, p in enumerate(priorities, 1):
                    story.append(Paragraph(f'{i}. {p}', styles['bullet']))

            # Supplement tablosu
            if supplements:
                story += supplement_tablosu(supplements, styles)

            # Egzersiz tablosu
            if exercise:
                story += egzersiz_tablosu(exercise, styles)

            # Risk notu
            if risk_notes:
                story.append(Spacer(1, 0.4*cm))
                story.append(Paragraph(' Risk Uyarilari', styles['h1']))
                story.append(Paragraph(risk_notes, styles['body']))

        except Exception:
            pass

    # ── DISCLAIMER ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGRAY,
                            spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        'Bu rapor yalnizca bilgilendirme amaclidir ve tibbi tavsiye niteliginde degildir. '
        'Herhangi bir takviye kullanmadan once bir saglik uzmanina danisiniz. | '
        'Wellness Analiz Sistemi | ' + tarih,
        styles['disclaimer']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
