"""
pdf_export.py — Wellness analiz raporunu PDF olarak üretir.
DejaVuSans fontu ile Türkçe karakter desteği.
Supplement detay kartları, marka önerileri ve markdown tablo desteği dahil.
"""
import io, json, re, os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── FONT ─────────────────────────────────────────────────────────────────────
def _reg():
    base = os.path.dirname(os.path.abspath(__file__))
    fd   = os.path.join(base, 'fonts')
    defs = {
        'DV':  [os.path.join(fd,'DejaVuSans.ttf'),         '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'],
        'DVB': [os.path.join(fd,'DejaVuSans-Bold.ttf'),    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
        'DVI': [os.path.join(fd,'DejaVuSans-Oblique.ttf'), '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf'],
    }
    reg = {}
    for k, paths in defs.items():
        for p in paths:
            if os.path.exists(p):
                try: pdfmetrics.registerFont(TTFont(k, p)); reg[k]=p; break
                except: pass
    if 'DV' in reg and 'DVB' in reg:
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily('DV', normal='DV', bold='DVB',
                           italic=reg.get('DVI','DV') and 'DVI' or 'DV',
                           boldItalic='DVB')
        return 'DV','DVB','DVI' if 'DVI' in reg else 'DV'
    return 'Helvetica','Helvetica-Bold','Helvetica-Oblique'

FN, FB, FI = _reg()

# ── RENKLER ──────────────────────────────────────────────────────────────────
C_BRAND  = colors.HexColor('#2D5F3F')
C_ACCENT = colors.HexColor('#D4A847')
C_DARK   = colors.HexColor('#1A1714')
C_GRAY   = colors.HexColor('#6B7280')
C_LGRAY  = colors.HexColor('#F3F4F6')
C_MGRAY  = colors.HexColor('#E5E7EB')
C_WHITE  = colors.white
C_RED    = colors.HexColor('#DC2626')
C_GREEN  = colors.HexColor('#16A34A')
C_BLUE   = colors.HexColor('#1D4ED8')
C_AMBER  = colors.HexColor('#D97706')


# ── STİLLER ──────────────────────────────────────────────────────────────────
def S():
    def ps(name, **kw):
        defaults = dict(fontName=FN, fontSize=10, textColor=C_DARK,
                        spaceAfter=4, leading=15)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)
    return {
        'title':    ps('t',  fontSize=20, fontName=FB, textColor=C_BRAND, spaceAfter=3, alignment=TA_CENTER),
        'subtitle': ps('s',  fontSize=11, textColor=C_GRAY, spaceAfter=2, alignment=TA_CENTER),
        'h1':       ps('h1', fontSize=13, fontName=FB, textColor=C_WHITE, spaceBefore=14,
                        spaceAfter=6, backColor=C_BRAND, borderPad=5),
        'h2':       ps('h2', fontSize=11, fontName=FB, textColor=C_BRAND, spaceBefore=10, spaceAfter=4),
        'h3':       ps('h3', fontSize=10, fontName=FB, textColor=C_DARK, spaceBefore=6, spaceAfter=3),
        'body':     ps('b'),
        'bullet':   ps('bl', leftIndent=14, spaceAfter=3, leading=14),
        'caption':  ps('c',  fontSize=9, textColor=C_GRAY, fontName=FI, spaceAfter=2),
        'disc':     ps('d',  fontSize=8, textColor=C_GRAY, fontName=FI, alignment=TA_CENTER),
        'th':       ps('th', fontSize=10, fontName=FB, textColor=C_WHITE, leading=13),
        'td':       ps('td', fontSize=9,  textColor=C_DARK, leading=13),
        'td_sm':    ps('ts', fontSize=8,  textColor=C_GRAY, leading=12),
        'high':     ps('hi', fontSize=9,  fontName=FB, textColor=C_RED),
        'medium':   ps('me', fontSize=9,  fontName=FB, textColor=C_AMBER),
        'low':      ps('lo', fontSize=9,  fontName=FB, textColor=C_GREEN),
        'brand_nm': ps('bn', fontSize=10, fontName=FB, textColor=C_BRAND, spaceAfter=2),
        'brand_why':ps('bw', fontSize=9,  textColor=C_DARK, leading=13, spaceAfter=2),
        'tag_eco':  ps('te', fontSize=8,  fontName=FB, textColor=C_GREEN),
        'tag_mid':  ps('tm2',fontSize=8,  fontName=FB, textColor=C_AMBER),
        'tag_pre':  ps('tp', fontSize=8,  fontName=FB, textColor=C_BLUE),
    }


# ── YARDIMCILAR ───────────────────────────────────────────────────────────────
def clean(t):
    if not t: return ''
    t = re.sub(r'```json.*?```','',t,flags=re.DOTALL)
    t = re.sub(r'```.*?```','',t,flags=re.DOTALL)
    t = re.sub(r'## BÖLÜM 2.*','',t,flags=re.DOTALL)
    t = re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',t)
    t = re.sub(r'\*(.+?)\*',r'<i>\1</i>',t)
    # emoji temizle
    t = re.sub(r'[^\x00-\xFF\u011E\u011F\u0130\u0131\u015E\u015F\u00C7\u00E7\u00D6\u00F6\u00DC\u00FC]','',t)
    return t.strip()

def tbl_style(header_bg=None):
    bg = header_bg or C_BRAND
    return TableStyle([
        ('BACKGROUND',    (0,0),(-1,0), bg),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[C_WHITE, C_LGRAY]),
        ('GRID',          (0,0),(-1,-1), 0.3, C_MGRAY),
        ('VALIGN',        (0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',   (0,0),(-1,-1), 6),
        ('RIGHTPADDING',  (0,0),(-1,-1), 6),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
    ])


# ── MARKDOWN TABLO PARSE ──────────────────────────────────────────────────────
def parse_md_table(lines, styles):
    """Markdown | tablo | satırlarını reportlab Table'a çevirir."""
    rows = []
    for line in lines:
        if re.match(r'^\|[-:\s|]+\|$', line.strip()):
            continue  # ayırıcı satır
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    if not rows:
        return None
    col_count = max(len(r) for r in rows)
    # Kolon genişlikleri — eşit dağıt
    avail = 16.4 * cm
    col_w = [avail / col_count] * col_count

    tbl_rows = []
    for i, row in enumerate(rows):
        # Sütun sayısını eşitle
        while len(row) < col_count:
            row.append('')
        if i == 0:
            tbl_rows.append([Paragraph(clean(c), styles['th']) for c in row])
        else:
            tbl_rows.append([Paragraph(clean(c), styles['td']) for c in row])

    t = Table(tbl_rows, colWidths=col_w, repeatRows=1)
    t.setStyle(tbl_style())
    return t


# ── METİN → FLOWABLE ─────────────────────────────────────────────────────────
def md_to_elems(metin, styles):
    elems = []
    lines = metin.split('\n')
    i = 0
    while i < len(lines):
        s = lines[i].strip()

        # Markdown tablo başlıyor mu?
        if s.startswith('|') and i+1 < len(lines) and re.match(r'^\|[-:\s|]+\|$', lines[i+1].strip()):
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                tbl_lines.append(lines[i])
                i += 1
            t = parse_md_table(tbl_lines, styles)
            if t:
                elems.append(Spacer(1, 0.1*cm))
                elems.append(t)
                elems.append(Spacer(1, 0.1*cm))
            continue

        if not s:
            pass
        elif s.startswith('## '):
            elems.append(Spacer(1,0.2*cm))
            elems.append(Paragraph(f'  {clean(s[3:])}', styles['h1']))
        elif s.startswith('### ') or (s.startswith('# ') and not s.startswith('## ')):
            elems.append(Paragraph(clean(s.lstrip('#').strip()), styles['h2']))
        elif s.startswith('- ') or s.startswith('* '):
            txt = clean(s[2:])
            if txt: elems.append(Paragraph(f'• {txt}', styles['bullet']))
        elif re.match(r'^\d+\.', s):
            num = re.match(r'^(\d+)\.', s).group(1)
            txt = clean(re.sub(r'^\d+\.\s*','',s))
            if txt: elems.append(Paragraph(f'{num}. {txt}', styles['bullet']))
        elif s.startswith('>'):
            txt = clean(s[1:].strip())
            if txt: elems.append(Paragraph(f'   {txt}', styles['caption']))
        elif s.startswith('---'):
            elems.append(HRFlowable(width='100%',thickness=0.4,color=C_LGRAY,spaceAfter=3))
        else:
            txt = clean(s)
            if txt: elems.append(Paragraph(txt, styles['body']))
        i += 1
    return elems


# ── SUPPLEMENT DETAY KARTLARI ─────────────────────────────────────────────────
def supplement_detay(supplements, styles):
    elems = []
    elems.append(Spacer(1,0.3*cm))
    elems.append(Paragraph('  Supplement Planı — Detaylı Analiz', styles['h1']))
    elems.append(Paragraph(
        'Önce yaşam tarzı, supplement en son. Maksimum etkili minimum doz.',
        styles['caption']))
    elems.append(Spacer(1,0.15*cm))

    oncelik_label = {'high':'Yüksek Öncelik','medium':'Orta Öncelik','low':'Düşük Öncelik'}
    oncelik_style = {'high':'high','medium':'medium','low':'low'}
    price_label   = {'ekonomik':'Ekonomik','orta':'Orta Fiyat','premium':'Premium'}
    price_style   = {'ekonomik':'tag_eco','orta':'tag_mid','premium':'tag_pre'}

    for s in supplements:
        priority = s.get('priority','low')
        p_lbl    = oncelik_label.get(priority, priority)
        p_sty    = oncelik_style.get(priority,'low')
        brands   = s.get('brands', [])
        caution  = s.get('caution','')
        mechanism= s.get('mechanism','')
        active   = s.get('active_ingredient','')

        card_elems = []

        # Başlık satırı
        header_row = [[
            Paragraph(f'<b>{clean(s.get("name",""))}</b>',
                      ParagraphStyle('sh', fontName=FB, fontSize=12,
                                     textColor=C_WHITE, leading=16)),
            Paragraph(p_lbl,
                      ParagraphStyle('sp', fontName=FB, fontSize=9,
                                     textColor=C_WHITE, alignment=TA_RIGHT)),
        ]]
        ht = Table(header_row, colWidths=[12*cm, 4.4*cm])
        ht.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1), C_BRAND),
            ('LEFTPADDING',(0,0),(-1,-1),8),
            ('RIGHTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ]))
        card_elems.append(ht)

        # Temel bilgiler
        info_rows = []
        if s.get('reason'):
            info_rows.append(['Neden', clean(s['reason'])])
        if s.get('dosage'):
            info_rows.append(['Doz', clean(s['dosage'])])
        if s.get('timing'):
            info_rows.append(['Alım Zamanı', clean(s['timing']).capitalize()])
        if active:
            info_rows.append(['Aktif Madde', clean(active)])
        if mechanism:
            info_rows.append(['Etki Mekanizması', clean(mechanism)])

        if info_rows:
            tbl = Table(
                [[Paragraph(r[0], ParagraphStyle('lbl',fontName=FB,fontSize=9,
                                                  textColor=C_GRAY,leading=13)),
                  Paragraph(r[1], styles['td'])] for r in info_rows],
                colWidths=[3.5*cm, 12.9*cm]
            )
            tbl.setStyle(TableStyle([
                ('ROWBACKGROUNDS',(0,0),(-1,-1),[C_WHITE,C_LGRAY]),
                ('GRID',(0,0),(-1,-1),0.3,C_MGRAY),
                ('LEFTPADDING',(0,0),(-1,-1),6),
                ('RIGHTPADDING',(0,0),(-1,-1),6),
                ('TOPPADDING',(0,0),(-1,-1),4),
                ('BOTTOMPADDING',(0,0),(-1,-1),4),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
            ]))
            card_elems.append(tbl)

        # Marka önerileri
        if brands:
            card_elems.append(Spacer(1,0.1*cm))
            card_elems.append(Paragraph('  Marka Önerileri', 
                ParagraphStyle('bh', fontName=FB, fontSize=9,
                               textColor=C_WHITE, backColor=C_ACCENT,
                               borderPad=4, leading=14)))

            brand_header = [
                Paragraph('Marka / Ürün', styles['th']),
                Paragraph('Neden Öneriliyor', styles['th']),
                Paragraph('Fiyat', styles['th']),
                Paragraph('Nereden', styles['th']),
            ]
            brand_rows = [brand_header]
            for b in brands:
                pr = b.get('price_range','orta')
                pr_lbl = price_label.get(pr, pr)
                pr_sty = price_style.get(pr,'tag_mid')
                brand_rows.append([
                    Paragraph(f'<b>{clean(b.get("name",""))}</b><br/>'
                              f'<i>{clean(b.get("product",""))}</i>',
                              styles['td']),
                    Paragraph(clean(b.get('why','')), styles['td_sm']),
                    Paragraph(pr_lbl, styles[pr_sty]),
                    Paragraph(clean(b.get('where','')), styles['td_sm']),
                ])
            bt = Table(brand_rows, colWidths=[4*cm,7*cm,2.2*cm,3.2*cm],
                       repeatRows=1)
            bt.setStyle(tbl_style(C_ACCENT))
            card_elems.append(bt)

        # Uyarı
        if caution:
            card_elems.append(Spacer(1,0.08*cm))
            card_elems.append(Paragraph(
                f'⚠ Dikkat: {clean(caution)}',
                ParagraphStyle('caut', fontName=FI, fontSize=8,
                               textColor=C_RED, leading=12,
                               backColor=colors.HexColor('#FFF5F5'),
                               borderPad=4)))

        card_elems.append(Spacer(1,0.3*cm))
        elems.append(KeepTogether(card_elems))

    return elems


# ── EGZERSİZ TABLOSU ─────────────────────────────────────────────────────────
def egzersiz_tablosu(exercise, styles):
    weekly = exercise.get('weekly_plan',{})
    level  = exercise.get('level','')
    if not weekly: return []
    lm = {'beginner':'Başlangıç','intermediate':'Orta','advanced':'İleri'}
    elems = [Spacer(1,0.3*cm),
             Paragraph(f'  Haftalık Egzersiz Planı — {lm.get(level,level)}', styles['h1']),
             Spacer(1,0.15*cm)]
    rows = [[Paragraph('Gün',styles['th']), Paragraph('Antrenman',styles['th'])]]
    for gun, akt in weekly.items():
        rows.append([Paragraph(gun,styles['td']), Paragraph(akt,styles['td'])])
    t = Table(rows, colWidths=[3.5*cm,13*cm], repeatRows=1)
    t.setStyle(tbl_style())
    elems.append(t)
    return elems


# ── ANA FONKSİYON ─────────────────────────────────────────────────────────────
def analiz_pdf_olustur(analiz_metni, analiz_json_str,
                       kullanici_adi='Kullanici', tarih=None):
    buffer = io.BytesIO()
    tarih  = tarih or datetime.now().strftime('%d.%m.%Y')
    styles = S()

    doc = SimpleDocTemplate(buffer, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        title=f'Wellness Analizi — {kullanici_adi}')

    story = []

    # Kapak
    story += [
        Spacer(1,0.5*cm),
        Paragraph('WELLNESS ANALİZ RAPORU', styles['title']),
        Paragraph(kullanici_adi, styles['subtitle']),
        Paragraph(tarih, styles['caption']),
        HRFlowable(width='100%',thickness=1.5,color=C_ACCENT,
                   spaceBefore=6,spaceAfter=10),
    ]

    # Analiz metni (markdown tabloları dahil)
    if analiz_metni:
        story += md_to_elems(analiz_metni, styles)

    # JSON bölümü
    if analiz_json_str:
        try:
            data = json.loads(analiz_json_str)

            # Normalize eski format
            supps = data.get('supplements', data.get('takviyeler',[]))
            if supps and 'isim' in (supps[0] if supps else {}):
                om = {1:'high',2:'medium',3:'low'}
                supps = [{'name':s.get('isim',''), 'reason':s.get('neden',''),
                          'dosage':s.get('doz',''), 'timing':s.get('zaman',''),
                          'priority':om.get(int(s.get('oncelik',2)),'medium')}
                         for s in supps]

            # Öncelikler
            priorities = data.get('priorities',[])
            if priorities:
                story.append(Spacer(1,0.3*cm))
                story.append(Paragraph('  Öncelik Alanları', styles['h1']))
                for i,p in enumerate(priorities,1):
                    story.append(Paragraph(f'{i}. {p}', styles['bullet']))

            # Supplement detay kartları
            if supps:
                story += supplement_detay(supps, styles)

            # Egzersiz planı
            exercise = data.get('exercise_plan',{})
            if exercise:
                story += egzersiz_tablosu(exercise, styles)

            # Risk
            risk_notes = data.get('risk_notes','')
            if risk_notes:
                story += [Spacer(1,0.3*cm),
                          Paragraph('  Risk Uyarıları', styles['h1']),
                          Paragraph(clean(risk_notes), styles['body'])]
        except Exception:
            pass

    # Disclaimer
    story += [
        Spacer(1,0.6*cm),
        HRFlowable(width='100%',thickness=0.5,color=C_LGRAY,
                   spaceBefore=4,spaceAfter=4),
        Paragraph(
            f'Bu rapor yalnızca bilgilendirme amaçlıdır ve tıbbi tavsiye niteliğinde değildir. '
            f'Herhangi bir takviye kullanmadan önce bir sağlık uzmanına danışınız. | '
            f'Wellness Analiz Sistemi | {tarih}',
            styles['disc'])
    ]

    doc.build(story)
    buffer.seek(0)
    return buffer.read()