#!/usr/bin/env python3
"""Optionaler Playwright-PDF-Export fuer WERK TRIFFT Profilmanagement.

Das Modul selbst nutzt nur die Python-Standardbibliothek. Playwright wird erst
beim eigentlichen Export importiert, damit der lokale JSON-Server ohne PDF-
Abhaengigkeit weiterhin starten kann.
"""
from __future__ import annotations

import base64
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

BLUE = "#143D6A"
ORANGE = "#D76F23"
INK = "#2B2B2B"
MUTED = "#66758A"
LINE = "#D9DDD8"
PAPER = "#FFFEFA"

LISTS = ("kompetenzen", "branchen", "projekte", "qualifikationen", "sprachen")


class PDFExportUnavailable(RuntimeError):
    """Der optionale Chromium-Export ist in der lokalen Installation nicht bereit."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _escape(value: Any) -> str:
    return html.escape(_text(value), quote=True)


def _safe_filename(value: str, fallback: str = "profil") -> str:
    value = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß._ -]+", "-", value).strip(" .-")
    return value or fallback


def _selected(profile: dict[str, Any], variant: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Liest sichtbare Variantenelemente aus dem Variantensnapshot oder Basisprofil.

    Die Reihenfolge kommt ausschließlich aus ``auswahl.<key>.reihenfolge``.
    """
    contents = variant.get("inhalte") if isinstance(variant.get("inhalte"), dict) else profile
    rows = contents.get(key, []) if isinstance(contents, dict) else []
    source = {str(row.get("id")): row for row in rows if isinstance(row, dict) and row.get("id")}
    choices = variant.get("auswahl", {}).get(key, []) if isinstance(variant.get("auswahl"), dict) else []
    visible: list[tuple[int, int, dict[str, Any]]] = []
    for index, choice in enumerate(choices):
        if not isinstance(choice, dict) or not choice.get("sichtbar", False):
            continue
        row = source.get(str(choice.get("id")))
        if row:
            order = choice.get("reihenfolge", index + 1)
            try:
                order = int(order)
            except (TypeError, ValueError):
                order = index + 1
            visible.append((order, index, row))
    return [row for _, _, row in sorted(visible, key=lambda item: (item[0], item[1]))]


def _project_period(project: dict[str, Any]) -> str:
    if _text(project.get("zeitraum")):
        return _text(project["zeitraum"])

    def month(value: Any) -> str:
        value = _text(value)
        return f"{value[5:7]}/{value[:4]}" if re.fullmatch(r"\d{4}-\d{2}", value) else value

    start = month(project.get("startMonat"))
    end = "laufend" if project.get("laufend") else month(project.get("endeMonat"))
    return " – ".join(part for part in (start, end) if part)


def profile_for_pdf(profile: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    """Uebersetzt das interne JSON-Modell in eine reine Exportansicht."""
    person = profile.get("person", {}) if isinstance(profile.get("person"), dict) else {}
    contents = variant.get("inhalte") if isinstance(variant.get("inhalte"), dict) else profile
    short = contents.get("kurzprofil", {}) if isinstance(contents.get("kurzprofil"), dict) else {}
    name = " ".join(part for part in (_text(person.get("titel")), _text(person.get("vorname")), _text(person.get("nachname"))) if part)
    role = _text(variant.get("zielrolle")) or _text(person.get("rolle"))
    bio = "\n\n".join(part for part in (_text(short.get("positionierung")), _text(short.get("zusammenfassung"))) if part)
    return {
        "name": name or "Beraterprofil",
        "rolle": role,
        "kurzprofil": bio,
        "kompetenzen": _selected(profile, variant, "kompetenzen"),
        "branchen": _selected(profile, variant, "branchen"),
        "qualifikationen": _selected(profile, variant, "qualifikationen"),
        "sprachen": _selected(profile, variant, "sprachen"),
        "projekte": _selected(profile, variant, "projekte"),
    }


def load_logo_data_url(logo_path: str | Path | None) -> str:
    if not logo_path:
        return ""
    path = Path(logo_path)
    if not path.is_file():
        return ""
    suffix = path.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}.get(suffix)
    if not mime:
        return ""
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _label(row: dict[str, Any], key: str) -> str:
    if key == "sprachen":
        return " · ".join(part for part in (_text(row.get("sprache")), _text(row.get("niveau"))) if part)
    return _text(row.get("bezeichnung")) or _text(row.get("titel"))


def _chips(rows: list[dict[str, Any]], key: str) -> str:
    return "".join(f'<span class="chip">{_escape(_label(row, key))}</span>' for row in rows if _label(row, key))


def _projects(rows: list[dict[str, Any]]) -> str:
    cards = []
    for project in rows:
        meta = " · ".join(part for part in (_text(project.get("brancheSituation")), _project_period(project), _text(project.get("rolle"))) if part)
        title = _text(project.get("titel"))
        description = _text(project.get("beschreibung"))
        tasks = _text(project.get("aufgaben"))
        extras = []
        if _text(project.get("highlights")):
            extras.append(f'<p><strong>Ergebnis:</strong> {_escape(project["highlights"])}</p>')
        if _text(project.get("technologienMethoden")):
            extras.append(f'<p><strong>Methoden:</strong> {_escape(project["technologienMethoden"])}</p>')
        cards.append(f'''<article class="project">
          <div class="project-meta">{_escape(meta)}</div>
          <h3>{_escape(title)}</h3>
          {f'<p>{_escape(description)}</p>' if description else ''}
          {f'<p><strong>Tätigkeiten:</strong> {_escape(tasks)}</p>' if tasks else ''}
          {''.join(extras)}
        </article>''')
    return "".join(cards)


def build_profile_html(profile: dict[str, Any], variant: dict[str, Any], logo_path: str | Path | None = None) -> str:
    data = profile_for_pdf(profile, variant)
    logo_url = load_logo_data_url(logo_path)
    logo = f'<img class="logo" src="{logo_url}" alt="WERK TRIFFT">' if logo_url else '<div class="wordmark">WERK <span>TRIFFT</span></div>'

    def section(title: str, content: str, class_name: str = "") -> str:
        return f'<section class="section {class_name}"><div class="section-label">{title}</div>{content}</section>' if content else ""

    competence = _chips(data["kompetenzen"], "kompetenzen")
    industries = _chips(data["branchen"], "branchen")
    qualifications = _chips(data["qualifikationen"], "qualifikationen")
    languages = _chips(data["sprachen"], "sprachen")
    profile_text = _text(data["kurzprofil"])
    generated = datetime.now().strftime("%d.%m.%Y")
    return f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><title>{_escape(data['name'])}</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: {INK}; background: white; font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt; line-height: 1.52; }}
.page {{ min-height: 297mm; padding: 12mm 16mm 14mm; }}
.header {{ display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 6mm; border-bottom: .5pt solid {LINE}; margin-bottom: 8mm; }}
.logo {{ height: 14mm; width: auto; mix-blend-mode: multiply; }}
.wordmark {{ color: {BLUE}; font-size: 14pt; font-weight: 800; letter-spacing: .12em; line-height: 1; }} .wordmark span {{ color: {ORANGE}; }}
.header-note {{ text-align: right; font-size: 7.5pt; color: {MUTED}; line-height: 1.6; }} .header-note strong {{ color: {BLUE}; }}
.profile {{ border-bottom: 1pt solid {LINE}; padding-bottom: 5mm; margin-bottom: 6mm; }}
h1 {{ color: {BLUE}; margin: 0 0 1mm; font-size: 20pt; line-height: 1.12; }} .role {{ color: {MUTED}; margin-bottom: 3mm; }}
.section {{ padding-bottom: 5mm; margin-bottom: 5mm; border-bottom: .5pt solid {LINE}; break-inside: avoid; }} .section:last-child {{ border: 0; }}
.section-label {{ color: {MUTED}; font-family: 'Courier New', monospace; font-size: 7.5pt; font-weight: bold; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 2mm; }}
.bio {{ color: #425161; white-space: pre-line; }} .chip {{ display: inline-block; background: {PAPER}; border: .5pt solid {LINE}; color: {BLUE}; border-radius: 9pt; padding: 1.1mm 2.3mm; margin: 0 1.5mm 1.5mm 0; font-size: 8.5pt; }}
.project {{ break-inside: avoid; padding: 3.5mm 0; border-top: .5pt solid #E5E7E5; }} .project:first-of-type {{ border-top: 0; padding-top: 0; }} .project-meta {{ color: {MUTED}; font-family: 'Courier New', monospace; font-size: 7.5pt; margin-bottom: 1mm; }} .project h3 {{ color: {BLUE}; font-size: 11pt; margin: 0 0 1.4mm; line-height: 1.25; }} .project p {{ margin: 0 0 1.3mm; }}
.footer {{ position: fixed; left: 16mm; right: 16mm; bottom: 7mm; display: flex; justify-content: space-between; border-top: .5pt solid {LINE}; padding-top: 2mm; color: {MUTED}; font-size: 7pt; }}
</style></head><body><main class="page"><header class="header">{logo}<div class="header-note"><strong>WERK TRIFFT</strong><br>Beraterprofil<br>Erstellt am {generated}</div></header>
<section class="profile"><h1>{_escape(data['name'])}</h1>{f'<div class="role">{_escape(data["rolle"])}</div>' if data['rolle'] else ''}</section>
{section('Kurzprofil', f'<div class="bio">{_escape(profile_text)}</div>') if profile_text else ''}
{section('Kompetenzen', competence)}{section('Branchen', industries)}{section('Qualifikationen', qualifications)}{section('Sprachen', languages)}{section('Projekterfahrung', _projects(data['projekte']), 'projects')}
<footer class="footer"><span>WERK TRIFFT · Vertraulich</span><span>{_escape(data['name'])}</span></footer></main></body></html>'''


def export_pdf(profile: dict[str, Any], variant: dict[str, Any], target: str | Path, logo_path: str | Path | None = None) -> Path:
    """Erzeugt eine A4-PDF. Playwright wird absichtlich erst hier importiert."""
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:
        raise PDFExportUnavailable("PDF-Export ist noch nicht eingerichtet. Installieren Sie optional 'playwright' und danach Chromium mit 'playwright install chromium'. Das Profilmanagement selbst läuft weiterhin ohne diese Zusatzbibliothek.") from error
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    html_document = build_profile_html(profile, variant, logo_path)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.set_content(html_document, wait_until="load")
            page.pdf(path=str(target), format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            browser.close()
    except Exception as error:
        raise PDFExportUnavailable(f"PDF-Export konnte Chromium nicht starten: {error}") from error
    return target
