(() => {
  const css = `
  .variant-workspace{display:grid;grid-template-columns:minmax(0,1fr) minmax(350px,420px);gap:20px;align-items:start}.variant-editor{min-width:0}.preview-panel{display:block;position:sticky;top:18px}.preview{margin:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff}.preview-variant{padding:10px 20px;background:#f7f2e8;border-bottom:1px solid var(--line);color:var(--blue);font:11px monospace;letter-spacing:.08em;text-transform:uppercase}.preview-person{padding:18px 20px;background:var(--blue);color:#fff;border-bottom:3px solid var(--orange)}.preview-person h2{font-size:22px;margin:0 0 5px}.preview-role,.preview-contact{color:#dce7f3;line-height:1.45}.preview-contact{font-size:12px;margin-top:8px}.preview-head{padding:16px;background:#f7f2e8;border-bottom:1px solid var(--line)}.preview-head h2{margin:0 0 4px}.preview-body{padding:20px}.preview-section{padding:13px 0;border-bottom:1px solid #e7e1d6}.preview-section:last-child{border-bottom:0}.preview-section h3{margin:0 0 8px}.preview-project{padding:12px 0;border-top:1px solid #ece6db}.preview-project:first-of-type{border-top:0}.preview-project b{color:var(--blue)}.preview-note{font-size:12px;color:var(--muted);line-height:1.45;margin-top:10px}.preview-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:16px;padding-top:14px;border-top:1px solid #e7e1d6}.preview-export-status{font-size:12px;color:var(--muted)}.section>h3{font-family:Arial,sans-serif;font-size:13px;font-weight:700;letter-spacing:.03em;color:var(--blue)}.profile-index{display:flex;flex-wrap:wrap;gap:5px;padding:12px 18px;border-bottom:1px solid var(--line);background:#f7f2e8}.profile-index button{min-width:26px;height:27px;padding:0 6px;border:1px solid transparent;border-radius:4px;background:transparent;color:var(--blue);font-size:12px;font-weight:700;cursor:pointer}.profile-index button:hover,.profile-index button.active{background:#fff;color:var(--orange);border-color:var(--line)}.profile-index button:disabled{color:#aeb8c4;cursor:default}.profile-index button:disabled:hover{background:transparent;border-color:transparent;color:#aeb8c4}@media(max-width:1050px){.variant-workspace{grid-template-columns:1fr}.preview-panel{position:static}}
  `;
  document.head.insertAdjacentHTML('beforeend', `<style>${css}</style>`);
  function selectedRows(key) { const map=Object.fromEntries((selection()[key]||[]).filter(item=>item.sichtbar).map(item=>[item.id,item])); return (profile[key]||[]).filter(item=>map[item.id]).sort((a,b)=>map[a.id].reihenfolge-map[b.id].reihenfolge); }
  function contacts(person) { return [person.standort,person.interneEmail,person.telefon].filter(Boolean).map(e).join(' · '); }
  function ensureRightPanel() {
    let panel=q('#variant-preview-panel'); if(panel) return panel;
    const preview=q('#variant-preview'), host=q('#variants'), start=host.querySelector('.section'), end=host.querySelector('.save-bar');
    if(!preview||!start||!end) throw Error('Die Variantenansicht ist noch nicht vollständig aufgebaut. Bitte die Variante einmal neu öffnen.');
    const workspace=document.createElement('div'), editor=document.createElement('div'); workspace.id='variant-workspace'; workspace.className='variant-workspace'; editor.className='variant-editor';
    panel=document.createElement('aside'); panel.id='variant-preview-panel'; panel.className='preview-panel'; start.parentElement.insertBefore(workspace,start);
    let node=start; while(node){const next=node.nextElementSibling; editor.append(node); if(node===end) break; node=next;}
    panel.append(preview); workspace.append(editor,panel); return panel;
  }
  window.showPreview=function(){
    try {
      ensureRightPanel(); const person=profile.person||{}, name=q('#vn').value.trim()||'Unbenannte Variante', role=q('#vr').value.trim()||person.rolle||'Rolle noch ergänzen', short=profile.kurzprofil||{}, sections=[];
      if(short.positionierung||short.zusammenfassung) sections.push(`<section class="preview-section"><h3>Kurzprofil</h3><b>${e(short.positionierung||'')}</b><p>${e(short.zusammenfassung||'')}</p></section>`);
      for(const key of ['kompetenzen','branchen','qualifikationen','sprachen']){const rows=selectedRows(key);if(rows.length)sections.push(`<section class="preview-section"><h3>${labels[key]}</h3><div>${rows.map(row=>e(key==='sprachen'?row.sprache+(row.niveau?' · '+row.niveau:''):row.bezeichnung)).join(' · ')}</div></section>`);}
      const projects=selectedRows('projekte'); if(projects.length)sections.push(`<section class="preview-section"><h3>Projekterfahrung</h3>${projects.map(project=>`<div class="preview-project"><b>${e(project.titel)}</b><div class="meta">${e([month(project.startMonat),project.laufend?'laufend':month(project.endeMonat),project.rolle].filter(Boolean).join(' · '))}</div><p>${e(project.beschreibung)}</p><p><b>Tätigkeiten:</b> ${e(project.aufgaben)}</p></div>`).join('')}</section>`);
      q('#variant-preview').innerHTML=`<section class="preview"><div class="preview-variant">Vorschau: ${e(name)}</div><div class="preview-person"><h2>${e([person.vorname,person.nachname].filter(Boolean).join(' ')||'Name noch ergänzen')}</h2><div class="preview-role">${e(role)}</div>${contacts(person)?`<div class="preview-contact">${contacts(person)}</div>`:''}</div><div class="preview-head"><h2>Vorschau</h2><div class="muted">Alle aktivierten Inhalte in der gewählten Reihenfolge.</div><div class="preview-note">Diese Ansicht ist die Grundlage für den PDF-Export.</div></div><div class="preview-body">${sections.join('')||'<p class="muted">Für diese Variante sind noch keine Inhalte eingeschaltet.</p>'}<div class="preview-actions"><button id="preview-pdf-button" class="button" type="button" onclick="exportVariantPdf()">PDF aus dieser Vorschau erstellen</button><span id="preview-export-status" class="preview-export-status" aria-live="polite"></span></div></div></section>`;
    } catch(error){say(error.message);}
  };
  window.exportVariantPdf=async function(){const button=q('#preview-pdf-button'),status=q('#preview-export-status');if(!button||!profile||!variant)return;button.disabled=true;if(status)status.textContent='PDF wird erstellt ...';try{const response=await fetch(`/api/profiles/${encodeURIComponent(profile.id)}/variants/${encodeURIComponent(variant.id)}/pdf`,{method:'POST',headers:{'Content-Type':'application/json','X-WT-Actor':actor},body:JSON.stringify({name:q('#vn').value.trim()||'Unbenannte Variante',zielrolle:q('#vr').value.trim()||profile.person.rolle||'',kunde:q('#vk').value.trim(),anfrage:q('#va').value.trim(),auswahl:selection()})});if(!response.ok){let message='Die PDF konnte nicht erstellt werden.';try{message=(await response.json()).fehler||message;}catch(_){}throw Error(message);}const blob=await response.blob(),match=(response.headers.get('Content-Disposition')||'').match(/filename="([^"]+)"/i),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=match?match[1]:'beraterprofil.pdf';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);if(status)status.textContent='PDF erstellt.';say('PDF aus der aktuellen Vorschau erstellt.');}catch(error){if(status)status.textContent='Export fehlgeschlagen.';say(error.message||'Die PDF konnte nicht erstellt werden.');}finally{button.disabled=false;}};
  const originalVariants=window.variants; window.variants=async function(edit=false){await originalVariants(edit);if(!edit||!variant)return;qa('button',q('#variants')).filter(button=>button.textContent.trim()==='Vorschau anzeigen').forEach(button=>button.remove());window.showPreview();};

  // Alphabetische Filterung der Profilakten nach Nachname.
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  let activeLetter = 'Alle';
  const surnameLetter = row => {
    const name = row.querySelector('.name')?.textContent.trim() || '';
    const surname = name.split(/\s+/).pop() || '';
    return surname.normalize('NFD').replace(/[\u0300-\u036f]/g, '').charAt(0).toUpperCase();
  };
  const applyProfileFilter = letter => {
    activeLetter = letter;
    const rows = qa('#profiles .profile');
    rows.forEach(row => { row.hidden = letter !== 'Alle' && surnameLetter(row) !== letter; });
    qa('.profile-index button').forEach(button => button.classList.toggle('active', button.dataset.letter === letter));
    const total = rows.length;
    const visible = rows.filter(row => !row.hidden).length;
    const footer = q('#footer');
    if (footer) footer.textContent = letter === 'Alle' ? `${total} Profilakte${total === 1 ? '' : 'n'}` : `${visible} von ${total} Profilakte${total === 1 ? '' : 'n'}`;
  };
  const renderProfileIndex = () => {
    const profiles = q('#profiles');
    if (!profiles || q('#profile-index')) return;
    const card = profiles.parentElement;
    const rows = qa('.profile', profiles);
    if (!card || !rows.length) return;
    const available = new Set(rows.map(surnameLetter));
    const index = document.createElement('nav');
    index.id = 'profile-index';
    index.className = 'profile-index';
    index.setAttribute('aria-label', 'Profile nach Nachname filtern');
    index.innerHTML = `<button type="button" class="active" data-letter="Alle">Alle</button>${alphabet.map(letter => `<button type="button" data-letter="${letter}" ${available.has(letter) ? '' : 'disabled'}>${letter}</button>`).join('')}`;
    index.addEventListener('click', event => {
      const button = event.target.closest('button[data-letter]');
      if (button && !button.disabled) applyProfileFilter(button.dataset.letter);
    });
    card.insertBefore(index, profiles);
  };
  const profileList = q('#profiles');
  if (profileList) {
    new MutationObserver(() => {
      if (q('#profile-index')) applyProfileFilter(activeLetter);
      else renderProfileIndex();
    }).observe(profileList, { childList: true });
    renderProfileIndex();
  }
})();