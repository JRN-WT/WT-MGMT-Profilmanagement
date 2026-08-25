"""Lokaler JSON-Server fuer WERK TRIFFT Profilmanagement. Nur Standardbibliothek."""
import argparse, copy, json, re, shutil, uuid
try:
    from profilmanagement_pdf_playwright import PDFExportUnavailable, export_pdf
except ModuleNotFoundError:
    PDFExportUnavailable = RuntimeError
    export_pdf = None
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
LISTS = ('kompetenzen', 'branchen', 'projekte', 'qualifikationen', 'sprachen')
FIELDS = ('kurzprofil',) + LISTS

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
def cp(value): return copy.deepcopy(value)
def safe(value, fallback='datei'): return re.sub(r'[^A-Za-z0-9ÄÖÜäöüß._ -]+', '-', str(value)).strip(' .-') or fallback
def slug(first, last): return re.sub(r'[^a-z0-9]+', '-', (last+'-'+first).lower()).strip('-') or uuid.uuid4().hex[:8]
def pick(items, visible=True): return [{'id': x['id'], 'sichtbar': visible, 'reihenfolge': index+1} for index, x in enumerate(items)]

def project(item):
    """Migrate legacy one-line projects and retain only project-card fields."""
    item = item if isinstance(item, dict) else {}
    return {
        'id': str(item.get('id') or uuid.uuid4().hex),
        'titel': str(item.get('titel') or item.get('bezeichnung') or ''),
        'startMonat': str(item.get('startMonat') or ''),
        'endeMonat': str(item.get('endeMonat') or ''),
        'laufend': bool(item.get('laufend', False)),
        'rolle': str(item.get('rolle') or ''),
        'beschreibung': str(item.get('beschreibung') or item.get('details') or ''),
        'aufgaben': str(item.get('aufgaben') or ''),
    }

def valid_month(value): return bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value or ''))

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.p = self.root/'profile'; self.v = self.root/'varianten'; self.d = self.root/'dokumente'; self.a = self.root/'archiv'
        for folder in (self.p, self.v, self.d, self.a): folder.mkdir(parents=True, exist_ok=True)
    def read(self, path):
        try: return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error: raise ValueError(f'JSON-Datei nicht lesbar: {path.name}') from error
    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(path.suffix+'.tmp'); temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8'); temp.replace(path)
    def pp(self, pid): return self.p/f'{safe(pid)}.json'
    def vf(self, pid, create=True):
        path = self.v/safe(pid)
        if create: path.mkdir(parents=True, exist_ok=True)
        return path
    def vp(self, pid, vid): return self.vf(pid)/f'{safe(vid)}.json'
    def normalize(self, key, items):
        result=[]
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict): continue
            if key=='projekte': result.append(project(item)); continue
            value=cp(item); value['id']=str(value.get('id') or uuid.uuid4().hex); result.append(value)
        return result
    def content(self, profile): return {key: cp(profile.get(key, {} if key=='kurzprofil' else [])) for key in FIELDS}
    def hints(self, profile):
        result=[]; person=profile.get('person',{})
        if not person.get('vorname') or not person.get('nachname'): result.append('Name unvollständig')
        for key, label in (('kurzprofil','Kurzprofil'),('kompetenzen','Kompetenzen'),('projekte','Projekterfahrung'),('qualifikationen','Qualifikationen'),('sprachen','Sprachen')):
            if not profile.get(key): result.append(label+' noch leer')
        return result
    def get(self, pid):
        path=self.pp(pid)
        if not path.exists(): raise FileNotFoundError('Profil nicht gefunden')
        profile=self.read(path); profile.setdefault('revision',1)
        for key in LISTS: profile[key]=self.normalize(key,profile.get(key,[]))
        profile['hinweise']=self.hints(profile); return profile
    def list(self):
        result=[]
        for path in self.p.glob('*.json'):
            profile=self.get(path.stem); person=profile.get('person',{})
            result.append({'id':profile['id'],'name':' '.join(filter(None,[person.get('vorname',''),person.get('nachname','')])), 'rolle':person.get('rolle',''),'status':profile.get('status','Entwurf'),'aktualisiertAm':profile.get('aktualisiertAm',''),'variantenAnzahl':len(list(self.vf(profile['id']).glob('*.json'))),'hinweise':self.hints(profile)})
        return sorted(result,key=lambda value:value['name'].casefold())
    def create(self, data, actor):
        source=data.get('person',{}); first=str(source.get('vorname','')).strip(); last=str(source.get('nachname','')).strip()
        if not first or not last: raise ValueError('Vorname und Nachname sind erforderlich.')
        pid=slug(first,last)
        while self.pp(pid).exists(): pid+='-'+uuid.uuid4().hex[:4]
        timestamp=now(); profile={'schemaVersion':'2.1','id':pid,'revision':1,'status':'Entwurf','erstelltAm':timestamp,'erstelltVon':actor,'aktualisiertAm':timestamp,'aktualisiertVon':actor,'person':{'vorname':first,'nachname':last,'titel':'','rolle':str(source.get('rolle','')),'standort':'','interneEmail':'','telefon':'','foto':None},'kurzprofil':{'positionierung':'','zusammenfassung':''},'kompetenzen':[],'branchen':[],'projekte':[],'qualifikationen':[],'sprachen':[],'dokumente':[],'historie':[{'zeitpunkt':timestamp,'aktion':'Profil angelegt','von':actor,'details':'Manuell als Entwurf angelegt.'}]}
        self.write(self.pp(pid),profile); return self.get(pid)
    def validate_projects(self, rows):
        for index,item in enumerate(rows,1):
            missing=[]
            if not item['titel'].strip(): missing.append('Titel')
            if not valid_month(item['startMonat']): missing.append('Startmonat')
            if not item['laufend'] and not valid_month(item['endeMonat']): missing.append('Endmonat oder „laufend“')
            if not item['rolle'].strip(): missing.append('Rolle')
            if not item['beschreibung'].strip(): missing.append('Kurzbeschreibung')
            if not item['aufgaben'].strip(): missing.append('Tätigkeiten')
            if missing: raise ValueError(f'Projekt {index}: '+', '.join(missing)+' ergänzen.')
            if not item['laufend'] and item['endeMonat']<item['startMonat']: raise ValueError(f'Projekt {index}: Der Endmonat liegt vor dem Startmonat.')
    def normvar(self, variant):
        variant.setdefault('inhalte',{}); variant.setdefault('basisSnapshot',cp(variant['inhalte']))
        for key in FIELDS:
            variant['inhalte'].setdefault(key,{} if key=='kurzprofil' else [])
            if key!='kurzprofil': variant['inhalte'][key]=self.normalize(key,variant['inhalte'][key])
        variant.setdefault('auswahl',{})
        for key in LISTS:
            existing={entry.get('id'):entry for entry in variant['auswahl'].get(key,[]) if entry.get('id')}
            variant['auswahl'][key]=[{'id':entry['id'],'sichtbar':bool(existing.get(entry['id'],{}).get('sichtbar',True)),'reihenfolge':existing.get(entry['id'],{}).get('reihenfolge',index+1)} for index,entry in enumerate(variant['inhalte'][key])]
        variant.setdefault('basisRevisionGeprueft',1); variant.setdefault('basisRevisionAktuell',variant['basisRevisionGeprueft']); variant.setdefault('pruefungErforderlich',False)
    def mark(self,pid,revision,timestamp,actor):
        profile=self.get(pid); content=self.content(profile)
        for path in self.vf(pid).glob('*.json'):
            variant=self.read(path); self.normvar(variant)
            if not variant.get('pruefungErforderlich'): variant['statusVorBasisAenderung']=variant.get('status','Entwurf')
            choices={}
            for key in LISTS:
                old={entry.get('id'):entry for entry in variant.get('auswahl',{}).get(key,[])}
                choices[key]=[{'id':entry['id'],'sichtbar':bool(old[entry['id']]['sichtbar']) if entry['id'] in old else False,'reihenfolge':old[entry['id']].get('reihenfolge',index+1) if entry['id'] in old else index+1} for index,entry in enumerate(content[key])]
            variant['inhalte']=cp(content); variant['auswahl']=choices; self.normvar(variant); variant['pruefungErforderlich']=True; variant['status']='Prüfung erforderlich'; variant['basisRevisionAktuell']=revision; variant['aktualisiertAm']=timestamp; variant['aktualisiertVon']=actor; variant.setdefault('historie',[]).append({'zeitpunkt':timestamp,'aktion':'Basisprofil aktualisiert','von':actor,'details':'Basisprofil geändert; Variante zur Prüfung markiert.'}); self.write(path,variant)
    def update(self,pid,data,actor):
        profile=self.get(pid); before=self.content(profile)
        for key in ('status','person','kurzprofil')+LISTS:
            if key in data: profile[key]=data[key]
        for key in LISTS: profile[key]=self.normalize(key,profile.get(key,[]))
        profile['projekte']=[item for item in profile['projekte'] if any((item['titel'].strip(),item['startMonat'],item['endeMonat'],item['laufend'],item['rolle'].strip(),item['beschreibung'].strip(),item['aufgaben'].strip()))]
        self.validate_projects(profile['projekte'])
        if profile.get('status') not in ('Entwurf','Aktuell'): raise ValueError('Ungültiger Profilstatus.')
        changed=before!=self.content(profile); timestamp=now(); profile['aktualisiertAm']=timestamp; profile['aktualisiertVon']=actor; profile['revision']=int(profile.get('revision',1))+(1 if changed else 0); profile.setdefault('historie',[]).append({'zeitpunkt':timestamp,'aktion':'Basisprofil gespeichert','von':actor,'details':'Profilinhalte aktualisiert.' if changed else 'Stammdaten gespeichert; Profilinhalte unverändert.'}); self.write(self.pp(pid),profile)
        if changed: self.mark(pid,profile['revision'],timestamp,actor)
        return self.get(pid)
    def variants(self,pid): self.get(pid); return sorted((self.read(path) for path in self.vf(pid).glob('*.json')),key=lambda value:value.get('aktualisiertAm',''),reverse=True)
    def variant(self,pid,vid):
        path=self.vp(pid,vid)
        if not path.exists(): raise FileNotFoundError('Variante nicht gefunden')
        value=self.read(path); self.normvar(value); return value
    def create_variant(self,pid,data,actor):
        profile=self.get(pid); timestamp=now(); vid='variante-'+uuid.uuid4().hex[:10]; content=self.content(profile)
        variant={'schemaVersion':'2.1','id':vid,'profilId':pid,'name':str(data.get('name','Neue Profilvariante')).strip() or 'Neue Profilvariante','status':'Entwurf','kunde':str(data.get('kunde','')),'anfrage':str(data.get('anfrage','')),'zielrolle':str(data.get('zielrolle',profile.get('person',{}).get('rolle',''))),'notiz':str(data.get('notiz','')),'fotoSichtbar':bool(data.get('fotoSichtbar',False)),'inhalte':content,'basisSnapshot':cp(content),'basisRevisionGeprueft':profile.get('revision',1),'basisRevisionAktuell':profile.get('revision',1),'pruefungErforderlich':False,'auswahl':{key:pick(content[key]) for key in LISTS},'erstelltAm':timestamp,'erstelltVon':actor,'aktualisiertAm':timestamp,'aktualisiertVon':actor,'historie':[{'zeitpunkt':timestamp,'aktion':'Variante angelegt','von':actor,'details':'Aus Basisprofil angelegt.'}]}
        self.write(self.vp(pid,vid),variant); return variant
    def update_variant(self,pid,vid,data,actor):
        self.get(pid); variant=self.variant(pid,vid)
        for key in ('name','kunde','anfrage','zielrolle','notiz','fotoSichtbar'):
            if key in data: variant[key]=data[key]
        if 'auswahl' in data: variant['auswahl']=cp(data['auswahl'])
        self.normvar(variant); desired=data.get('status')
        if desired=='Freigegeben' and variant.get('pruefungErforderlich'): raise ValueError('Bitte zuerst die Basisprofil-Änderungen prüfen, bevor Sie diese Variante freigeben.')
        if desired in ('Entwurf','Freigegeben'): variant['status']=desired
        elif variant.get('pruefungErforderlich'): variant['status']='Prüfung erforderlich'
        timestamp=now(); variant['aktualisiertAm']=timestamp; variant['aktualisiertVon']=actor
        variant.setdefault('historie',[]).append({'zeitpunkt':timestamp,'aktion':'Variante freigegeben' if variant['status']=='Freigegeben' else 'Variante gespeichert','von':actor,'details':'Kontext, Auswahl und Reihenfolge gespeichert.'}); self.write(self.vp(pid,vid),variant); return variant
    def changes(self,pid,vid):
        profile=self.get(pid); variant=self.variant(pid,vid); old=variant.get('basisSnapshot',{}); changes=[]
        if old.get('kurzprofil',{})!=profile.get('kurzprofil',{}): changes.append({'feld':'kurzprofil','typ':'geaendert','titel':'Kurzprofil'})
        for key in LISTS:
            before={entry.get('id'):entry for entry in old.get(key,[]) if entry.get('id')}; current={entry.get('id'):entry for entry in profile.get(key,[]) if entry.get('id')}
            for ident,item in current.items():
                if ident not in before or before[ident]!=item: changes.append({'feld':key,'typ':'neu' if ident not in before else 'geaendert','titel':item.get('titel') or item.get('sprache') or item.get('bezeichnung') or 'Eintrag'})
            for ident,item in before.items():
                if ident not in current: changes.append({'feld':key,'typ':'entfernt','titel':item.get('titel') or item.get('sprache') or item.get('bezeichnung') or 'Eintrag'})
        return {'pruefungErforderlich':bool(variant.get('pruefungErforderlich')),'aenderungen':changes}
    def review(self,pid,vid,actor):
        profile=self.get(pid); variant=self.variant(pid,vid); variant['inhalte']=self.content(profile); variant['basisSnapshot']=self.content(profile); variant['basisRevisionGeprueft']=profile.get('revision',1); variant['basisRevisionAktuell']=profile.get('revision',1); variant['pruefungErforderlich']=False
        if variant.get('status')=='Prüfung erforderlich': variant['status']=variant.pop('statusVorBasisAenderung','Entwurf')
        self.normvar(variant); timestamp=now(); variant['aktualisiertAm']=timestamp; variant['aktualisiertVon']=actor
        variant.setdefault('historie',[]).append({'zeitpunkt':timestamp,'aktion':'Basisänderungen geprüft','von':actor,'details':'Basisprofil-Änderungen bestätigt.'}); self.write(self.vp(pid,vid),variant); return variant
    def archive(self,pid,actor):
        profile=self.get(pid); target=self.a/f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe(pid)}"; target.mkdir(); shutil.move(str(self.pp(pid)),str(target/'profil.json'))
        for source,name in ((self.vf(pid,False),'varianten'),(self.d/safe(pid),'dokumente')):
            if source.exists(): shutil.move(str(source),str(target/name))
        self.write(target/'archiv-info.json',{'profilId':profile['id'],'archiviertAm':now(),'archiviertVon':actor,'grund':'Archivierung über Profilmanagement'})
    def archive_variant(self,pid,vid,actor):
        variant=self.variant(pid,vid); source=self.vp(pid,vid); target=self.a/safe(pid)/'varianten'; target.mkdir(parents=True,exist_ok=True); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); shutil.move(str(source),str(target/f'{stamp}-{safe(vid)}.json')); self.write(target/f'{stamp}-{safe(vid)}.archiv-info.json',{'profilId':pid,'variantenId':vid,'variantenName':variant.get('name',''), 'archiviertAm':now(),'archiviertVon':actor,'grund':'Archivierung über Profilmanagement'}); return {'archiviert':True,'profilId':pid,'variantenId':vid}

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self): self.send_header('Cache-Control','no-store'); super().end_headers()
    def do_GET(self):
        if self.path.split('?',1)[0].endswith('profilmanagement.html'):
            page=(ROOT/'profilmanagement.html').read_text(encoding='utf-8')
            if 'profilmanagement-enhancements.js' not in page:
                page=page.replace('</body>','<script src="profilmanagement-enhancements.js"></script></body>')
            body=page.encode('utf-8'); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if not self.api(): super().do_GET()
    def do_POST(self): self.api()
    def do_PUT(self): self.api()
    def do_DELETE(self): self.api()
    def body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))).decode() or '{}')
        except json.JSONDecodeError: raise ValueError('Ungültige JSON-Anfrage.')
    def sendjson(self,status,data):
        body=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return True
    def sendfile(self,path,name):
        body=Path(path).read_bytes(); self.send_response(200); self.send_header('Content-Type','application/pdf'); self.send_header('Content-Disposition',f'attachment; filename="{safe(name)}"'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return True
    def api(self):
        path=unquote(urlparse(self.path).path).rstrip('/') or '/'
        if not path.startswith('/api'): return False
        try:
            store=self.server.store; actor=self.headers.get('X-WT-Actor','Julius Rollmann'); parts=[part for part in path.split('/') if part]
            if path=='/api/health' and self.command=='GET': return self.sendjson(200,{'status':'ok','zeitpunkt':now()})
            if path=='/api/profiles':
                if self.command=='GET': return self.sendjson(200,{'profile':store.list()})
                if self.command=='POST': return self.sendjson(201,store.create(self.body(),actor))
            if len(parts)>=3 and parts[1]=='profiles':
                pid=parts[2]
                if len(parts)==3:
                    if self.command=='GET': return self.sendjson(200,store.get(pid))
                    if self.command=='PUT': return self.sendjson(200,store.update(pid,self.body(),actor))
                    if self.command=='DELETE': store.archive(pid,actor); return self.sendjson(200,{'archiviert':True,'profilId':pid})
                if len(parts)==4 and parts[3]=='variants':
                    if self.command=='GET': return self.sendjson(200,{'varianten':store.variants(pid)})
                    if self.command=='POST': return self.sendjson(201,store.create_variant(pid,self.body(),actor))
                if len(parts)==5 and parts[3]=='variants':
                    if self.command=='GET': return self.sendjson(200,store.variant(pid,parts[4]))
                    if self.command=='PUT': return self.sendjson(200,store.update_variant(pid,parts[4],self.body(),actor))
                    if self.command=='DELETE': return self.sendjson(200,store.archive_variant(pid,parts[4],actor))
                if len(parts)==6 and parts[3]=='variants' and parts[5]=='pdf' and self.command in ('GET','POST'):
                    if export_pdf is None: raise ValueError('PDF-Export ist nicht verfügbar: Die Datei „profilmanagement_pdf_playwright.py“ fehlt. Das Profilmanagement selbst läuft weiterhin ohne den PDF-Export.')
                    profile=store.get(pid); variant=store.variant(pid,parts[4])
                    if self.command=='POST':
                        current=self.body()
                        for key in ('name','kunde','anfrage','zielrolle','notiz','fotoSichtbar'):
                            if key in current: variant[key]=current[key]
                        if 'auswahl' in current: variant['auswahl']=cp(current['auswahl'])
                        # Exportiert genau die aktive Vorschau, ohne Variante oder Status zu speichern.
                        variant['inhalte']=store.content(profile)
                        store.normvar(variant)
                    filename=safe(f"{datetime.now().strftime('%Y-%m-%d')}_WT-Profil_{profile.get('person', {}).get('vorname', '')}_{profile.get('person', {}).get('nachname', '')}.pdf")
                    output=store.d/safe(pid)/filename
                    logo_path=next((candidate for candidate in (ROOT/'logo_werktrifft.png', ROOT/'assets'/'logo_werktrifft.png', ROOT.parent/'WT-Dashboard-Module'/'logo_werktrifft.png') if candidate.exists()), None)
                    try:
                        export_pdf(profile,variant,output,logo_path=logo_path)
                    except PDFExportUnavailable as error:
                        raise ValueError(str(error)) from error
                    return self.sendfile(output,filename)
                if len(parts)==6 and parts[3]=='variants' and parts[5]=='basis-aenderungen':
                    if self.command=='GET': return self.sendjson(200,store.changes(pid,parts[4]))
                    if self.command=='POST': return self.sendjson(200,store.review(pid,parts[4],actor))
            return self.sendjson(404,{'fehler':'API-Endpunkt nicht gefunden.'})
        except FileNotFoundError as error: return self.sendjson(404,{'fehler':str(error)})
        except ValueError as error: return self.sendjson(400,{'fehler':str(error)})
        except Exception: return self.sendjson(500,{'fehler':'Interner Serverfehler.'})

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8081); parser.add_argument('--data-dir',type=Path,default=ROOT/'daten'); args=parser.parse_args(); server=ThreadingHTTPServer((args.host,args.port),Handler); server.store=Store(args.data_dir); print(f'Profilmanagement: http://{args.host}:{args.port}'); server.serve_forever()
if __name__=='__main__': main()
