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
def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def cp(x):return copy.deepcopy(x)
def safe(x,f='datei'):return re.sub(r'[^A-Za-z0-9._ -]+','-',str(x)).strip(' .-') or f
def slug(a,b):return re.sub(r'[^a-z0-9]+','-',(b+'-'+a).lower()).strip('-') or uuid.uuid4().hex[:8]
def pick(a,on=True):return[{'id':x['id'],'sichtbar':on,'reihenfolge':i+1}for i,x in enumerate(a)]
def project(x):
 x=x if isinstance(x,dict)else{}
 return{'id':str(x.get('id')or uuid.uuid4().hex),'titel':str(x.get('titel')or x.get('bezeichnung')or''),'startMonat':str(x.get('startMonat')or''),'endeMonat':str(x.get('endeMonat')or''),'laufend':bool(x.get('laufend',False)),'rolle':str(x.get('rolle')or''),'beschreibung':str(x.get('beschreibung')or x.get('details')or''),'aufgaben':str(x.get('aufgaben')or'')}
def valid_month(x):return bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',x or''))
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
 def norm(self,k,items):
  r=[]
  for x in items if isinstance(items,list)else[]:
   if not isinstance(x,dict):continue
   if k=='projekte':r.append(project(x));continue
   y=cp(x);y['id']=str(y.get('id')or uuid.uuid4().hex);r.append(y)
  return r
 def content(self,p):return{k:cp(p.get(k,{}if k=='kurzprofil'else[]))for k in FIELDS}
 def hints(self,p):
  r=[];person=p.get('person',{})
  if not person.get('vorname')or not person.get('nachname'):r.append('Name unvollständig')
  for k,l in(('kurzprofil','Kurzprofil'),('kompetenzen','Kompetenzen'),('projekte','Projekterfahrung'),('qualifikationen','Qualifikationen'),('sprachen','Sprachen')):
   if not p.get(k):r.append(l+' noch leer')
  return r
 def get(self,pid):
  x=self.pp(pid)
  if not x.exists():raise FileNotFoundError('Profil nicht gefunden')
  p=self.read(x);p.setdefault('revision',1)
  for k in LISTS:p[k]=self.norm(k,p.get(k,[]))
  p['hinweise']=self.hints(p);return p
 def list(self):
  r=[]
  for x in self.p.glob('*.json'):
   p=self.get(x.stem);a=p.get('person',{});r.append({'id':p['id'],'name':' '.join(filter(None,[a.get('vorname',''),a.get('nachname','')])), 'rolle':a.get('rolle',''),'status':p.get('status','Entwurf'),'aktualisiertAm':p.get('aktualisiertAm',''),'variantenAnzahl':len(list(self.vf(p['id']).glob('*.json'))),'hinweise':self.hints(p)})
  return sorted(r,key=lambda x:x['name'].casefold())
 def create(self,d,actor):
  q=d.get('person',{});a=str(q.get('vorname','')).strip();b=str(q.get('nachname','')).strip()
  if not a or not b:raise ValueError('Vorname und Nachname sind erforderlich.')
  pid=slug(a,b)
  while self.pp(pid).exists():pid+='-'+uuid.uuid4().hex[:4]
  t=now();p={'schemaVersion':'2.1','id':pid,'revision':1,'status':'Entwurf','erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'person':{'vorname':a,'nachname':b,'titel':'','rolle':str(q.get('rolle','')),'standort':'','interneEmail':'','telefon':'','foto':None},'kurzprofil':{'positionierung':'','zusammenfassung':''},'kompetenzen':[],'branchen':[],'projekte':[],'qualifikationen':[],'sprachen':[],'dokumente':[],'historie':[{'zeitpunkt':t,'aktion':'Profil angelegt','von':actor,'details':'Manuell als Entwurf angelegt.'}]};self.write(self.pp(pid),p);return self.get(pid)
 def validate_projects(self,rows):
  for n,x in enumerate(rows,1):
   miss=[]
   if not x['titel'].strip():miss.append('Titel')
   if not valid_month(x['startMonat']):miss.append('Startmonat')
   if not x['laufend']and not valid_month(x['endeMonat']):miss.append('Endmonat oder „laufend“')
   if not x['rolle'].strip():miss.append('Rolle')
   if not x['beschreibung'].strip():miss.append('Kurzbeschreibung')
   if not x['aufgaben'].strip():miss.append('Tätigkeiten')
   if miss:raise ValueError(f'Projekt {n}: '+', '.join(miss)+' ergänzen.')
   if not x['laufend']and x['endeMonat']<x['startMonat']:raise ValueError(f'Projekt {n}: Der Endmonat liegt vor dem Startmonat.')
 def normvar(self,v):
  v.setdefault('inhalte',{});v.setdefault('basisSnapshot',cp(v['inhalte']))
  for k in FIELDS:
   v['inhalte'].setdefault(k,{}if k=='kurzprofil'else[])
   if k!='kurzprofil':v['inhalte'][k]=self.norm(k,v['inhalte'][k])
  v.setdefault('auswahl',{})
  for k in LISTS:
   old={x.get('id'):x for x in v['auswahl'].get(k,[])if x.get('id')};v['auswahl'][k]=[{'id':x['id'],'sichtbar':bool(old.get(x['id'],{}).get('sichtbar',True)),'reihenfolge':old.get(x['id'],{}).get('reihenfolge',i+1)}for i,x in enumerate(v['inhalte'][k])]
  v.setdefault('basisRevisionGeprueft',1);v.setdefault('basisRevisionAktuell',v['basisRevisionGeprueft']);v.setdefault('pruefungErforderlich',False)
 def mark(self,pid,rev,t,actor):
  p=self.get(pid);content=self.content(p)
  for x in self.vf(pid).glob('*.json'):
   v=self.read(x);self.normvar(v)
   if not v.get('pruefungErforderlich'):v['statusVorBasisAenderung']=v.get('status','Entwurf')
   choices={}
   for k in LISTS:
    old={z.get('id'):z for z in v.get('auswahl',{}).get(k,[])};choices[k]=[{'id':z['id'],'sichtbar':bool(old[z['id']]['sichtbar'])if z['id']in old else False,'reihenfolge':old[z['id']].get('reihenfolge',i+1)if z['id']in old else i+1}for i,z in enumerate(content[k])]
   v['inhalte']=cp(content);v['auswahl']=choices;self.normvar(v);v['pruefungErforderlich']=True;v['status']='Prüfung erforderlich';v['basisRevisionAktuell']=rev;v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil aktualisiert','von':actor,'details':'Basisprofil geändert; Variante zur Prüfung markiert.'});self.write(x,v)
 def update(self,pid,d,actor):
  p=self.get(pid);before=self.content(p)
  for k in('status','person','kurzprofil')+LISTS:
   if k in d:p[k]=d[k]
  for k in LISTS:p[k]=self.norm(k,p.get(k,[]))
  p['projekte']=[x for x in p['projekte']if any((x['titel'].strip(),x['startMonat'],x['endeMonat'],x['laufend'],x['rolle'].strip(),x['beschreibung'].strip(),x['aufgaben'].strip()))]
  self.validate_projects(p['projekte'])
  if p.get('status')not in('Entwurf','Aktuell'):raise ValueError('Ungültiger Profilstatus.')
  changed=before!=self.content(p);t=now();p['aktualisiertAm']=t;p['aktualisiertVon']=actor;p['revision']=int(p.get('revision',1))+(1 if changed else 0);p.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil gespeichert','von':actor,'details':'Profilinhalte aktualisiert.'if changed else'Stammdaten gespeichert; Profilinhalte unverändert.'});self.write(self.pp(pid),p)
  if changed:self.mark(pid,p['revision'],t,actor)
  return self.get(pid)
 def variants(self,pid):self.get(pid);return sorted((self.read(x)for x in self.vf(pid).glob('*.json')),key=lambda x:x.get('aktualisiertAm',''),reverse=True)
 def variant(self,pid,vid):
  x=self.vp(pid,vid)
  if not x.exists():raise FileNotFoundError('Variante nicht gefunden')
  v=self.read(x);self.normvar(v);return v
 def create_variant(self,pid,d,actor):
  p=self.get(pid);t=now();vid='variante-'+uuid.uuid4().hex[:10];c=self.content(p);v={'schemaVersion':'2.1','id':vid,'profilId':pid,'name':str(d.get('name','Neue Profilvariante')).strip()or'Neue Profilvariante','status':'Entwurf','kunde':str(d.get('kunde','')),'anfrage':str(d.get('anfrage','')),'zielrolle':str(d.get('zielrolle',p.get('person',{}).get('rolle',''))),'notiz':'','fotoSichtbar':False,'inhalte':c,'basisSnapshot':cp(c),'basisRevisionGeprueft':p.get('revision',1),'basisRevisionAktuell':p.get('revision',1),'pruefungErforderlich':False,'auswahl':{k:pick(c[k])for k in LISTS},'erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'historie':[{'zeitpunkt':t,'aktion':'Variante angelegt','von':actor,'details':'Aus Basisprofil angelegt.'}]};self.write(self.vp(pid,vid),v);return v
 def update_variant(self,pid,vid,d,actor):
  self.get(pid);v=self.variant(pid,vid)
  for k in('name','kunde','anfrage','zielrolle','notiz','fotoSichtbar'):
   if k in d:v[k]=d[k]
  if'auswahl'in d:v['auswahl']=cp(d['auswahl'])
  self.normvar(v);want=d.get('status')
  if want=='Freigegeben'and v.get('pruefungErforderlich'):raise ValueError('Bitte zuerst die Basisprofil-Änderungen prüfen, bevor Sie diese Variante freigeben.')
  if want in('Entwurf','Freigegeben'):v['status']=want
  elif v.get('pruefungErforderlich'):v['status']='Prüfung erforderlich'
  t=now();v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Variante freigegeben'if v['status']=='Freigegeben'else'Variante gespeichert','von':actor,'details':'Kontext, Auswahl und Reihenfolge gespeichert.'});self.write(self.vp(pid,vid),v);return v
 def review(self,pid,vid,actor):
  p=self.get(pid);v=self.variant(pid,vid);v['inhalte']=self.content(p);v['basisSnapshot']=self.content(p);v['basisRevisionGeprueft']=p.get('revision',1);v['basisRevisionAktuell']=p.get('revision',1);v['pruefungErforderlich']=False
  if v.get('status')=='Prüfung erforderlich':v['status']=v.pop('statusVorBasisAenderung','Entwurf')
  self.normvar(v);t=now();v['aktualisiertAm']=t;v['aktualisiertVon']=actor;self.write(self.vp(pid,vid),v);return v
 def archive(self,pid,actor):
  p=self.get(pid);target=self.a/f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe(pid)}";target.mkdir();shutil.move(str(self.pp(pid)),str(target/'profil.json'))
  for source,name in((self.vf(pid,False),'varianten'),(self.d/safe(pid),'dokumente')):
   if source.exists():shutil.move(str(source),str(target/name))
  self.write(target/'archiv-info.json',{'profilId':p['id'],'archiviertAm':now(),'archiviertVon':actor})
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
