/* Profilfoto: kompakter lokaler Upload im Basisprofil, sichtbar je Variante. */
(() => {
  const css=`
    .profile-photo-box{display:flex;align-items:center;gap:16px;flex-wrap:wrap}.base-photo{width:82px;height:82px;border:1px solid var(--line);border-radius:50%;object-fit:cover;background:#e6ecf5}.photo-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.photo-note{font-size:12px;color:var(--muted);line-height:1.45;max-width:560px}.variant-photo-toggle{padding-top:4px}
  `; document.head.insertAdjacentHTML('beforeend',`<style>${css}</style>`);
  const imageUrl=()=>profile&&profile.person&&profile.person.foto&&profile.person.foto.url;
  const photoMarkup=()=>imageUrl()?`<img class="base-photo" src="${e(imageUrl())}" alt="Aktuelles Profilfoto">`:`<div class="avatar" style="width:82px;height:82px;font-size:20px">${e(((profile.person.vorname||'')[0]||'')+((profile.person.nachname||'')[0]||'')).toUpperCase()||'–'}</div>`;
  const originalRenderBase=window.renderBase;
  window.renderBase=function(){
    originalRenderBase();
    const head=q('#base > .row'); if(!head)return;
    const section=document.createElement('section'); section.className='section'; section.id='profile-photo-section';
    section.innerHTML=`<h3>Profilfoto</h3><div class="profile-photo-box"><div id="base-photo-current">${photoMarkup()}</div><div><div class="photo-actions"><label class="button secondary" for="profile-photo-input">Foto auswählen</label><input id="profile-photo-input" type="file" accept="image/jpeg,image/png" hidden onchange="uploadProfilePhoto(this)">${imageUrl()?'<button class="remove" type="button" onclick="removeProfilePhoto()">Foto entfernen</button>':''}</div><p class="photo-note">Das Bild wird vor dem Speichern auf maximal 640 × 640 Pixel verkleinert und als kompaktes JPG abgelegt. Es bleibt zunächst nur im Basisprofil; in Varianten schaltest du es gezielt für die Ausgabe ein.</p></div></div>`;
    head.insertAdjacentElement('afterend',section);
  };
  window.uploadProfilePhoto=async function(input){
    const file=input.files&&input.files[0]; if(!file)return;
    if(!['image/jpeg','image/png'].includes(file.type)){say('Bitte ein JPG- oder PNG-Bild auswählen.');input.value='';return}
    if(file.size>12*1024*1024){say('Das Ausgangsbild ist zu groß. Bitte eine Datei unter 12 MB auswählen.');input.value='';return}
    try{const dataUrl=await compactPhoto(file);profile=await api('/profiles/'+profile.id+'/photo','POST',{dataUrl});updatePhotoUI();say('Profilfoto gespeichert.');}catch(error){say(error.message||'Das Profilfoto konnte nicht gespeichert werden.')}finally{input.value=''}
  };
  function compactPhoto(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(Error('Die Bilddatei konnte nicht gelesen werden.'));reader.onload=()=>{const image=new Image();image.onerror=()=>reject(Error('Die Bilddatei ist nicht lesbar.'));image.onload=()=>{const max=640,ratio=Math.min(1,max/image.width,max/image.height),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.width*ratio));canvas.height=Math.max(1,Math.round(image.height*ratio));const ctx=canvas.getContext('2d');ctx.fillStyle='#ffffff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);let result=canvas.toDataURL('image/jpeg',.84);if(result.length>1_100_000)result=canvas.toDataURL('image/jpeg',.70);resolve(result)};image.src=reader.result};reader.readAsDataURL(file)})}
  function updatePhotoUI(){const target=q('#base-photo-current');if(target)target.innerHTML=photoMarkup();const initials=q('#initials');if(initials&&imageUrl())initials.innerHTML=`<img class="base-photo" style="width:60px;height:60px;border:0" src="${e(imageUrl())}" alt="Profilfoto">`;if(variant)showPreview();}
  window.removeProfilePhoto=async function(){if(!confirm('Profilfoto entfernen? Bereits gespeicherte Varianten behalten nur die Einstellung, aber zeigen danach kein Bild mehr.'))return;try{profile=await api('/profiles/'+profile.id+'/photo','DELETE');renderBase();if(variant)showPreview();say('Profilfoto entfernt.')}catch(error){say(error.message)}};
  const originalVariants=window.variants;
  window.variants=async function(edit=false){
    await originalVariants(edit);
    if(!edit||!variant)return;
    const context=q('.variant-editor .section'); if(!context||context.querySelector('.variant-photo-toggle'))return;
    const fields=context.querySelector('.fields'); if(!fields)return;
    const available=!!imageUrl(); const row=document.createElement('div');row.className='field wide variant-photo-toggle';
    row.innerHTML=available?`<label class="check"><input type="checkbox" ${variant.fotoSichtbar?'checked':''} onchange="photoVisibilityChanged(this)"> Profilfoto in dieser Variante anzeigen</label><div class="photo-note">Die Einstellung gilt nur für diese Variante und wird später auch vom PDF-Export verwendet.</div>`:`<div class="photo-note">Für diese Variante ist noch kein Profilfoto verfügbar. Ein Foto kann im Basisprofil hinterlegt werden.</div>`;
    fields.append(row); if(available)showPreview();
  };
  window.photoVisibilityChanged=function(box){variant.fotoSichtbar=box.checked;variantChanged();showPreview();};
  window.saveVariant=async function(freigeben){
    try{variant=await api('/profiles/'+profile.id+'/variants/'+variant.id,'PUT',{name:q('#vn').value.trim()||'Unbenannte Variante',zielrolle:q('#vr').value.trim(),kunde:q('#vk').value.trim(),anfrage:q('#va').value.trim(),auswahl:selection(),fotoSichtbar:!!variant.fotoSichtbar,status:freigeben?'Freigegeben':'Entwurf'});variants(true);load();say(freigeben?'Variante gespeichert und freigegeben.':'Variante gespeichert.')}catch(error){say(error.message)}
  };
})();
