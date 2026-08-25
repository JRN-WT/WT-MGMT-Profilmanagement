"""Playwright-PDF-Export für WERK TRIFFT Profilmanagement."""
from __future__ import annotations
import base64, html, re
from datetime import datetime
from pathlib import Path

BLUE, ORANGE, MUTED, LINE = '#143D6A', '#D76F23', '#66758A', '#D9DDD8'
class PDFExportUnavailable(RuntimeError): pass

def txt(value): return str(value or '').strip()
def esc(value): return html.escape(txt(value), quote=True)
def data_url(path):
    path=Path(path) if path else None
    if not path or not path.is_file(): return ''
    mime={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.svg':'image/svg+xml'}.get(path.suffix.lower())
    return f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}' if mime else ''
def rows(profile, variant, key):
    source=(variant.get('inhalte') or profile).get(key,[]); index={str(x.get('id')):x for x in source if isinstance(x,dict)}; result=[]
    for pos, choice in enumerate((variant.get('auswahl') or {}).get(key,[])):
        item=index.get(str(choice.get('id')))
        if item and choice.get('sichtbar',False):
            try: order=int(choice.get('reihenfolge',pos+1))
            except (TypeError,ValueError): order=pos+1
            result.append((order,pos,item))
    return [item for _,_,item in sorted(result)]
def period(item):
    def month(value):
        value=txt(value); return f'{value[5:7]}/{value[:4]}' if re.fullmatch(r'\d{4}-\d{2}',value) else value
    return ' – '.join(x for x in (month(item.get('startMonat')), 'laufend' if item.get('laufend') else month(item.get('endeMonat'))) if x)
def label(item,key):
    return ' · '.join(x for x in (txt(item.get('sprache')),txt(item.get('niveau'))) if x) if key=='sprachen' else txt(item.get('bezeichnung')) or txt(item.get('titel'))
def chips(items,key): return ''.join(f'<span class="chip">{esc(label(item,key))}</span>' for item in items if label(item,key))
def build_html(profile,variant,logo_path=None,photo_path=None):
    person=profile.get('person') or {}; content=variant.get('inhalte') or profile; short=content.get('kurzprofil') or {}
    name=' '.join(x for x in (txt(person.get('titel')),txt(person.get('vorname')),txt(person.get('nachname'))) if x) or 'Beraterprofil'
    role=txt(variant.get('zielrolle')) or txt(person.get('rolle')); logo=data_url(logo_path); photo=data_url(photo_path) if variant.get('fotoSichtbar') else ''
    def section(title,body): return f'<section><div class="label">{title}</div>{body}</section>' if body else ''
    bio='\n\n'.join(x for x in (txt(short.get('positionierung')),txt(short.get('zusammenfassung'))) if x)
    groups=''.join(section({'kompetenzen':'Kompetenzen','branchen':'Branchen','qualifikationen':'Qualifikationen','sprachen':'Sprachen'}[key],chips(rows(profile,variant,key),key)) for key in ('kompetenzen','branchen','qualifikationen','sprachen'))
    projects=[]
    for item in rows(profile,variant,'projekte'):
        meta=' · '.join(x for x in (period(item),txt(item.get('rolle'))) if x); desc=txt(item.get('beschreibung')); tasks=txt(item.get('aufgaben'))
        projects.append(f'<article><div class="meta">{esc(meta)}</div><h3>{esc(item.get("titel"))}</h3>{f"<p>{esc(desc)}</p>" if desc else ""}{f"<p><strong>Tätigkeiten:</strong> {esc(tasks)}</p>" if tasks else ""}</article>')
    mark=f'<img class="logo" src="{logo}" alt="WERK TRIFFT">' if logo else f'<div class="word">WERK <b>TRIFFT</b></div>'
    avatar=f'<img class="photo" src="{photo}" alt="Profilfoto">' if photo else ''
    return f'''<!doctype html><html lang="de"><meta charset="utf-8"><style>@page{{size:A4;margin:0}}*{{box-sizing:border-box}}body{{margin:0;font:9.5pt Arial;color:#2B2B2B;line-height:1.52}}main{{padding:12mm 16mm 14mm}}header{{display:flex;justify-content:space-between;border-bottom:.5pt solid {LINE};padding-bottom:6mm;margin-bottom:8mm}}.logo{{height:14mm}}.word{{font-size:14pt;font-weight:bold;letter-spacing:.12em;color:{BLUE}}.word b{{color:{ORANGE}}}.note,.meta,.label{{font:7.5pt 'Courier New';color:{MUTED}}}.note{{text-align:right}}.profile{{display:flex;justify-content:space-between;align-items:center;gap:6mm;border-bottom:1pt solid {LINE};padding-bottom:5mm;margin-bottom:6mm}}h1{{margin:0;color:{BLUE};font-size:20pt}}.role{{color:{MUTED}}}.photo{{width:25mm;height:25mm;border-radius:50%;object-fit:cover;border:.7pt solid {LINE}}}section{{border-bottom:.5pt solid {LINE};padding-bottom:5mm;margin-bottom:5mm}}.label{{font-weight:bold;letter-spacing:.1em;text-transform:uppercase;margin-bottom:2mm}}.chip{{display:inline-block;border:.5pt solid {LINE};border-radius:9pt;padding:1.1mm 2.3mm;margin:0 1.5mm 1.5mm 0;color:{BLUE}}article{{border-top:.5pt solid #E5E7E5;padding:3.5mm 0}}article:first-child{{border:0;padding-top:0}}h3{{margin:0;color:{BLUE};font-size:11pt}}p{{margin:1.3mm 0}}.bio{{white-space:pre-line}}</style><main><header>{mark}<div class="note">WERK TRIFFT<br>Beraterprofil<br>Erstellt am {datetime.now().strftime('%d.%m.%Y')}</div></header><div class="profile"><div><h1>{esc(name)}</h1>{f'<div class="role">{esc(role)}</div>' if role else ''}</div>{avatar}</div>{section('Kurzprofil',f'<div class="bio">{esc(bio)}</div>') if bio else ''}{groups}{section('Projekterfahrung',''.join(projects))}</main></html>'''
def export_pdf(profile,variant,target,logo_path=None,photo_path=None):
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error: raise PDFExportUnavailable('PDF-Export ist noch nicht eingerichtet.') from error
    target=Path(target); target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(); page=browser.new_page(); page.set_content(build_html(profile,variant,logo_path,photo_path),wait_until='load'); page.pdf(path=str(target),format='A4',print_background=True,margin={'top':'0','right':'0','bottom':'0','left':'0'}); browser.close()
    except Exception as error: raise PDFExportUnavailable(f'PDF-Export konnte Chromium nicht starten: {error}') from error
    return target
