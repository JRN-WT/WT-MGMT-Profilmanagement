/* Ergänzungen für die Variantenansicht: rechte Vorschau und PDF-Export. */
(() => {
  const css=`
  .variant-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(330px,430px);gap:18px;align-items:start}.variant-editor{min-width:0}.preview-panel{position:sticky;top:18px}.preview{margin:0;border:1px solid var(--l);border-radius:8px;overflow:hidden;background:#fff}.preview-person{padding:18px 20px;background:var(--n);color:#fff;border-bottom:3px solid var(--o)}.preview-person h2{font-size:22px;margin:0 0 5px}.preview-person .role,.preview-contact{color:#dce7f3;line-height:1.5}.preview-contact{font-size:12px;margin-top:8px}.preview-head{padding:16px;background:#f7f2e8;border-bottom:1px solid var(--l)}.preview-head h2{margin:0 0 4px}.preview-body{padding:20px}.preview-section{padding:13px 0;border-bottom:1px solid #e7e1d6}.preview-section:last-child{border-bottom:0}.preview-section h3{margin:0 0 8px}.preview-project{padding:12px 0;border-top:1px solid #ece6db}.preview-project:first-of-type{border-top:0}.preview-project b{color:var(--n)}.preview-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;padding:12px 16px;background:#f7f2e8;border-top:1px solid var(--l)}@media(max-width:980px){.variant-layout{grid-template-columns:1fr}.preview-panel{position:static}}`;
  document.head.insertAdjacentHTML('beforeend',`<style>${css}</style>`);
  const contact=p=>[p.standort,p.interneEmail,p.telefon].filter(Boolean).map(e).join(' · ');
  window.showPreview=function(){
    const person=profile.person||{}, name=q('#vn').value.trim()||'Unbenannte Variante', role=q('#vr').value.trim()||person.rolle||'Rolle noch ergänzen', kp=profile.kurzprofil||{}, parts=[];
    if(kp.positionierung||kp.zusammenfassung) parts.push(`<section class="preview-section"><h3>Kurzprofil</h3><b>${e(kp.positionierung||'')}</b><p>${e(kp.zusammenfassung||'')}</p></section>`);
    for(const key of ['kompetenzen','branchen','qualifikationen','sprachen']){const rows=previewRows(key);if(rows.length)parts.push(`<section class="preview-section"><h3>${labels[key]}</h3><div>${rows.map(x=>e(key==='sprachen'?x.sprache+(x.niveau?' · '+x.niveau:''):x.bezeichnung)).join(' · ')}</div></section>`)}
    const projects=previewRows('projekte');if(projects.length)parts.push(`<section class="preview-section"><h3>Projekterfahrung</h3>${projects.map(p=>`<div class="preview-project"><b>${e(p.titel)}</b><div class="meta">${e([month(p.startMonat),p.laufend?'laufend':month(p.endeMonat),p.rolle].filter(Boolean).join(' · '))}</div><p>${e(p.beschreibung)}</p><p><b>Tätigkeiten:</b> ${e(p.aufgaben)}</p></div>`).join('')}</section>`);
    q('#variant-preview').innerHTML=`<section class="preview"><div class="preview-person"><h2>${e((person.vorname||'')+' '+(person.nachname||''))}</h2><div class="role">${e(role)}</div>${contact(person)?`<div class="preview-contact">${contact(person)}</div>`:''}</div><div class="preview-head"><h2>Vorschau: ${e(name)}</h2><div class="muted">Aktuell eingeschaltete Inhalte in der gewählten Reihenfolge.</div></div><div class="preview-body">${parts.join('')||'<p class="muted">Für diese Variante sind noch keine Inhalte eingeschaltet.</p>'}</div><div class="preview-actions"><button class="button secondary" onclick="showPreview()">Vorschau aktualisieren</button><button class="button" onclick="downloadPdf()">PDF erstellen</button></div></section>`;
  };
  window.downloadPdf=async function(){
    try{await saveVariant(false);const response=await fetch('/api/profiles/'+profile.id+'/variants/'+variant.id+'/pdf',{headers:{'X-WT-Actor':actor}});if(!response.ok){const err=await response.json();throw Error(err.fehler)}const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=(q('#vn').value.trim()||'profilvariante')+'.pdf';link.click();URL.revokeObjectURL(url);say('PDF erstellt und heruntergeladen.')}catch(error){say(error.message)}
  };
  const previousVariants=window.variants;
  window.variants=async function(edit=false){
    await previousVariants(edit);
    if(!edit||!variant)return;
    const host=q('#variants'), oldPreview=q('#variant-preview');
    if(!oldPreview||host.querySelector('.variant-layout'))return;
    const save=host.querySelector('.save-bar'), sections=[...host.querySelectorAll('.section')];
    const first=sections.shift(); const editor=document.createElement('div');editor.className='variant-editor';
    if(first)editor.append(first);sections.forEach(x=>editor.append(x));if(save)editor.append(save);
    const layout=document.createElement('div');layout.className='variant-layout';layout.append(editor);
    const aside=document.createElement('aside');aside.className='preview-panel';aside.append(oldPreview);layout.append(aside);host.append(layout);showPreview();
  };
})();
