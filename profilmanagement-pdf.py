#!/usr/bin/env python3
"""PDF-Export fuer WERK TRIFFT Profilmanagement.
Erzeugt eine A4-Profil-PDF aus einer gespeicherten Profilvariante.
"""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
import subprocess

BLUE = colors.HexColor('#143D6A')
ORANGE = colors.HexColor('#D76F23')
INK = colors.HexColor('#2B2B2B')
MUTED = colors.HexColor('#66758A')
LINE = colors.HexColor('#C8BEA8')
PAPER = colors.HexColor('#F9F6EF')
WHITE = colors.white


def font_path(name):
    result = subprocess.run(['fc-match', '-f', '%{file}', name], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont('Inter', font_path('Inter')))
        pdfmetrics.registerFont(TTFont('InterBold', font_path('Inter:style=Bold')))
        return 'Inter', 'InterBold'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'


def months(project):
    start = project.get('startMonat', '')
    end = project.get('endeMonat', '')
    def display(value): return f'{value[5:7]}/{value[:4]}' if len(value) == 7 else ''
    parts = [display(start), 'laufend' if project.get('laufend') else display(end), project.get('rolle', '')]
    return ' · '.join(part for part in parts if part)


def selected(contents, selection, key):
    order = {item.get('id'): item for item in selection.get(key, []) if item.get('sichtbar')}
    return sorted((item for item in contents.get(key, []) if item.get('id') in order), key=lambda item: order[item['id']].get('reihenfolge', 9999))


def export_pdf(profile, variant, target):
    regular, bold = register_fonts()
    person = profile.get('person', {})
    contents = variant.get('inhalte') or {key: profile.get(key, []) for key in ('kompetenzen', 'branchen', 'qualifikationen', 'sprachen', 'projekte')}
    selection = variant.get('auswahl', {})
    title = f"{person.get('vorname', '')} {person.get('nachname', '')}".strip() or 'Beraterprofil'
    role = variant.get('zielrolle') or person.get('rolle', '')

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Name', fontName=bold, fontSize=25, leading=29, textColor=BLUE, spaceAfter=3))
    styles.add(ParagraphStyle(name='Role', fontName=regular, fontSize=11, leading=15, textColor=MUTED, spaceAfter=8))
    styles.add(ParagraphStyle(name='Section', fontName=bold, fontSize=9, leading=12, textColor=BLUE, spaceBefore=11, spaceAfter=5, uppercase=True))
    styles.add(ParagraphStyle(name='Body', fontName=regular, fontSize=9.5, leading=14, textColor=INK))
    styles.add(ParagraphStyle(name='Position', fontName=bold, fontSize=11, leading=15, textColor=INK, spaceAfter=4))
    styles.add(ParagraphStyle(name='Meta', fontName=regular, fontSize=8.5, leading=12, textColor=MUTED))
    styles.add(ParagraphStyle(name='ProjectTitle', fontName=bold, fontSize=10.5, leading=14, textColor=BLUE, spaceAfter=1))

    def paragraph(text, style='Body'):
        return Paragraph(escape(str(text or '')).replace('\n', '<br/>'), styles[style])
    def section(title, content):
        return [Paragraph(title, styles['Section']), content]

    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=19*mm, leftMargin=19*mm, topMargin=17*mm, bottomMargin=16*mm, title=title, author='WERK TRIFFT')
    story = []

    header = Table([[paragraph('WERK TRIFFT', 'Section'), paragraph(variant.get('name') or 'Profilvariante', 'Meta')]], colWidths=[85*mm, 87*mm])
    header.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LINEBELOW', (0,0), (-1,-1), 2, ORANGE), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    story += [header, Spacer(1, 9), paragraph(title, 'Name'), paragraph(role, 'Role')]

    contacts = [person.get('standort', ''), person.get('interneEmail', ''), person.get('telefon', '')]
    contacts = [x for x in contacts if x]
    if contacts:
        story += [paragraph(' · '.join(contacts), 'Meta'), Spacer(1, 5)]

    short = contents.get('kurzprofil') or profile.get('kurzprofil', {})
    if short.get('positionierung') or short.get('zusammenfassung'):
        content = []
        if short.get('positionierung'): content.append(paragraph(short['positionierung'], 'Position'))
        if short.get('zusammenfassung'): content.append(paragraph(short['zusammenfassung']))
        story += section('Kurzprofil', KeepTogether(content))

    for key, heading in [('kompetenzen', 'Kompetenzen'), ('branchen', 'Branchen'), ('qualifikationen', 'Qualifikationen & Zertifikate'), ('sprachen', 'Sprachen')]:
        rows = selected(contents, selection, key)
        if rows:
            values = []
            for row in rows:
                values.append(row.get('sprache', '') + (f" · {row.get('niveau')}" if row.get('niveau') else '') if key == 'sprachen' else row.get('bezeichnung', ''))
            story += section(heading, paragraph(' · '.join(filter(None, values))))

    projects = selected(contents, selection, 'projekte')
    if projects:
        project_blocks = []
        for project in projects:
            block = [paragraph(project.get('titel') or 'Projekt', 'ProjectTitle')]
            meta = months(project)
            if meta: block.append(paragraph(meta, 'Meta'))
            if project.get('beschreibung'): block += [Spacer(1, 3), paragraph(project['beschreibung'])]
            if project.get('aufgaben'): block += [Spacer(1, 3), paragraph('<b>Tätigkeiten:</b> ' + project['aufgaben'])]
            project_blocks.append(KeepTogether(block + [Spacer(1, 8)]))
        story += section('Projekterfahrung', project_blocks)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE); canvas.setLineWidth(.5)
        canvas.line(19*mm, 12*mm, A4[0]-19*mm, 12*mm)
        canvas.setFont(regular, 7.5); canvas.setFillColor(MUTED)
        canvas.drawString(19*mm, 8*mm, 'WERK TRIFFT · Profilmanagement')
        canvas.drawRightString(A4[0]-19*mm, 8*mm, f'Seite {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return target
