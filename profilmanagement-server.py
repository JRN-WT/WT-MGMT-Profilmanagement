#!/usr/bin/env python3
"""Lokaler JSON-Server fuer WERK TRIFFT Profilmanagement.
Nur Python-Standardbibliothek. Start: python profilmanagement-server.py
"""
import argparse, json, re, shutil, uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def safe(s, fallback='datei'):
    return re.sub(r'[^A-Za-z0-9ÄÖÜäöüß._ -]+','-',str(s)).strip(' .-') or fallback
def slug(first,last):
    s=(last+'-'+first).lower().translate(str.maketrans({'ä':'ae','ö':'oe','ü':'ue','ß':'ss'}))
    return re.sub(r'[^a-z0-9]+','-',s).strip('-') or uuid.uuid4().hex[:8]

class Store:
    def __init__(self, root):
        self.root=Path(root).resolve(); self.p=self.root/'profile'; self.v=self.root/'varianten'; self.d=self.root/'dokumente'; self.a=self.root/'archiv'
        for x in (self.p,self.v,self.d,self.a): x.mkdir(parents=True,exist_ok=True)
    def read(self,path):
        try: return json.loads(path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError) as e: raise ValueError(f'JSON-Datei nicht lesbar: {path.name}') from e
    def write(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); tmp.replace(path)
    def pp(self,id): return self.p/f'{safe(id)}.json'
    def vf(self,id,create=True):
        x=self.v/safe(id)
        if create:x.mkdir(parents=True,exist_ok=True)
        return x
    def vp(self,pid,vid): return self.vf(pid)/f'{safe(vid)}.json'
    def hints(self,p):
        r=[]
        if not p.get('person',{}).get('vorname') or not p.get('person',{}).get('nachname'):r.append('Name unvollständig')
        for k,l in [('kurzprofil','Kurzprofil'),('kompetenzen','Kompetenzen'),('projekte','Projekterfahrung'),('qualifikationen','Qualifikationen'),('sprachen','Sprachen')]:
            if not p.get(k): r.append(l+' noch leer')
        return r
    def get(self,id):
        x=self.pp(id)
        if not x.exists():raise FileNotFoundError('Profil nicht gefunden')
        p=self.read(x);p['hinweise']=self.hints(p);return p
    def list(self):
        r=[]
        for x in self.p.glob('*.json'):
            p=self.read(x); person=p.get('person',{})
            r.append({'id':p['id'],'name':' '.join(filter(None,[person.get('vorname',''),person.get('nachname','')])), 'rolle':person.get('rolle',''),'status':p.get('status','Entwurf'),'aktualisiertAm':p.get('aktualisiertAm',''),'aktualisiertVon':p.get('aktualisiertVon',''),'variantenAnzahl':len(list(self.vf(p['id']).glob('*.json'))),'hinweise':self.hints(p)})
        return sorted(r,key=lambda x:x['name'].casefold())
    def create(self,data,actor):
        person=data.get('person',{}); first=str(person.get('vorname','')).strip();last=str(person.get('nachname','')).strip()
        if not first or not last:raise ValueError('Vorname und Nachname sind erforderlich.')
        id=slug(first,last)
        while self.pp(id).exists():id+='-'+uuid.uuid4().hex[:4]
        t=now(); p={'schemaVersion':'1.0','id':id,'status':'Entwurf','erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'person':{'vorname':first,'nachname':last,'titel':str(person.get('titel','')),'rolle':str(person.get('rolle','')),'standort':str(person.get('standort','')),'interneEmail':str(person.get('interneEmail','')),'telefon':str(person.get('telefon','')),'foto':None},'kurzprofil':{'positionierung':'','zusammenfassung':''},'kompetenzen':[],'branchen':[],'projekte':[],'qualifikationen':[],'sprachen':[],'dokumente':[],'historie':[{'zeitpunkt':t,'aktion':'Profil angelegt','von':actor,'details':'Manuell als Entwurf angelegt.'}]}
        self.write(self.pp(id),p);return self.get(id)
    def update(self,id,data,actor):
        p=self.get(id)
        for k in ('status','person','kurzprofil','kompetenzen','branchen','projekte','qualifikationen','sprachen'):
            if k in data:p[k]=data[k]
        if p.get('status') not in ('Entwurf','Aktuell'):raise ValueError('Ungültiger Profilstatus.')
        t=now();p['aktualisiertAm']=t;p['aktualisiertVon']=actor;p.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil gespeichert','von':actor,'details':'Profilinhalte aktualisiert.'});self.write(self.pp(id),p)
        for x in self.vf(id).glob('*.json'):
            v=self.read(x);v['status']='Basisprofil aktualisiert';v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Basisprofil aktualisiert','von':actor,'details':'Variante gegen den aktuellen Stand prüfen.'});self.write(x,v)
        return self.get(id)
    def variants(self,id):self.get(id);return sorted((self.read(x) for x in self.vf(id).glob('*.json')),key=lambda x:x.get('aktualisiertAm',''),reverse=True)
    def variant(self,pid,vid):
        x=self.vp(pid,vid)
        if not x.exists():raise FileNotFoundError('Variante nicht gefunden')
        return self.read(x)
    def create_variant(self,pid,data,actor):
        self.get(pid);t=now();id='variante-'+uuid.uuid4().hex[:10];v={'schemaVersion':'1.0','id':id,'profilId':pid,'name':str(data.get('name','Neue Profilvariante')).strip() or 'Neue Profilvariante','status':'Entwurf','kunde':str(data.get('kunde','')),'anfrage':str(data.get('anfrage','')),'zielrolle':str(data.get('zielrolle','')),'notiz':str(data.get('notiz','')),'fotoSichtbar':bool(data.get('fotoSichtbar',False)),'auswahl':data.get('auswahl',{}),'erstelltAm':t,'erstelltVon':actor,'aktualisiertAm':t,'aktualisiertVon':actor,'historie':[{'zeitpunkt':t,'aktion':'Variante angelegt','von':actor,'details':'Als Entwurf angelegt.'}]};self.write(self.vp(pid,id),v);return v
    def update_variant(self,pid,vid,data,actor):
        v=self.variant(pid,vid)
        for k in ('name','status','kunde','anfrage','zielrolle','notiz','fotoSichtbar','auswahl'):
            if k in data:v[k]=data[k]
        if v.get('status') not in ('Entwurf','Freigegeben','Basisprofil aktualisiert'):raise ValueError('Ungültiger Variantenstatus.')
        t=now();v['aktualisiertAm']=t;v['aktualisiertVon']=actor;v.setdefault('historie',[]).append({'zeitpunkt':t,'aktion':'Variante freigegeben' if v['status']=='Freigegeben' else 'Variante gespeichert','von':actor,'details':'Auswahl, Reihenfolge und Sichtbarkeit aktualisiert.'});self.write(self.vp(pid,vid),v);return v
    def archive(self,id,actor):
        p=self.get(id);target=self.a/f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe(id)}";target.mkdir();shutil.move(str(self.pp(id)),str(target/'profil.json'))
        for source,name in ((self.vf(id,False),'varianten'),(self.d/safe(id),'dokumente')):
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
            s=self.server.store;actor=self.headers.get('X-WT-Actor','Julius Rollmann');parts=[x for x in path.split('/') if x]
            if path=='/api/health' and self.command=='GET':return self.sendjson(200,{'status':'ok','zeitpunkt':now()})
            if path=='/api/profiles':
                if self.command=='GET':return self.sendjson(200,{'profile':s.list()})
                if self.command=='POST':return self.sendjson(201,s.create(self.body(),actor))
            if len(parts)>=3 and parts[1]=='profiles':
                pid=parts[2]
                if len(parts)==3:
                    if self.command=='GET':return self.sendjson(200,s.get(pid))
                    if self.command=='PUT':return self.sendjson(200,s.update(pid,self.body(),actor))
                    if self.command=='DELETE':s.archive(pid,actor);return self.sendjson(200,{'archiviert':True,'profilId':pid})
                if len(parts)==4 and parts[3]=='variants':
                    if self.command=='GET':return self.sendjson(200,{'varianten':s.variants(pid)})
                    if self.command=='POST':return self.sendjson(201,s.create_variant(pid,self.body(),actor))
                if len(parts)==5 and parts[3]=='variants':
                    if self.command=='GET':return self.sendjson(200,s.variant(pid,parts[4]))
                    if self.command=='PUT':return self.sendjson(200,s.update_variant(pid,parts[4],self.body(),actor))
            return self.sendjson(404,{'fehler':'API-Endpunkt nicht gefunden.'})
        except FileNotFoundError as e:return self.sendjson(404,{'fehler':str(e)})
        except ValueError as e:return self.sendjson(400,{'fehler':str(e)})
        except Exception:return self.sendjson(500,{'fehler':'Interner Serverfehler.'})

def main():
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8081);p.add_argument('--data-dir',type=Path,default=ROOT/'daten');a=p.parse_args();server=ThreadingHTTPServer((a.host,a.port),Handler);server.store=Store(a.data_dir);print(f'Profilmanagement: http://{a.host}:{a.port}');server.serve_forever()
if __name__=='__main__':main()
