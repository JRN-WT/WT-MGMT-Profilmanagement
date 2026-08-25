#!/usr/bin/env python3
"""Lokaler JSON-Server fuer WERK TRIFFT Profilmanagement. Nur Standardbibliothek."""
import argparse,json,re,shutil,uuid
from datetime import datetime,timezone
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlparse
ROOT=Path(__file__).resolve().parent
LISTS=('kompetenzen','branchen','projekte','qualifikationen','sprachen')
def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def safe(v,f='datei'):return re.sub(r'[^A-Za-z0-9._ -]+','-',str(v)).strip(' .-') or f
def slug(a,b):return re.sub(r'[^a-z0-9]+','-',(b+'-'+a).lower()).strip('-') or uuid.uuid4().hex[:8]
def clone(x):return json.loads(json.dumps(x,ensure_ascii=False))
def norm(items):
 r=[]
 for x in items if isinstance(items,list) else []:
  if isinstance(x,dict):
   y=clone(x);y['id']=str(y.get('id') or uuid.uuid4().hex);r.append(y)
 return r
class Store:
 def __init__(self,root):
  self.root=Path(root).resolve();self.p=self.root/'profile';self.v=self.root/'varianten';self.d=self.root/'dokumente';self.a=self.root/'archiv'
  for x in(self.p,self.v,self.d,self.a):x.mkdir(parents=True,exist_ok=True)
 def read(self,x):
  try:return json.loads(x.read_text(encoding='utf-8'))
  except(OSError,json.JSONDecodeError)as e:raise ValueError(f'JSON-Datei nicht lesbar: {x.name}')from e
 def write(self,x,d):
  x.parent.mkdir(parents=True,exist_ok=True);t=x.with_suffix(x.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(x)
 def pp(self,pid):return self.p/f'{safe(pid)}.json'
 def vf(self,pid,create=True):
  x=self.v/safe(pid)
  if create:x.mkdir(parents=True,exist_ok=True)
  return x
 def vp(self,pid,vid):return self.vf(pid)/f'{safe(vid)}.json'
 def hints(self,p):
  r=[]
  if not p.get('person',{}).get('vorname')or not p.get('person',{}).get('nachname'):r.append('Name unvollständig')
  for k,l in(('kurzprofil','Kurzprofil'),('kompetenzen','Kompetenzen'),('projekte','Projekterfahrung'),('qualifikationen','Qualifikationen'),('sprachen','Sprachen')):
   if not p.get(k):r.append(l+' noch leer')
  return r
 def get(self,pid):
  x=self.pp(pid)
  if not x.exists():raise FileNotFoundError('Profil nicht gefunden')
  p=self.read(x);p.setdefault('revision',1);p['hinweise']=self.hints(p);return p
 def list(self):
  r=[]
  for x in self.p.glob('*.json'):
   p=self.read(x);a=p.get('person',{});r.append({'id':p['id'],'name':' '.join(filter(None,[a.get('vorname',''),a.get('nachname','')])), 'rolle':a.get('rolle',''),'status':p.get('status','Entwurf'),'aktualisiertAm':p.get('aktualisiertAm',''),'variantenAnzahl':len(list(self.vf(p['id']).glob('*.json'))),'hinweise':self.hints(p)})
  return sorted(r,key=lambda x:x['name'].casefold())
 def create(self,d,actor):
  q=d.get('person',{});a=str(q.get('vorname','')).strip();b=str(q.get('nachname','')).strip()
  if not a or not b:raise ValueError('Vorname und Nachname sind erforderlich.')
  pid=slug(a,b)
  while self.pp(pid).exists():pid+='-'+uuid.uuid4().hex[:4]
  t=now();p={'schemaVersion':'3.0','id':pid,'revision':1,'status':'Entwurf','erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'person':{'vorname':a,'nachname':b,'titel':'','rolle':str(q.get('rolle','')),'standort':'','interneEmail':'','telefon':'','foto':None},'kurzprofil':{'positionierung':'','zusammenfassung':''},'kompetenzen':[],'branchen':[],'projekte':[],'qualifikationen':[],'sprachen':[],'dokumente':[],'historie':[{'zeitpunkt':t,'aktion':'Profil angelegt','von':actor,'details':'Manuell als Entwurf angelegt.'}]};self.write(self.pp(pid),p);return self.get(pid)
 def mark(self,pid,revision,t,actor):
  for x in self.vf(pid).glob('*.json'):
   v=self.read(x)
   if not v.get('pruefungErforderlich'):v['statusVorBasisAenderung']=v.get('status','Entwurf')
   v['pruefungErforderlich']=True;v['status']='Basisprofil aktualisiert';v['basisRevisionAktuell']=revision;v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil aktualisiert','von':actor,'details':f'Basisprofil-Revision {revision} prüfen.'});self.write(x,v)
 def update(self,pid,d,actor):
  p=self.get(pid);old={k:clone(p.get(k,{}if k=='kurzprofil' else[]))for k in('kurzprofil',)+LISTS}
  for k in('status','person','kurzprofil')+LISTS:
   if k in d:p[k]=d[k]
  for k in LISTS:p[k]=norm(p.get(k,[]))
  if p.get('status')not in('Entwurf','Aktuell'):raise ValueError('Ungültiger Profilstatus.')
  changed=old!={k:p.get(k,{}if k=='kurzprofil' else[])for k in('kurzprofil',)+LISTS};t=now();p['aktualisiertAm']=t;p['aktualisiertVon']=actor
  if changed:p['revision']=int(p.get('revision',1))+1
  p.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil gespeichert','von':actor,'details':f'Basisprofil-Revision {p.get("revision",1)} gespeichert.'});self.write(self.pp(pid),p)
  if changed:self.mark(pid,p['revision'],t,actor)
  return self.get(pid)
 def full(self,p,old,new=False):
  out={}
  for k in LISTS:
   prior={x.get('id'):x for x in old.get(k,[])if isinstance(x,dict)and x.get('id')};rows=[]
   for i,x in enumerate(p.get(k,[])):
    q=prior.get(x['id']);rows.append({'id':x['id'],'sichtbar':bool(q.get('sichtbar'))if q else new,'reihenfolge':int(q.get('reihenfolge',i+1))if q else i+1})
   rows.sort(key=lambda x:x['reihenfolge'])
   for i,x in enumerate(rows):x['reihenfolge']=i+1
   out[k]=rows
  return out
 def migrate(self,pid,v):
  p=self.get(pid);legacy=not v.get('selectionModel');old=v.get('auswahl',{})if isinstance(v.get('auswahl'),dict)else{};sel=self.full(p,old,False if legacy else False);changed=v.get('auswahl')!=sel;v['auswahl']=sel
  if v.get('inhalte')is not None:v.pop('inhalte',None);changed=True
  if v.get('basisSnapshot')is not None:v.pop('basisSnapshot',None);changed=True
  if legacy:
   v['schemaVersion']='3.0';v['selectionModel']='basisprofil';v.setdefault('basisRevisionGeprueft',p.get('revision',1));v.setdefault('basisRevisionAktuell',p.get('revision',1));v.setdefault('pruefungErforderlich',True);v.setdefault('statusVorBasisAenderung',v.get('status','Entwurf'));v['status']='Basisprofil aktualisiert';v.setdefault('historie',[]).append({'zeitpunkt':now(),'aktion':'Variante technisch aktualisiert','von':'System','details':'Variante verwendet jetzt Basisprofil, Schalter und Reihenfolge. Neue oder zuvor nicht gespeicherte Einträge sind ausgeschaltet.'});changed=True
  return changed
 def variants(self,pid):
  self.get(pid);out=[]
  for x in self.vf(pid).glob('*.json'):
   v=self.read(x)
   if self.migrate(pid,v):self.write(x,v)
   out.append(v)
  return sorted(out,key=lambda x:x.get('aktualisiertAm',''),reverse=True)
 def variant(self,pid,vid):
  x=self.vp(pid,vid)
  if not x.exists():raise FileNotFoundError('Variante nicht gefunden')
  v=self.read(x)
  if self.migrate(pid,v):self.write(x,v)
  return v
 def create_variant(self,pid,d,actor):
  p=self.get(pid);t=now();vid='variante-'+uuid.uuid4().hex[:10];v={'schemaVersion':'3.0','selectionModel':'basisprofil','id':vid,'profilId':pid,'name':str(d.get('name','Neue Profilvariante')).strip()or'Neue Profilvariante','status':'Entwurf','kunde':str(d.get('kunde','')),'anfrage':str(d.get('anfrage','')),'zielrolle':str(d.get('zielrolle',p.get('person',{}).get('rolle',''))),'notiz':str(d.get('notiz','')),'fotoSichtbar':False,'auswahl':self.full(p,{},True),'basisRevisionGeprueft':p.get('revision',1),'basisRevisionAktuell':p.get('revision',1),'pruefungErforderlich':False,'erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'historie':[{'zeitpunkt':t,'aktion':'Variante angelegt','von':actor,'details':f'Auf Basisprofil-Revision {p.get("revision",1)} angelegt.'}]};self.write(self.vp(pid,vid),v);return v
 def update_variant(self,pid,vid,d,actor):
  p=self.get(pid);v=self.variant(pid,vid)
  for k in('name','kunde','anfrage','zielrolle','notiz','fotoSichtbar'):
   if k in d:v[k]=d[k]
  if 'auswahl'in d:v['auswahl']=self.full(p,d['auswahl']if isinstance(d['auswahl'],dict)else{},False)
  want=d.get('status')
  if want=='Freigegeben'and v.get('pruefungErforderlich'):raise ValueError('Bitte zuerst die Basisprofil-Änderungen prüfen, bevor Sie diese Variante freigeben.')
  if want in('Entwurf','Freigegeben'):v['status']=want
  t=now();v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Variante freigegeben'if v['status']=='Freigegeben'else'Variantensteuerung gespeichert','von':actor,'details':'Sichtbarkeit und Priorisierung gespeichert.'});self.write(self.vp(pid,vid),v);return v
 def review(self,pid,vid,actor):
  p=self.get(pid);v=self.variant(pid,vid);v['basisRevisionGeprueft']=p.get('revision',1);v['basisRevisionAktuell']=p.get('revision',1);v['pruefungErforderlich']=False
  if v.get('status')=='Basisprofil aktualisiert':v['status']=v.pop('statusVorBasisAenderung','Entwurf')
  t=now();v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil-Änderungen geprüft','von':actor,'details':'Sichtbarkeit und Reihenfolge wurden geprüft.'});self.write(self.vp(pid,vid),v);return v
 def archive(self,pid,actor):
  p=self.get(pid);target=self.a/f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe(pid)}";target.mkdir();shutil.move(str(self.pp(pid)),str(target/'profil.json'))
  for source,name in((self.vf(pid,False),'varianten'),(self.d/safe(pid),'dokumente')):
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
  try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))).decode()or'{}')
  except json.JSONDecodeError:raise ValueError('Ungültige JSON-Anfrage.')
 def sendjson(self,status,d):
  b=json.dumps(d,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return True
 def api(self):
  path=unquote(urlparse(self.path).path).rstrip('/')or'/'
  if not path.startswith('/api'):return False
  try:
   s=self.server.store;actor=self.headers.get('X-WT-Actor','Julius Rollmann');z=[x for x in path.split('/')if x]
   if path=='/api/health'and self.command=='GET':return self.sendjson(200,{'status':'ok','zeitpunkt':now()})
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
    if len(z)==6 and z[3]=='variants'and z[5]=='basis-aenderungen'and self.command=='POST':return self.sendjson(200,s.review(pid,z[4],actor))
   return self.sendjson(404,{'fehler':'API-Endpunkt nicht gefunden.'})
  except FileNotFoundError as e:return self.sendjson(404,{'fehler':str(e)})
  except ValueError as e:return self.sendjson(400,{'fehler':str(e)})
  except Exception:return self.sendjson(500,{'fehler':'Interner Serverfehler.'})
def main():
 a=argparse.ArgumentParser();a.add_argument('--host',default='127.0.0.1');a.add_argument('--port',type=int,default=8081);a.add_argument('--data-dir',type=Path,default=ROOT/'daten');x=a.parse_args();server=ThreadingHTTPServer((x.host,x.port),Handler);server.store=Store(x.data_dir);print(f'Profilmanagement: http://{x.host}:{x.port}');server.serve_forever()
if __name__=='__main__':main()
