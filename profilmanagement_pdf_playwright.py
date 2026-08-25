"""Playwright-PDF-Export für WERK TRIFFT Profilmanagement."""
from __future__ import annotations

import base64
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

BLUE, ORANGE, INK, MUTED, LINE, PAPER = '#143D6A', '#D76F23', '#2B2B2B', '#66758A', '#D9DDD8', '#FFFEFA'


class PDFExportUnavailable(RuntimeError):
    pass


def _text(value: Any) -> str:
    return str(value or '').strip()


def _escape(value: Any) -> str:
    return html.escape(_text(value), quote=True)


def _data_url(path: str | Path | None) -> str:
    if not path:
        return ''
    path = Path(path)
    if not path.is_file():
        return ''
    mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml'}.get(path.suffix.lower())
    return f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode("ascii")}' if mime else ''


def _selected(profile: dict[str, Any], variant: dict[str, Any], key: str) -> list[dict[str, Any]]:
    contents = variant.get('inhalte') if isinstance(variant.get('inhalte'), dict) else profile
    source = {str(row.get('id')): row for row in contents.get(key, []) if isinstance(row, dict) and row.get('id')}
    result = []
    for index, choice in enumerate((variant.get('auswahl') or {}).get(key, [])):
        if not isinstance(choice, dict) or not choice.get('sichtbar', False):
            continue
        row = source.get(str(choice.get('id')))
        if row:
            try:
                order = int(choice.get('reihenfolge', index + 1))
            except (TypeError, ValueError):
                order = index + 1
            result.append((order, index, row))
    return [row for _, _, row in sorted(result)]


def _period(item: dict[str, Any]) -> str:
    def month(value: Any) -> str:
        value = _text(value)
        return f'{value[5:7]}/{value[:4]}' if re.fullmatch(r'\d{4}-\d{2}', value) else value
    return ' – '.join(part for part in (month(item.get('startMonat')), 'laufend' if item.get('laufend') else month(item.get('endeMonat'))) if part)


def _label(item: dict[str, Any], key: str) -> str:
    if key == 'sprachen':
        return ' · '.join(part for part in (_text(item.get('sprache')), _text(item.get('niveau'))) if part)
    return _text(item.get('bezeichnung')) or _text(item.get('titel'))


def _chips(items: list[dict[str, Any]], key: str) -> str:
    return ''.join(f'<span class="chip">{_escape(_label(item, key))}</span>' for item in items if _label(item, key))


def build_profile_html(profile: dict[str, Any], variant: dict[str, Any], logo_path: str | Path | None = None, photo_path: str | Path | None = None) -> str:
    person = profile.get('person') or {}
    content = variant.get('inhalte') if isinstance(variant.get('inhalte'), dict) else profile
    short = content.get('kurzprofil') or {}
    name = ' '.join(part for part in (_text(person.get('titel')), _text(person.get('vorname')), _text(person.get('nachname'))) if part) or 'Beraterprofil'
    role = _text(variant.get('zielrolle')) or _text(person.get('rolle'))
    photo = _data_url(photo_path) if variant.get('fotoSichtbar') else ''
    logo = _data_url(logo_path)
    bio = '\n\n'.join(part for part in (_text(short.get('positionierung')), _text(short.get('zusammenfassung'))) if part)

    def section(title: str, body: str) -> str:
        return f'<section><div class="label">{title}</div>{body}</section>' if body else ''

    sections = []
    if bio:
        sections.append(section('Kurzprofil', f'<div class="bio">{_escape(bio)}</div>'))
    for key, title in (('kompetenzen', 'Kompetenzen'), ('branchen', 'Branchen'), ('qualifikationen', 'Qualifikationen'), ('sprachen', 'Sprachen')):
        sections.append(section(title, _chips(_selected(profile, variant, key), key)))
    projects = []
    for item in _selected(profile, variant, 'projekte'):
        meta = ' · '.join(part for part in (_period(item), _text(item.get('rolle'))) if part)
        description, tasks = _text(item.get('beschreibung')), _text(item.get('aufgaben'))
        projects.append(f'<article><div class="meta">{_escape(meta)}</div><h3>{_escape(item.get("titel"))}</h3>{f"<p>{_escape(description)}</p>" if description else ""}{f"<p><strong>Tätigkeiten:</strong> {_escape(tasks)}</p>" if tasks else ""}</article>')
    sections.append(section('Projekterfahrung', ''.join(projects)))

    wordmark = f'<img class="logo" src="{logo}" alt="WERK TRIFFT">' if logo else '<div class="wordmark">WERK <span>TRIFFT</span></div>'
    portrait = f'<img class="portrait" src="{photo}" alt="Profilfoto">' if photo else ''
    role_html = f'<div class="role">{_escape(role)}</div>' if role else ''
    generated = datetime.now().strftime('%d.%m.%Y')
    css = '''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;color:#2B2B2B;background:#fff;font:9.5pt Arial,sans-serif;line-height:1.52}.page{min-height:297mm;padding:12mm 16mm 14mm}.header{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:6mm;border-bottom:.5pt solid #D9DDD8;margin-bottom:8mm}.logo{height:14mm;width:auto}.wordmark{color:#143D6A;font-size:14pt;font-weight:800;letter-spacing:.12em}.wordmark span{color:#D76F23}.header-note,.meta,.label{font:7.5pt 'Courier New',monospace;color:#66758A}.header-note{text-align:right}.profile{display:flex;justify-content:space-between;align-items:center;gap:6mm;border-bottom:1pt solid #D9DDD8;padding-bottom:5mm;margin-bottom:6mm}.portrait{width:25mm;height:25mm;border-radius:50%;object-fit:cover;border:.7pt solid #D9DDD8;flex:0 0 auto}h1{margin:0;color:#143D6A;font-size:20pt;line-height:1.12}.role{color:#66758A}section{padding-bottom:5mm;margin-bottom:5mm;border-bottom:.5pt solid #D9DDD8}.label{font-weight:bold;letter-spacing:.1em;text-transform:uppercase;margin-bottom:2mm}.bio{white-space:pre-line;color:#425161}.chip{display:inline-block;border:.5pt solid #D9DDD8;border-radius:9pt;padding:1.1mm 2.3mm;margin:0 1.5mm 1.5mm 0;color:#143D6A}article{border-top:.5pt solid #E5E7E5;padding:3.5mm 0}article:first-child{border-top:0;padding-top:0}article h3{margin:0;color:#143D6A;font-size:11pt}article p{margin:1.3mm 0}'''
    return f'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>{_escape(name)}</title><style>{css}</style></head><body><main class="page"><header class="header">{wordmark}<div class="header-note">WERK TRIFFT<br>Beraterprofil<br>Erstellt am {generated}</div></header><section class="profile"><div><h1>{_escape(name)}</h1>{role_html}</div>{portrait}</section>{"".join(sections)}</main></body></html>'


def export_pdf(profile: dict[str, Any], variant: dict[str, Any], target: str | Path, logo_path: str | Path | None = None, photo_path: str | Path | None = None) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:
        raise PDFExportUnavailable('PDF-Export ist noch nicht eingerichtet.') from error
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.set_content(build_profile_html(profile, variant, logo_path, photo_path), wait_until='load')
            page.pdf(path=str(target), format='A4', print_background=True, margin={'top':'0','right':'0','bottom':'0','left':'0'})
            browser.close()
    except Exception as error:
        raise PDFExportUnavailable(f'PDF-Export konnte Chromium nicht starten: {error}') from error
    return target
