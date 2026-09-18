#!/usr/bin/env python3
"""Run with `python3 server.py`. No packages or accounts required."""
from __future__ import annotations
import argparse, hmac, json, secrets, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from store import Store, ConflictError
from safeweb import verify

ROOT=Path(__file__).resolve().parent
STATIC={'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),'/styles.css':('styles.css','text/css; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/seed.js':('seed.js','text/javascript; charset=utf-8')}

class AppServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,port,store):
        self.store=store; self.token=secrets.token_urlsafe(32); self.check_slots=threading.BoundedSemaphore(2)
        super().__init__(('127.0.0.1',port),Handler)

class Handler(BaseHTTPRequestHandler):
    server_version='LaunchDesk/1.0'
    def allowed_origin(self):
        port=self.server.server_port
        host=self.headers.get('Host','')
        if host not in {f'127.0.0.1:{port}',f'localhost:{port}'}: return False
        origin=self.headers.get('Origin')
        return origin is None or origin in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
    def reply(self,status,body,ctype='application/json; charset=utf-8'):
        if not isinstance(body,bytes): body=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError): pass
    def authorize(self,write=False):
        if not self.allowed_origin(): self.reply(403,{'error':'Origin/Host rejected'}); return False
        if write and not hmac.compare_digest(self.headers.get('X-LaunchDesk-Token',''),self.server.token):
            self.reply(403,{'error':'Missing or invalid local CSRF token'}); return False
        return True
    def read_json(self):
        if self.headers.get('Transfer-Encoding'): raise ValueError('Chunked requests are not supported')
        if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('Use application/json')
        try: n=int(self.headers.get('Content-Length','0'))
        except ValueError: raise ValueError('Invalid Content-Length')
        if not 0<n<=10_000_000: raise ValueError('Request must be 1 byte–10 MB')
        self.connection.settimeout(15)
        raw=self.rfile.read(n)
        if len(raw)!=n: raise ValueError('Incomplete request body')
        return json.loads(raw,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
    def do_GET(self):
        if not self.authorize(): return
        path=urlsplit(self.path).path
        if path=='/api/workspace':
            rev,state=self.server.store.read(); return self.reply(200,{'revision':rev,'state':state,'token':self.server.token})
        if path=='/api/health': return self.reply(200,{'ok':True,'storage':'sqlite','schema_version':1})
        if path in STATIC:
            name,ctype=STATIC[path]
            try: return self.reply(200,(ROOT/'web'/name).read_bytes(),ctype)
            except FileNotFoundError: return self.reply(500,{'error':'Missing app asset. Run tools/build_catalog.py.'})
        self.reply(404,{'error':'Not found'})
    def do_PUT(self):
        if not self.authorize(write=True): return
        if urlsplit(self.path).path!='/api/workspace': return self.reply(404,{'error':'Not found'})
        try:
            state=self.read_json()
            try: revision=int(self.headers.get('If-Match',''))
            except ValueError: return self.reply(428,{'error':'If-Match revision is required'})
            new_revision=self.server.store.write(state,revision)
            self.reply(200,{'revision':new_revision})
        except ConflictError as e: self.reply(409,{'error':str(e)})
        except (ValueError,TypeError,KeyError,RecursionError) as e: self.reply(400,{'error':str(e)})
        except Exception: self.reply(500,{'error':'Save failed; existing SQLite state was not intentionally replaced'})
    def do_POST(self):
        if not self.authorize(write=True): return
        if urlsplit(self.path).path!='/api/verify': return self.reply(404,{'error':'Not found'})
        if not self.server.check_slots.acquire(blocking=False): return self.reply(429,{'error':'Two checks are already running. Try again after they finish.'})
        try:
            data=self.read_json()
            if not isinstance(data,dict): raise ValueError('Expected JSON object')
            result=verify(data.get('listing_url',''),data.get('target_url',''))
            self.reply(200,result)
        except (ValueError,TypeError,RecursionError) as e: self.reply(400,{'error':str(e)})
        except Exception: self.reply(500,{'error':'Link check failed; no verification claim recorded'})
        finally: self.server.check_slots.release()
    def do_OPTIONS(self): self.reply(405,{'error':'Cross-origin access is not supported'})
    def log_message(self,fmt,*args):
        # Do not log request bodies, product URLs, or full verification queries.
        print('[LaunchDesk]',fmt % args)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8765); p.add_argument('--db',type=Path,default=ROOT/'data'/'workspace.sqlite3'); p.add_argument('--no-browser',action='store_true')
    args=p.parse_args()
    if not 1024<=args.port<=65535: p.error('Choose a port from 1024 to 65535')
    seed=json.loads((ROOT/'data'/'catalog.json').read_text())
    server=AppServer(args.port,Store(args.db,seed))
    url=f'http://127.0.0.1:{args.port}'
    print(f'LaunchDesk: {url}\nDatabase: {args.db}\nPrivate localhost only. Press Ctrl+C to stop.')
    if not args.no_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nStopped.')
    finally: server.server_close()

if __name__=='__main__': main()
