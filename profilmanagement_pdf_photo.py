"""Ergänzt den bestehenden Playwright-Export um optionale Profilfotos."""
from __future__ import annotations

from pathlib import Path
import re
import profilmanagement_pdf_playwright as base

PDFExportUnavailable = base.PDFExportUnavailable


def export_pdf(profile, variant, target, logo_path=None, photo_path=None):
    """Rendert ein Foto ausschließlich, wenn es in der Variante aktiviert wurde."""
    original = base.build_profile_html

    def with_photo(profil, variante, logo=None):
        document = original(profil, variante, logo)
        if not variante.get('fotoSichtbar') or not photo_path:
            return document
        photo = base.load_logo_data_url(photo_path)
        if not photo:
            return document
        data = base.profile_for_pdf(profil, variante)
        role = f'<div class="role">{base._escape(data["rolle"])}</div>' if data['rolle'] else ''
        replacement = (
            '<section class="profile"><div class="profile-copy">'
            f'<h1>{base._escape(data["name"])}</h1>{role}'
            f'</div><img class="profile-photo" src="{photo}" alt="Profilfoto"></section>'
        )
        document = document.replace(
            '</style>',
            '.profile{display:flex;justify-content:space-between;align-items:center;gap:6mm}'
            '.profile-copy{min-width:0}.profile-photo{width:25mm;height:25mm;border-radius:50%;'
            'object-fit:cover;border:.7pt solid #D9DDD8;flex:0 0 auto}</style>',
            1,
        )
        return re.sub(r'<section class="profile">.*?</section>', replacement, document, count=1, flags=re.S)

    base.build_profile_html = with_photo
    try:
        return base.export_pdf(profile, variant, target, logo_path)
    finally:
        base.build_profile_html = original
