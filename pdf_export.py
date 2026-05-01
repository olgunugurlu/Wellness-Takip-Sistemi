"""
pdf_export.py — Wellness analiz raporunu PDF olarak üretir.
DejaVuSans fontu ile Türkçe karakter desteği.
"""
import io
import json
import re
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── FONT KAYIT ────────────────────────────────────────────────────────────────
def _register_fonts():
    """DejaVuSans fontunu kaydet — Türkçe karakter desteği için."""
    # Önce proje içindeki fonts/ klasörüne bak
    base = os.path.dirname(os.path.abspath(__file__))
    font_dir = os.path.join(base, 'fonts')

    candidates = {
        'DejaVuSans': [
            os.path.join(font_dir, 'DejaVuSans.ttf'),
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ],
        'DejaVuSans-Bold': [
            os.path.join(font_dir, 'DejaVuSans-Bold.ttf'),
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ],
        'DejaVuSans-Oblique': [
            os.path.join(font_dir, 'DejaVuSans-Oblique.ttf'),
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf',
        ],
    }

    registered = []
    for name, paths in candidates.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    registered.append(name)
                    break
                except Exception:
                    pass

    # Bold ve Italic mapping
    if 'DejaVuSans' in registered and 'DejaVuSans-Bold' in registered:
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        oblique = 'DejaVuSans-Oblique' if 'DejaVuSans-Oblique' in registered else 'DejaVuSans'
        registerFontFamily(
            'DejaVuSans',
            normal='DejaVuSans',
            bold='DejaVuSans-Bold',
            italic=oblique,
            boldItalic='DejaVuSans-Bold'
        )
        return 'DejaVuSans', 'DejaVuSans-Bold', oblique

    # Fallback
    return 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique'


FONT_NORMAL, FONT_BOLD, FONT_ITALIC = _register_fonts()

# ── RENKLER ──────────────────────────────────────────────────────────────────
BRAND  = colors.HexColor('#2D5F3F')
ACCENT = colors.HexColor('#D4A847')
DARK   = colors.HexColor('#1A1714')
GRAY   = colors.HexColor('#6B7280')
LGRAY  = colors.HexColor('#F3F4F6')
WHITE  = colors.white
RED    = colors.HexColor('#DC2626')
GREEN  = colors.HexColor('#16A34A')


# ── STİLLER ──────────────────────────────────────────────────────────────────
def get_styles():
    return {
        'title': ParagraphStyle('title', fontSize=20, textColor=BRAND,
                                fontName=FONT_BOLD, spaceAfter=4,
                                alignment=TA_CENTER),
        'subtitle': ParagraphStyle('subtitle', fontSize=12, textColor=GRAY,
                                   fontName=FONT_NORMAL, spaceAfter=2,
                                   alignment=TA_CENTER),
        'h1': ParagraphStyle('h1', fontSize=13, textColor=WHITE,
                              fontName=FONT_BOLD, spaceBefore=14,
                              spaceAfter=6, backColor=BRAND, borderPad=5),
        'h2': ParagraphStyle('h2', fontSize=11, textColor=BRAND,
                              fontName=FONT_BOLD, spaceBefore=10, spaceAfter=4),
        'body': ParagraphStyle('body', fontSize=10, textColor=DARK,
                               fontName=FONT_NORMAL, spaceAfter=4, leading=15),
        'bullet': ParagraphStyle('bullet', fontSize=10, textColor=DARK,
                                 fontName=FONT_NORMAL, spaceAfter=3,
                                 leftIndent=14, leading=14),
        'caption': ParagraphStyle('caption', fontSize=9, textColor=GRAY,
                                  fontName=FONT_ITALIC, spaceAfter=2),
        'disclaimer': ParagraphStyle('disclaimer', fontSize=8, textColor=GRAY,
                                     fontName=FONT_ITALIC,
                                     alignment=TA_CENTER, spaceAfter=2),
        'tbl_header': ParagraphStyle('tblh', fontSize=10, textColor=WHITE,
                                     fontName=FONT_BOLD),
        'tbl_body': ParagraphStyle('tblb', fontSize=9, textColor=DARK,
                                   fontName=FONT_NORMAL, leading=13),
        'high': ParagraphStyle('high', fontSize=9, textColor=RED,
                               fontName=FONT_BOLD),
        'medium': ParagraphStyle('med', fontSize=9, textColor=ACCENT,
                                 fontName=FONT_BOLD),
        'low': ParagraphStyle('low', fontSize=9, textColor=GREEN,
                              fontName=FONT_BOLD),
    }


# ── METİN TEMİZLEME ──────────────────────────────────────────────────────────
def temizle(metin: str) -> str:
    """JSON bloklarını ve markdown sembollerini temizler."""
    if not metin:
        return ""
    metin = re.sub(r'```json.*?```', '', metin, flags=re.DOTALL)
    metin = re.sub(r'```.*?```', '', metin, flags=re.DOTALL)
    metin = re.sub(r'## BÖLÜM 2.*', '', metin, flags=re.DOTALL)
    metin = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', metin)
    metin = re.sub(r'\*(.+?)\*', r'<i>\1</i>', metin)
    # Emoji ve desteklenmeyen karakterleri kaldır
    metin = re.sub(r'[^\x00-\xFF\u011E\u011F\u0130\u0131\u015E\u015F\u00C7\u00E7\u00D6\u00F6\u00DC\u00FC\u00C2\u00E2\u00CE\u00EE\u00DB\u00FB]', '', metin)
    return metin.strip()


def markdown_to_elems(metin: str, styles: dict) -> list:
    """Markdown analiz metnini reportlab flowable listesine çevirir."""
    elems = []
    for satir in metin.split('\n'):
        s = satir.strip()
        if not s:
            continue
        if s.startswith('## '):
            elems.append(Spacer(1, 0.2*cm))
            elems.append(Paragraph(f'  {temizle(s[3:])}', styles['h1']))
        elif s.startswith('### ') or s.startswith('# '):
            txt = s.lstrip('#').strip()
            elems.append(Paragraph(temizle(txt), styles['h2']))
        elif s.startswith('- ') or s.startswith('* '):
            txt = temizle(s[2:])
            if txt:
                elems.append(Paragraph(f'• {txt}', styles['bullet']))
        elif re.match(r'^\d+\.', s):
            txt = temizle(re.sub(r'^\d+\.\s*', '', s))
            num = re.match(r'^(\d+)\.', s).group(1)
            if txt:
                elems.append(Paragraph(f'{num}. {txt}', styles['bullet']))
        elif s.startswith('>'):
            txt = temizle(s[1:].strip())
            if txt:
                elems.append(Paragraph(f'   {txt}', styles['caption']))
        elif s.startswith('---'):
            elems.append(HRFlowable(width='100%', thickness=0.4,
                                    color=LGRAY, spaceAfter=3))
        elif s.startswith('|'):
            pass  # Markdown tabloları atla — zaten analiz metninde var
        else:
            txt = temizle(s)
            if txt:
                elems.append(Paragraph(txt, styles['body']))
    return elems


# ── SUPPLEMENT TABLOSU ────────────────────────────────────────────────────────
def supplement_tablosu(supplements: list, styles: dict) -> list:
    elems = []
    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph('  Supplement Plani', styles['h1']))
    elems.append(Paragraph(
        'Once yasam tarzi, supplement en son. Maksimum etkili minimum doz.',
        styles['caption']))
    elems.append(Spacer(1, 0.15*cm))

    oncelik_label = {'high': 'Yüksek', 'medium': 'Orta', 'low': 'Düşük'}
    oncelik_renk  = {'high': RED, 'medium': ACCENT, 'low': GREEN}

    header = [
        Paragraph('Takviye', styles['tbl_header']),
        Paragraph('Neden', styles['tbl_header']),
        Paragraph('Doz', styles['tbl_header']),
        Paragraph('Zaman', styles['tbl_header']),
        Paragraph('Öncelik', styles['tbl_header']),
    ]
    rows = [header]
    for s in supplements:
        p = s.get('priority', 'low')
        renk = oncelik_renk.get(p, GREEN)
        lbl  = oncelik_label.get(p, p)
        rows.append([
            Paragraph(s.get('name', ''), styles['tbl_body']),
            Paragraph(s.get('reason', ''), styles['tbl_body']),
            Paragraph(s.get('dosage', ''), styles['tbl_body']),
            Paragraph(s.get('timing', '').capitalize(), styles['tbl_body']),
            Paragraph(f'<b>{lbl}</b>',
                      ParagraphStyle('pl', fontSize=9, fontName=FONT_BOLD,
                                     textColor=renk)),
        ])

    t = Table(rows, colWidths=[3.5*cm, 6*cm, 2.5*cm, 2.5*cm, 2*cm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), BRAND),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LGRAY]),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#E5E7EB')),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elems.append(t)
    return elems


# ── EGZERSİZ PLANI TABLOSU ────────────────────────────────────────────────────
def egzersiz_tablosu(exercise: dict, styles: dict) -> list:
    weekly = exercise.get('weekly_plan', {})
    level  = exercise.get('level', '')
    if not weekly:
        return []

    level_map = {'beginner': 'Başlangıç', 'intermediate': 'Orta', 'advanced': 'İleri'}
    elems = []
    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph(
        f'  Haftalık Egzersiz Planı — {level_map.get(level, level)}',
        styles['h1']))
    elems.append(Spacer(1, 0.15*cm))

    header = [
        Paragraph('Gün', styles['tbl_header']),
        Paragraph('Antrenman', styles['tbl_header']),
    ]
    rows = [header]
    for gun, aktivite in weekly.items():
        rows.append([
            Paragraph(gun, styles['tbl_body']),
            Paragraph(aktivite, styles['tbl_body']),
        ])

    t = Table(rows, colWidths=[3.5*cm, 13*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), BRAND),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LGRAY]),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#E5E7EB')),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elems.append(t)
    return elems


# ── ANA FONKSİYON ─────────────────────────────────────────────────────────────
def analiz_pdf_olustur(
    analiz_metni: str,
    analiz_json_str: str | None,
    kullanici_adi: str = "Kullanici",
    tarih: str | None = None
) -> bytes:
    buffer = io.BytesIO()
    tarih = tarih or datetime.now().strftime('%d.%m.%Y')

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        title=f'Wellness Analizi — {kullanici_adi}',
    )

    styles = get_styles()
    story  = []

    # Kapak
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('WELLNESS ANALİZ RAPORU', styles['title']))
    story.append(Paragraph(kullanici_adi, styles['subtitle']))
    story.append(Paragraph(tarih, styles['caption']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT,
                            spaceBefore=6, spaceAfter=10))

    # Analiz metni
    if analiz_metni:
        story += markdown_to_elems(analiz_metni, styles)

    # JSON bölümü
    if analiz_json_str:
        try:
            data = json.loads(analiz_json_str)

            # Supplement normalize
            supps = data.get('supplements', data.get('takviyeler', []))
            if supps and 'isim' in (supps[0] if supps else {}):
                om = {1:'high', 2:'medium', 3:'low'}
                supps = [{'name': s.get('isim',''), 'reason': s.get('neden',''),
                          'dosage': s.get('doz',''), 'timing': s.get('zaman',''),
                          'priority': om.get(int(s.get('oncelik',2)),'medium')}
                         for s in supps]

            # Öncelikler
            priorities = data.get('priorities', [])
            if priorities:
                story.append(Spacer(1, 0.3*cm))
                story.append(Paragraph('  Öncelik Alanları', styles['h1']))
                for i, p in enumerate(priorities, 1):
                    story.append(Paragraph(f'{i}. {p}', styles['bullet']))

            # Supplement tablosu
            if supps:
                story += supplement_tablosu(supps, styles)

            # Egzersiz tablosu
            exercise = data.get('exercise_plan', {})
            if exercise:
                story += egzersiz_tablosu(exercise, styles)

            # Risk
            risk_notes = data.get('risk_notes', '')
            if risk_notes:
                story.append(Spacer(1, 0.3*cm))
                story.append(Paragraph('  Risk Uyarıları', styles['h1']))
                story.append(Paragraph(risk_notes, styles['body']))

        except Exception:
            pass

    # Disclaimer
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGRAY,
                            spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        f'Bu rapor yalnızca bilgilendirme amaçlıdır ve tıbbi tavsiye niteliğinde değildir. '
        f'Herhangi bir takviye kullanmadan önce bir sağlık uzmanına danışınız. | '
        f'Wellness Analiz Sistemi | {tarih}',
        styles['disclaimer']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()