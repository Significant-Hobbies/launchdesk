"""SQLite state with atomic revisions. Kept out of the served web directory."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, os, re, sqlite3
from pathlib import Path
from catalog import clean_url, parse_dr, initial_state, STATUSES, LINKS, identity

class ConflictError(Exception): pass

def _id(value):
    return isinstance(value,str) and bool(re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',value)) and value not in {'__proto__','constructor','prototype'}

def validate_state(s):
    if not isinstance(s,dict) or s.get('schema_version')!=1: raise ValueError('Unsupported workspace schema')
    rows=s.get('catalog'); products=s.get('products'); submissions=s.get('submissions')
    if not isinstance(rows,list) or len(rows)>50_000: raise ValueError('Catalog limit is 50,000 rows')
    if not isinstance(products,list) or not 1<=len(products)<=1000: raise ValueError('Need 1–1000 products')
    if not isinstance(submissions,dict): raise ValueError('Invalid submissions map')
    ids=set(); keys=set(); pids=set()
    for r in rows:
        if not isinstance(r,dict) or not _id(r.get('id')) or r['id'] in ids: raise ValueError('Duplicate or invalid destination ID')
        ids.add(r['id'])
        if not isinstance(r.get('key'),str) or r['key'] in keys: raise ValueError('Duplicate or invalid destination key')
        keys.add(r['key'])
        if not isinstance(r.get('name'),str) or not 1<=len(r['name'].strip())<=500: raise ValueError('Invalid destination name')
        if not clean_url(r.get('website','')): raise ValueError('Destination URL required')
        if r['key'] != identity(r['website']): raise ValueError('Destination key does not match its URL')
        for field in ('submission_url','source_url','evidence_url'):
            if r.get(field): clean_url(r[field])
        parse_dr(r.get('reported_dr'))
        if r.get('reported_link') not in LINKS: raise ValueError('Invalid link type')
        if not isinstance(r.get('flags'),list) or not all(isinstance(x,str) for x in r['flags']): raise ValueError('Invalid flags')
        if not isinstance(r.get('claims'),list) or len(r['claims'])>200: raise ValueError('Invalid claims')
        for c in r['claims']:
            if not isinstance(c,dict): raise ValueError('Invalid source claim')
            parse_dr(c.get('dr'))
            if c.get('source'): clean_url(c['source'])
    for p in products:
        if not isinstance(p,dict) or not _id(p.get('id')) or p['id'] in pids: raise ValueError('Duplicate or invalid product ID')
        pids.add(p['id'])
        if not isinstance(p.get('name'),str) or not 1<=len(p['name'].strip())<=500: raise ValueError('Invalid product name')
        if not isinstance(p.get('tags'),list) or not all(isinstance(x,str) for x in p['tags']): raise ValueError('Invalid product tags')
        if p.get('url'): clean_url(p['url'])
    if s.get('active_product') not in pids: raise ValueError('Active product does not exist')
    for key,v in submissions.items():
        parts=key.split('::')
        if len(parts)!=2 or parts[0] not in pids or parts[1] not in ids: raise ValueError('Submission references unknown records')
        if not isinstance(v,dict) or v.get('status') not in STATUSES: raise ValueError('Invalid submission status')
        if v.get('listing_url'): clean_url(v['listing_url'])
    return s

class Store:
    def __init__(self,path: Path,catalog: list):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, body TEXT NOT NULL, updated_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS audit (revision INTEGER PRIMARY KEY, updated_at TEXT NOT NULL, sha256 TEXT NOT NULL, action TEXT NOT NULL)')
            seed=initial_state(catalog); validate_state(seed)
            db.execute('INSERT OR IGNORE INTO workspace VALUES (1,0,?,?)',(json.dumps(seed,ensure_ascii=False),self.now()))
        try: os.chmod(self.path,0o600)
        except OSError: pass
    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat()
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10); db.execute('PRAGMA busy_timeout=10000'); return db
    def read(self):
        with self.connect() as db:
            rev,body=db.execute('SELECT revision,body FROM workspace WHERE id=1').fetchone()
        return rev,json.loads(body)
    def write(self,state,expected,action='workspace-save'):
        validate_state(state); body=json.dumps(state,ensure_ascii=False,allow_nan=False)
        if len(body.encode())>10_000_000: raise ValueError('Workspace exceeds 10 MB')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rev,previous=db.execute('SELECT revision,body FROM workspace WHERE id=1').fetchone()
            if rev!=expected: raise ConflictError('Revision conflict. Export your edits and reload.')
            stamp=self.now()
            # A previous-state recovery file supplements SQLite atomic commits.
            recovery=self.path.parent/'last-good-workspace.json'
            tmp=recovery.with_suffix('.tmp')
            fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(previous); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,recovery)
            db.execute('UPDATE workspace SET revision=?,body=?,updated_at=? WHERE id=1',(rev+1,body,stamp))
            db.execute('INSERT INTO audit VALUES (?,?,?,?)',(rev+1,stamp,hashlib.sha256(body.encode()).hexdigest(),action))
        return rev+1
