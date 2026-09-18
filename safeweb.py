"""Bounded public-web reads with pinned DNS, per-origin pacing, and robots checks.

No browser execution, cookies, authentication, CAPTCHA bypass, or proxying of
private IP addresses. Intended for user-initiated checks, not mass crawling.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
import http.client, ipaddress, re, socket, ssl, threading, time
from catalog import clean_url, host_of

AGENT = 'LaunchDesk/1.0 (user-initiated backlink verification)'
MAX_BYTES = 2_000_000
TIMEOUT = 7
_lock = threading.Lock()
_last_request: dict[str, float] = {}

class FetchError(ValueError): pass

@dataclass
class Page:
    url: str
    status: int
    headers: dict[str, str]
    text: str
    redirects: list[str]


def public_target(url: str):
    url=clean_url(url)
    p=urlsplit(url)
    if not p.hostname: raise FetchError('Missing hostname')
    host=p.hostname
    if host in {'localhost', 'metadata.google.internal'} or host.endswith(('.local','.localhost','.internal')):
        raise FetchError('Private/local destinations are not allowed')
    port=p.port or (443 if p.scheme=='https' else 80)
    if port not in (80,443): raise FetchError('Only public HTTP/HTTPS ports 80 and 443 are allowed')
    try: addresses=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    except OSError as e: raise FetchError('DNS lookup failed; this is not proof the site is dead') from e
    ips=list(dict.fromkeys(a[4][0] for a in addresses))
    if not ips: raise FetchError('No DNS addresses found')
    for address in ips:
        ip=ipaddress.ip_address(address)
        mapped=getattr(ip,'ipv4_mapped',None)
        if not ip.is_global or (mapped and not mapped.is_global):
            raise FetchError('A DNS answer points to a non-public address; request blocked')
    return url,host,port,ips[0]

class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host, port, ip, tls):
        super().__init__(host,port,timeout=TIMEOUT)
        self.pinned_ip=ip; self.use_tls=tls
    def connect(self):
        # Never re-resolve the hostname after validating DNS. TLS still verifies
        # the original hostname through SNI and standard certificate validation.
        sock=socket.create_connection((self.pinned_ip,self.port),self.timeout)
        if self.use_tls:
            try: sock=ssl.create_default_context().wrap_socket(sock,server_hostname=self.host)
            except Exception: sock.close(); raise
        self.sock=sock


def pace(origin: str, delay=1.0):
    with _lock:
        wait=max(0,_last_request.get(origin,0)+delay-time.monotonic())
        if wait: time.sleep(wait)
        _last_request[origin]=time.monotonic()


def fetch_public(url: str, max_bytes=MAX_BYTES, redirect_guard=None) -> Page:
    redirects=[]
    for hop in range(5):
        url,host,port,ip=public_target(url)
        p=urlsplit(url)
        origin=f'{p.scheme}://{host}:{port}'
        pace(origin)
        conn=PinnedConnection(host,port,ip,p.scheme=='https')
        try:
            path=urlunsplit(('', '', p.path or '/', p.query, ''))
            conn.request('GET',path,headers={'User-Agent':AGENT,'Accept':'text/html,text/plain,application/json;q=0.8,*/*;q=0.1','Accept-Encoding':'identity','Connection':'close'})
            response=conn.getresponse()
            headers={k.lower():v for k,v in response.getheaders()}
            if response.status in (301,302,303,307,308):
                if not headers.get('location'): raise FetchError('Redirect has no Location')
                nxt=clean_url(urljoin(url,headers['location']))
                if urlsplit(url).scheme=='https' and urlsplit(nxt).scheme=='http':
                    raise FetchError('HTTPS-to-HTTP redirect blocked')
                if redirect_guard is not None:
                    redirect_guard(nxt)
                redirects.append(url); url=nxt; continue
            length=headers.get('content-length','')
            if length.isdigit() and int(length)>max_bytes: raise FetchError('Response exceeds the size limit')
            deadline=time.monotonic()+20
            chunks=[]; size=0
            while True:
                if time.monotonic()>deadline: raise FetchError('Response body deadline exceeded')
                part=response.read1(min(65_536,max_bytes+1-size))
                if not part: break
                chunks.append(part); size+=len(part)
                if size>max_bytes: raise FetchError('Response exceeds the size limit')
            content=b''.join(chunks)
            encoding=re.search(r'charset\s*=\s*["\']?([\w-]+)',headers.get('content-type',''),re.I)
            charset=encoding.group(1) if encoding else 'utf-8'
            try: text=content.decode(charset,errors='replace')
            except LookupError: text=content.decode('utf-8',errors='replace')
            return Page(url,response.status,headers,text,redirects)
        except (OSError, http.client.HTTPException) as e:
            raise FetchError('Network/TLS request failed; site availability is unconfirmed') from e
        finally: conn.close()
    raise FetchError('Too many redirects')


def robots_policy(url: str):
    p=urlsplit(clean_url(url)); robots_url=urlunsplit((p.scheme,p.netloc,'/robots.txt','',''))
    robots=fetch_public(robots_url,max_bytes=512_000)
    if robots.status in (404,410): return True,1.0,'robots.txt not found'
    if robots.status in (401,403): return False,1.0,'robots.txt access denied; check skipped'
    if robots.status!=200: return False,1.0,f'Could not establish robots permission (HTTP {robots.status})'
    parser=RobotFileParser(); parser.set_url(robots.url); parser.parse(robots.text.splitlines())
    allowed=parser.can_fetch('LaunchDesk',url)
    delay=parser.crawl_delay('LaunchDesk') or parser.crawl_delay('*') or 1
    rate=parser.request_rate('LaunchDesk') or parser.request_rate('*')
    if rate and rate.requests: delay=max(delay,rate.seconds/rate.requests)
    if delay>15: return False,delay,'Robots pacing exceeds this interactive checker’s limit; check manually'
    return allowed,max(1.0,float(delay)),'Allowed by parsed robots.txt' if allowed else 'Disallowed by robots.txt; check skipped'

class LinksParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors=[]; self.base=''; self.directives=[]
    def handle_starttag(self,tag,attrs):
        a={k.lower():v or '' for k,v in attrs}
        if tag=='a' and a.get('href') and len(self.anchors)<10_000:
            self.anchors.append({'href':a['href'],'rel':a.get('rel','').lower().split()})
        elif tag=='base' and not self.base: self.base=a.get('href','')
        elif tag=='meta' and a.get('name','').lower() in {'robots','googlebot','bingbot'}:
            self.directives.append(a.get('content','').lower())

def analyze_html(html: str, listing_url: str, target_url: str, headers=None):
    parser=LinksParser(); parser.feed(html)
    base=urljoin(listing_url,parser.base) if parser.base else listing_url
    target=host_of(target_url)
    matches=[]
    for a in parser.anchors:
        try:
            href=clean_url(urljoin(base,a['href'])); h=host_of(href)
        except (ValueError,UnicodeError): continue
        if h!=target and not h.endswith('.'+target): continue
        rel=set(a['rel']); qualifiers=rel&{'nofollow','ugc','sponsored'}
        kind='nofollow' if 'nofollow' in rel else 'sponsored' if 'sponsored' in rel else 'ugc' if 'ugc' in rel else 'follow'
        matches.append({'href':href,'rel':sorted(rel),'qualifiers':sorted(qualifiers),'html_link_type':kind})
    directives=' '.join(parser.directives)+' '+(headers or {}).get('x-robots-tag','').lower()
    noindex=bool(re.search(r'\b(noindex|none)\b',directives)); nofollow=bool(re.search(r'\b(nofollow|none)\b',directives))
    kinds={m['html_link_type'] for m in matches}
    link_type='not_found' if not matches else 'mixed' if len(kinds)>1 else next(iter(kinds))
    effective='nofollow' if nofollow and matches else link_type
    return {'link_type':effective,'html_link_type':link_type,'matches':matches,'target_domain':target,
        'page_noindex':noindex,'page_nofollow':nofollow,
        'message': 'No matching link in the fetched HTML. It may be JavaScript-rendered; this is not a definitive missing-link verdict.' if not matches else 'Matching anchors found. Read the exact attributes and page directives; indexing and ranking value were not checked.'}


def verify(listing_url: str, target_url: str):
    listing_url=clean_url(listing_url); target_url=clean_url(target_url)
    if not listing_url or not target_url: raise FetchError('Listing and target URLs are required')
    result={'listing_url':listing_url,'target_url':target_url,'checked_at':datetime.now(timezone.utc).isoformat(),'link_type':'unknown','method':'static-html'}
    try:
        allowed,delay,note=robots_policy(listing_url); result['robots']=note
        if not allowed: result['message']=note; return result
        p=urlsplit(listing_url); pace(f'{p.scheme}://{p.hostname}:{p.port or (443 if p.scheme=="https" else 80)}',delay)
        def guard_redirect(url):
            ok, redirect_delay, redirect_note = robots_policy(url)
            if not ok: raise FetchError('Redirect target: ' + redirect_note)
            q = urlsplit(url)
            pace(f'{q.scheme}://{q.hostname}:{q.port or (443 if q.scheme == "https" else 80)}', redirect_delay)
        page=fetch_public(listing_url, redirect_guard=guard_redirect)
        result.update({'http_status':page.status,'final_url':page.url,'redirects':page.redirects})
        if page.redirects:
            result['redirect_note']='Redirect targets passed public-network and robots checks before fetching.'
        if page.status!=200:
            result['message']=f'HTTP {page.status}. Link status is unknown; no dead-site verdict recorded.'; return result
        if 'html' not in page.headers.get('content-type','').lower():
            result['message']='The response is not labelled HTML; check skipped.'; return result
        result.update(analyze_html(page.text,page.url,target_url,page.headers))
        return result
    except (ValueError,OSError) as e:
        result['message']=str(e); return result
