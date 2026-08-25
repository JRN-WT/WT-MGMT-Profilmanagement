/* Rechte, rein browserbasierte Variantenvorschau. Keine Zusatzbibliothek. */
(() => {
  const css = `
  .variant-workspace{display:block}.variant-editor{min-width:0}.preview-panel{display:none}.variant-workspace.preview-open{display:grid;grid-template-columns:minmax(0,1fr) minmax(350px,420px);gap:20px;align-items:start}.variant-workspace.preview-open .preview-panel{display:block;position:sticky;top:18px}.preview{margin:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff}.preview-person{padding:18px 20px;background:var(--blue);color:#fff;border-bottom:3px solid var(--orange)}.preview-person h2{font-size:22px;margin:0 0 5px}.preview-role,.preview-contact{color:#dce7f3;line-height:1.45}.preview-contact{font-size:12px;margin-top:8px}.preview-head{padding:16px;background:#f7f2e8;border-bottom:1px solid var(--line)}.preview-head h2{margin:0 0 4px}.preview-body{padding:20px}.preview-section{padding:13px 0;border-bottom:1px solid #e7e1d6}.preview-section:last-child{border-bottom:0}.preview-section h3{margin:0 0 8px}.preview-project{padding:12px 0;border-top:1px solid #ece6db}.preview-project:first-of-type{border-top:0}.preview-project b{color:var(--blue)}.preview-note{font-size:12px;color:var(--muted);line-height:1.45;margin-top:10px}@media(max-width:1050px){.variant-workspace.preview-open{grid-template-columns:1fr}.variant-workspace.preview-open .preview-panel{position:static}}`;
  document.head.insertAdjacentHTML('beforeend', `<style>${css}</style>`);

  function selectedRows(key) {
    const map = Object.fromEntries((selection()[key] || []).filter(item => item.sichtbar).map(item => [item.id, item]));
    return (profile[key] || []).filter(item => map[item.id]).sort((a, b) => map[a.id].reihenfolge - map[b.id].reihenfolge);
  }
  function contacts(person) {
    return [person.standort, person.interneEmail, person.telefon].filter(Boolean).map(e).join(' · ');
  }
  function ensureRightPanel() {
    let panel = q('#variant-preview-panel');
    if (panel) return panel;
    const preview = q('#variant-preview');
    const host = q('#variants');
    const start = host.querySelector('.section');
    const end = host.querySelector('.save-bar');
    if (!preview || !start || !end) throw Error('Die Variantenansicht ist noch nicht vollständig aufgebaut. Bitte die Variante einmal neu öffnen.');
    const workspace = document.createElement('div');
    workspace.id = 'variant-workspace'; workspace.className = 'variant-workspace';
    const editor = document.createElement('div'); editor.className = 'variant-editor';
    const panelElement = document.createElement('aside'); panelElement.id = 'variant-preview-panel'; panelElement.className = 'preview-panel';
    start.parentElement.insertBefore(workspace, start);
    let node = start;
    while (node) {
      const next = node.nextElementSibling;
      editor.append(node);
      if (node === end) break;
      node = next;
    }
    panelElement.append(preview); workspace.append(editor, panelElement);
    return panelElement;
  }
  window.showPreview = function () {
    try {
      ensureRightPanel();
      q('#variant-workspace').classList.add('preview-open');
      const person = profile.person || {};
      const name = q('#vn').value.trim() || 'Unbenannte Variante';
      const role = q('#vr').value.trim() || person.rolle || 'Rolle noch ergänzen';
      const short = profile.kurzprofil || {}, sections = [];
      if (short.positionierung || short.zusammenfassung) sections.push(`<section class="preview-section"><h3>Kurzprofil</h3><b>${e(short.positionierung || '')}</b><p>${e(short.zusammenfassung || '')}</p></section>`);
      for (const key of ['kompetenzen', 'branchen', 'qualifikationen', 'sprachen']) {
        const rows = selectedRows(key);
        if (rows.length) sections.push(`<section class="preview-section"><h3>${labels[key]}</h3><div>${rows.map(row => e(key === 'sprachen' ? row.sprache + (row.niveau ? ' · ' + row.niveau : '') : row.bezeichnung)).join(' · ')}</div></section>`);
      }
      const projects = selectedRows('projekte');
      if (projects.length) sections.push(`<section class="preview-section"><h3>Projekterfahrung</h3>${projects.map(project => `<div class="preview-project"><b>${e(project.titel)}</b><div class="meta">${e([month(project.startMonat), project.laufend ? 'laufend' : month(project.endeMonat), project.rolle].filter(Boolean).join(' · '))}</div><p>${e(project.beschreibung)}</p><p><b>Tätigkeiten:</b> ${e(project.aufgaben)}</p></div>`).join('')}</section>`);
      q('#variant-preview').innerHTML = `<section class="preview"><div class="preview-person"><h2>${e([person.vorname, person.nachname].filter(Boolean).join(' ') || 'Name noch ergänzen')}</h2><div class="preview-role">${e(role)}</div>${contacts(person) ? `<div class="preview-contact">${contacts(person)}</div>` : ''}</div><div class="preview-head"><h2>Vorschau: ${e(name)}</h2><div class="muted">Alle aktivierten Inhalte in der gewählten Reihenfolge.</div><div class="preview-note">Diese Ansicht ist die Grundlage für den PDF-Export.</div></div><div class="preview-body">${sections.join('') || '<p class="muted">Für diese Variante sind noch keine Inhalte eingeschaltet.</p>'}</div></section>`;
    } catch (error) { say(error.message); }
  };

  // Die Hauptoberfläche baut den Varianteneditor dynamisch auf. Diese Überwachung
  // macht die Vorschau deshalb zu einem festen Teil des Editors statt zu einer Aktion.
  const variantsHost = q('#variants');
  new MutationObserver(() => {
    const previewButton = variantsHost.querySelector('.save-bar .button.secondary[onclick*="showPreview"]');
    if (!previewButton || !q('#vn') || !q('#variant-preview')) return;
    previewButton.remove();
    window.showPreview();
  }).observe(variantsHost, { childList: true, subtree: true });
})();
