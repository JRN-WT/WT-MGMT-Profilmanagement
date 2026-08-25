#!/usr/bin/env python3
"""Lokaler JSON-Server fuer WERK TRIFFT Profilmanagement. Nur Standardbibliothek."""
import argparse, copy, json, re, shutil, uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
ROOT=Path(__file__).resolve().parent
LISTS=('kompetenzen','branchen','projekte','qualifikationen','sprachen')
FIELDS=('kurzprofil',)+LISTS
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def safe(v,f='datei'): return re.sub(r'[^A-Za-z0-9._ -]+','-',str(v)).strip(' .-') or f
def slug(a,b): return re.sub(r'[^a-z0-9]+','-',(b+'-'+a).lower()).strip('-') or uuid.uuid4().hex[:8]
def cp(x): return copy.deepcopy(x)
def pick(items): return [{'id':x['id'],'sichtbar':True,'reihenfolge':i+1} for i,x in enumerate(items)]
class Store:
 def __init__(self,root):
  self.root=Path(root).resolve();self.p=self.root/'profile';self.v=self.root/'varianten';self.d=self.root/'dokumente';self.a=self.root/'archiv'
  for x in(self.p,self.v,self.d,self.a):x.mkdir(parents=True,exist_ok=True)
 def read(self,x):
  try:return json.loads(x.read_text(encoding='utf-8'))
  except (OSError,json.JSONDecodeError) as e:raise ValueError(f'JSON-Datei nicht lesbar: {x.name}') from e
 def write(self,x,data):
  x.parent.mkdir(parents=True,exist_ok=True);t=x.with_suffix(x.suffix+'.tmp');t.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(x)
 def pp(self,pid):return self.p/f'{safe(pid)}.json'
 def vf(self,pid,create=True):
  x=self.v/safe(pid)
  if create:x.mkdir(parents=True,exist_ok=True)
  return x
 def vp(self,pid,vid):return self.vf(pid)/f'{safe(vid)}.json'
 def normalize(self,items):
  out=[]
  for x in items if isinstance(items,list) else []:
   if isinstance(x,dict):
    y=cp(x);y['id']=str(y.get('id') or uuid.uuid4().hex);out.append(y)
  return out
 def content(self,p):return {k:cp(p.get(k,{} if k=='kurzprofil' else [])) for k in FIELDS}
 def hints(self,p):
  r=[];person=p.get('person',{})
  if not person.get('vorname') or not person.get('nachname'):r.append('Name unvollständig')
  for k,l in [('kurzprofil','Kurzprofil'),('kompetenzen','Kompetenzen'),('projekte','Projekterfahrung'),('qualifikationen','Qualifikationen'),('sprachen','Sprachen')]:
   if not p.get(k):r.append(l+' noch leer')
  return r
 def get(self,pid):
  x=self.pp(pid)
  if not x.exists():raise FileNotFoundError('Profil nicht gefunden')
  p=self.read(x);p.setdefault('revision',1);p['hinweise']=self.hints(p);return p
 def list(self):
  out=[]
  for x in self.p.glob('*.json'):
   p=self.read(x);a=p.get('person',{})
   out.append({'id':p['id'],'name':' '.join(filter(None,[a.get('vorname',''),a.get('nachname','')])), 'rolle':a.get('rolle',''),'status':p.get('status','Entwurf'),'aktualisiertAm':p.get('aktualisiertAm',''),'variantenAnzahl':len(list(self.vf(p['id']).glob('*.json'))),'hinweise':self.hints(p)})
  return sorted(out,key=lambda x:x['name'].casefold())
 def create(self,data,actor):
  q=data.get('person',{});a=str(q.get('vorname','')).strip();b=str(q.get('nachname','')).strip()
  if not a or not b:raise ValueError('Vorname und Nachname sind erforderlich.')
  pid=slug(a,b)
  while self.pp(pid).exists():pid+='-'+uuid.uuid4().hex[:4]
  t=now();p={'schemaVersion':'2.0','id':pid,'revision':1,'status':'Entwurf','erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'person':{'vorname':a,'nachname':b,'titel':'','rolle':str(q.get('rolle','')),'standort':'','interneEmail':'','telefon':'','foto':None},'kurzprofil':{'positionierung':'','zusammenfassung':''},'kompetenzen':[],'branchen':[],'projekte':[],'qualifikationen':[],'sprachen':[],'dokumente':[],'historie':[{'zeitpunkt':t,'aktion':'Profil angelegt','von':actor,'details':'Manuell als Entwurf angelegt.'}]};self.write(self.pp(pid),p);return self.get(pid)
 def mark(self,pid,revision,t,actor):
  for x in self.vf(pid).glob('*.json'):
   v=self.read(x)
   if not v.get('pruefungErforderlich'):v['statusVorBasisAenderung']=v.get('status','Entwurf')
   v['pruefungErforderlich']=True;v['status']='Basisprofil aktualisiert';v['basisRevisionAktuell']=revision;v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil aktualisiert','von':actor,'details':f'Basisprofil-Revision {revision} gegen Variante prüfen.'});self.write(x,v)
 def update(self,pid,data,actor):
  p=self.get(pid);before=self.content(p)
  for k in ('status','person','kurzprofil')+LISTS:
   if k in data:p[k]=data[k]
  for k in LISTS:p[k]=self.normalize(p.get(k,[]))
  if p.get('status') not in('Entwurf','Aktuell'):raise ValueError('Ungültiger Profilstatus.')
  changed=before!=self.content(p);t=now();p['aktualisiertAm']=t;p['aktualisiertVon']=actor
  if changed:p['revision']=int(p.get('revision',1))+1;detail=f'Profilinhalte aktualisiert. Revision {p["revision"]} erzeugt.'
  else:detail='Stammdaten gespeichert; Profilinhalte unverändert.'
  p.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil gespeichert','von':actor,'details':detail});self.write(self.pp(pid),p)
  if changed:self.mark(pid,p['revision'],t,actor)
  return self.get(pid)
 def migrate_legacy_variant(self,pid,v):
  if v.get('inhalte') is not None:return False
  p=self.get(pid);c=self.content(p);old=v.get('auswahl',{})
  v['schemaVersion']='2.0';v['inhalte']=c;v['basisSnapshot']=cp(c);v['basisRevisionGeprueft']=p.get('revision',1);v['basisRevisionAktuell']=p.get('revision',1)
  v['auswahl']={}
  for k in LISTS:
   prior={x.get('id'):x for x in old.get(k,[]) if x.get('id')}
   v['auswahl'][k]=[{'id':x['id'],'sichtbar':bool(prior.get(x['id'],{}).get('sichtbar',True)),'reihenfolge':i+1} for i,x in enumerate(c[k])]
  v.setdefault('historie',[]).append({'zeitpunkt':now(),'aktion':'Variante technisch aktualisiert','von':'System','details':'Bestehende Variante mit dem aktuellen Basisprofilbestand ergänzt. Inhalte bitte prüfen.'})
  return True
 def variants(self,pid):
  self.get(pid);out=[]
  for x in self.vf(pid).glob('*.json'):
   v=self.read(x)
   if self.migrate_legacy_variant(pid,v):self.write(x,v)
   out.append(v)
  return sorted(out,key=lambda x:x.get('aktualisiertAm',''),reverse=True)
 def variant(self,pid,vid):
  x=self.vp(pid,vid)
  if not x.exists():raise FileNotFoundError('Variante nicht gefunden')
  v=self.read(x)
  if self.migrate_legacy_variant(pid,v):self.write(x,v)
  return v
 def create_variant(self,pid,data,actor):
  p=self.get(pid);t=now();vid='variante-'+uuid.uuid4().hex[:10];c=self.content(p)
  v={'schemaVersion':'2.0','id':vid,'profilId':pid,'name':str(data.get('name','Neue Profilvariante')).strip() or 'Neue Profilvariante','status':'Entwurf','kunde':str(data.get('kunde','')),'anfrage':str(data.get('anfrage','')),'zielrolle':str(data.get('zielrolle',p.get('person',{}).get('rolle',''))),'notiz':str(data.get('notiz','')),'fotoSichtbar':bool(data.get('fotoSichtbar',False)),'inhalte':c,'basisSnapshot':cp(c),'basisRevisionGeprueft':p.get('revision',1),'basisRevisionAktuell':p.get('revision',1),'pruefungErforderlich':False,'auswahl':{k:pick(c[k]) for k in LISTS},'erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'historie':[{'zeitpunkt':t,'aktion':'Variante angelegt','von':actor,'details':f'Auf Basisprofil-Revision {p.get("revision",1)} angelegt.'}]};self.write(self.vp(pid,vid),v);return v
 def normvar(self,v):
  v.setdefault('inhalte',{});v.setdefault('basisSnapshot',cp(v['inhalte']))
  for k in FIELDS:
   v['inhalte'].setdefault(k,{} if k=='kurzprofil' else [])
   if k!='kurzprofil':v['inhalte'][k]=self.normalize(v['inhalte'][k])
  v.setdefault('auswahl',{})
  for k in LISTS:
   ids={x['id'] for x in v['inhalte'][k]};old={x.get('id'):x for x in v['auswahl'].get(k,[]) if x.get('id') in ids};v['auswahl'][k]=[{'id':x['id'],'sichtbar':bool(old.get(x['id'],{}).get('sichtbar',True)),'reihenfolge':i+1} for i,x in enumerate(v['inhalte'][k])]
  v.setdefault('basisRevisionGeprueft',1);v.setdefault('basisRevisionAktuell',v['basisRevisionGeprueft']);v.setdefault('pruefungErforderlich',False)
 def update_variant(self,pid,vid,data,actor):
  self.get(pid);v=self.variant(pid,vid);self.normvar(v)
  for k in ('name','kunde','anfrage','zielrolle','notiz','fotoSichtbar'):
   if k in data:v[k]=data[k]
  if 'inhalte' in data:
   for k in FIELDS:
    if k in data['inhalte']:v['inhalte'][k]=cp(data['inhalte'][k])
  if 'auswahl' in data:v['auswahl']=cp(data['auswahl'])
  self.normvar(v);want=data.get('status')
  if want=='Freigegeben' and v.get('pruefungErforderlich'):raise ValueError('Bitte zuerst die Basisänderungen prüfen, bevor Sie diese Variante freigeben.')
  if want in('Entwurf','Freigegeben'):v['status']=want
  elif v.get('pruefungErforderlich'):v['status']='Basisprofil aktualisiert'
  t=now();v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Variante freigegeben' if v['status']=='Freigegeben' else 'Variante gespeichert','von':actor,'details':'Varianteninhalt, Auswahl und Reihenfolge gespeichert.'});self.write(self.vp(pid,vid),v);return v
 def changes(self,pid,vid):
  p=self.get(pid);v=self.variant(pid,vid);self.normvar(v);old=v.get('basisSnapshot',{});r=[]
  if old.get('kurzprofil',{})!=p.get('kurzprofil',{}):r.append({'feld':'kurzprofil','id':'kurzprofil','typ':'geaendert','titel':'Kurzprofil','basis':p.get('kurzprofil',{}),'variante':v['inhalte'].get('kurzprofil',{})})
  for k in LISTS:
   before={x.get('id'):x for x in old.get(k,[]) if x.get('id')};cur={x.get('id'):x for x in p.get(k,[]) if x.get('id')}
   for ident,item in cur.items():
    typ='neu' if ident not in before else ('geaendert' if before[ident]!=item else '')
    if typ:r.append({'feld':k,'id':ident,'typ':typ,'titel':item.get('titel') or item.get('sprache') or item.get('bezeichnung') or 'Eintrag','basis':item,'variante':next((x for x in v['inhalte'].get(k,[]) if x.get('id')==ident),None)})
   for ident,item in before.items():
    if ident not in cur:r.append({'feld':k,'id':ident,'typ':'entfernt','titel':item.get('titel') or item.get('sprache') or item.get('bezeichnung') or 'Eintrag','basis':None,'variante':next((x for x in v['inhalte'].get(k,[]) if x.get('id')==ident),None)})
  return {'basisRevision':p.get('revision',1),'gepruefteBasisRevision':v.get('basisRevisionGeprueft',1),'pruefungErforderlich':bool(v.get('pruefungErforderlich')),'aenderungen':r}
 def review(self,pid,vid,data,actor):
  p=self.get(pid);v=self.variant(pid,vid);self.normvar(v);changes=self.changes(pid,vid)['aenderungen'];d={(x.get('feld'),x.get('id')):x.get('aktion','beibehalten') for x in data.get('entscheidungen',[]) if isinstance(x,dict)};taken=0
  for c in changes:
   if d.get((c['feld'],c['id']),'beibehalten')!='uebernehmen':continue
   k=c['feld'];taken+=1
   if k=='kurzprofil':v['inhalte']['kurzprofil']=cp(p.get('kurzprofil',{}));continue
   vals=v['inhalte'][k];i=next((i for i,x in enumerate(vals) if x.get('id')==c['id']),None)
   if c['typ']=='entfernt':
    if i is not None:vals.pop(i)
   elif i is None:vals.append(cp(c['basis']))
   else:vals[i]=cp(c['basis'])
  v['basisSnapshot']=self.content(p);v['basisRevisionGeprueft']=p.get('revision',1);v['basisRevisionAktuell']=p.get('revision',1);v['pruefungErforderlich']=False
  if v.get('status')=='Basisprofil aktualisiert':v['status']=v.pop('statusVorBasisAenderung','Entwurf')
  self.normvar(v);t=now();v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisänderungen geprüft','von':actor,'details':f'{len(changes)} Basisänderungen geprüft, {taken} in Variante übernommen.'});self.write(self.vp(pid,vid),v);return v
 def archive(self,pid,actor):
  p=self.get(pid);target=self.a/f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe(pid)}";target.mkdir();shutil.move(str(self.pp(pid)),str(target/'profil.json'))
  for source,name in ((self.vf(pid,False),'varianten'),(self.d/safe(pid),'dokumente')):
   if source.exists():shutil.move(str(source),str(target/name))
  self.write(target/'archiv-info.json',{'profilId':p['id'],'archiviertAm':now(),'archiviertVon':actor,'grund':'Archivierung über Profilmanagement'})
class Handler(SimpleHTTPRequestHandler):
 def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
 def do_GET(self):
  if not self.api():super().do_GET()
 def do_POST(self):self.api()
 def do_PUT(self):self.api()
 def do_DELETE(self):self.api()
 def body(self):
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))).decode() or '{}')
  except json.JSONDecodeError:raise ValueError('Ungültige JSON-Anfrage.')
 def sendjson(self,status,data):
  b=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return True
 def api(self):
  path=unquote(urlparse(self.path).path).rstrip('/') or '/'
  if not path.startswith('/api'):return False
  try:
   s=self.server.store;actor=self.headers.get('X-WT-Actor','Julius Rollmann');z=[x for x in path.split('/') if x]
   if path=='/api/health' and self.command=='GET':return self.sendjson(200,{'status':'ok','zeitpunkt':now()})
   if path=='/api/profiles':
    if self.command=='GET':return self.sendjson(200,{'profile':s.list()})
    if self.command=='POST':return self.sendjson(201,s.create(self.body(),actor))
   if len(z)>=3 and z[1]=='profiles':
    pid=z[2]
    if len(z)==3:
     if self.command=='GET':return self.sendjson(200,s.get(pid))
     if self.command=='PUT':return self.sendjson(200,s.update(pid,self.body(),actor))
     if self.command=='DELETE':s.archive(pid,actor);return self.sendjson(200,{'archiviert':True,'profilId':pid})
    if len(z)==4 and z[3]=='variants':
     if self.command=='GET':return self.sendjson(200,{'varianten':s.variants(pid)})
     if self.command=='POST':return self.sendjson(201,s.create_variant(pid,self.body(),actor))
    if len(z)==5 and z[3]=='variants':
     if self.command=='GET':return self.sendjson(200,s.variant(pid,z[4]))
     if self.command=='PUT':return self.sendjson(200,s.update_variant(pid,z[4],self.body(),actor))
    if len(z)==6 and z[3]=='variants' and z[5]=='basis-aenderungen':
     if self.command=='GET':return self.sendjson(200,s.changes(pid,z[4]))
     if self.command=='POST':return self.sendjson(200,s.review(pid,z[4],self.body(),actor))
   return self.sendjson(404,{'fehler':'API-Endpunkt nicht gefunden.'})
  except FileNotFoundError as e:return self.sendjson(404,{'fehler':str(e)})
  except ValueError as e:return self.sendjson(400,{'fehler':str(e)})
  except Exception:return self.sendjson(500,{'fehler':'Interner Serverfehler.'})
def main():
 a=argparse.ArgumentParser();a.add_argument('--host',default='127.0.0.1');a.add_argument('--port',type=int,default=8081);a.add_argument('--data-dir',type=Path,default=ROOT/'daten');x=a.parse_args();server=ThreadingHTTPServer((x.host,x.port),Handler);server.store=Store(x.data_dir);print(f'Profilmanagement: http://{x.host}:{x.port}');server.serve_forever()
if __name__=='__main__':main()
