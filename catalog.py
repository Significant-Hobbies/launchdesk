"""Pure catalog normalization. Unknown metrics stay null, never become zero."""
from __future__ import annotations
import csv, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
TODAY = '2026-09-18'
SOURCE = 'https://github.com/mezmer90/saas-directories/blob/main/saas-directories.csv'
STATUSES = {'unstarted', 'queued', 'submitted', 'live', 'rejected', 'skipped'}
LINKS = {'follow', 'nofollow', 'ugc', 'sponsored', 'mixed', 'unknown', 'not_found'}
CATEGORIES = {'Directory', 'AI', 'Developer', 'Launch', 'Community', 'Review', 'Marketplace', 'Press', 'Newsletter', 'Design', 'Local business'}

# Classification is an editorial heuristic, not a source-provided eligibility guarantee.
PRESS_HOSTS = set('techcrunch.com boingboing.net cnet.com mashable.com in.mashable.com theverge.com venturebeat.com buzzfeednews.com readwrite.com engadget.com fastcompany.com in.pcmag.com zdnet.com arstechnica.com geekwire.com digitaltrends.com deals.thenextweb.com businessinsider.in makeuseof.com slate.com androidauthority.com infoworld.com kotaku.com pocket-lint.com appleinsider.com techhive.com techdirt.com siliconangle.com techinasia.com cloudwards.net addictivetips.com merchantmaverick.com betakit.com pocketgamer.com inc42.com toucharcade.com arcticstartup.com pando.com springwise.com tech.co startups.co.uk americaninno.com tech.eu youngupstarts.com startupvalley.news techli.com paggu.com techpluto.com new-startups.com startupdope.com redferret.net saasmag.com nextbigwhat.com projecthatch.co superbcrew.com appspy.com mactrast.com startupbeat.com startupworld.com techfaster.com theiphoneappreview.com startup88.com unboxingstartups.com stateoftech.net theapplegoogle.com coindoo.com tapscape.com thetechblock.com howbrandsarebuilt.com'.split())
COMMUNITY_HOSTS = set('reddit.com indiehackers.com dev.to news.ycombinator.com e27.co growthhackers.com lobste.rs gust.com cofounderslab.com nocodefounders.com elpha.com community.inside.com make.rs promptzone.com getmakerlog.com sideprojects.net saasalliance.io hopps.io saascommunity.com lunadio.com makerlead.com saasinsider.com'.split())
REVIEW_HOSTS = set('g2.com capterra.com getapp.com alternativeto.net saashub.com softwareadvice.com trustradius.com trustpilot.com financesonline.com crozdesk.com softwaresuggest.com spiceworks.com saasworthy.com softwareworld.co serchen.com tekpon.com saasgenius.com technologyadvice.com selecthub.com itcentralstation.com findstack.com softwaresupp.com itqlick.com featuredcustomers.com saaslist.com betterbuys.com allthatsaas.com 360quadrants.com efficient.app saasdirectory.com discovercrm.com comparasoftware.com crowdreviews.com'.split())
LAUNCH_HOSTS = set('producthunt.com betalist.com microlaunch.net fazier.com uneed.best devhunt.org open-launch.com peerlist.io peerpush.net tinylaunch.com launchigniter.com launchvault.dev launchingnext.com firsto.co openhunts.com huzzler.so shipybara.com startupfa.me'.split())
LOCAL_HOSTS = set('brownbook.net callupcontact.com merchantcircle.com indianyellowpages.com seller.indiamart.com partners.local.com amfibi.com discoverourtown.com bbb.org nextdoor.com yellowpages.com'.split())
SUSPECT_HOSTS = {'business.velp.com', 'siteiabber.com', 'fintechnews.sq', 'growthiunkie.com', 'submissionwebdirectory.cor', 'biqstartups.co', 'promoteproiect.com'}
BAD_ENDINGS = ('informati', 'advertist', 'digital-marke', 'submit-st', 'pages/cont', 'submissic', 'registratio', 'post-a-star', 'best-pr', 'submit-a-star', 'pron', 'submit-nev', '/add-', '/mybl', '/startur', '/post-a-pi', '/fintec', '/contact-ir', '/share-your-s', '/information/m', '/marketplace-', '/contributor-', '/startup-director', '/conti', '/submit-your-c', '/become-', '/submit-startu', '/category/star', '/post-', '/submit-your-st', '/advertise-', '/project-showca', '/submit-your-application-fol', '/submit-press-releast', '/submit-app-re', '/contact-t', '/busin', '/submit-app-for-revien')

def clean_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError('URL must be text')
    value = value.strip()
    if not value: return ''
    if '://' not in value: value = 'https://' + value
    p = urlsplit(value)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        raise ValueError('Use an http(s) URL without credentials')
    if any(ord(c) < 32 or c in '<>"\\' for c in value):
        raise ValueError('Invalid URL characters')
    try:
        host = p.hostname.encode('idna').decode('ascii').lower()
        port = p.port
    except (ValueError, UnicodeError) as e: raise ValueError('Invalid host or port') from e
    hostpart = f'[{host}]' if ':' in host else host
    if port: hostpart += ':' + str(port)
    return urlunsplit((p.scheme, hostpart, p.path or '/', p.query, ''))

def host_of(url: str) -> str:
    h = (urlsplit(clean_url(url)).hostname or '').lower()
    return h[4:] if h.startswith('www.') else h

def identity(url: str) -> str:
    """Deduplicate www/http variants; preserve named communities and repo lists."""
    p = urlsplit(clean_url(url)); host = host_of(url)
    if host == 'reddit.com' and re.match(r'^/r/[^/]+', p.path, re.I):
        return host + re.match(r'^/r/[^/]+', p.path, re.I).group(0).lower()
    if host == 'github.com' and len(p.path.strip('/').split('/')) >= 2:
        return host + '/' + '/'.join(p.path.strip('/').split('/')[:2]).lower()
    return host

def stable_id(key: str) -> str:
    return 'd_' + hashlib.sha256(key.encode()).hexdigest()[:16]

def infer_category(url: str, name: str) -> str:
    h = host_of(url); text = (h + ' ' + name).lower()
    if h in PRESS_HOSTS: return 'Press'
    if h in REVIEW_HOSTS: return 'Review'
    if h in LOCAL_HOSTS: return 'Local business'
    if h in COMMUNITY_HOSTS or h == 'reddit.com': return 'Community'
    if h in LAUNCH_HOSTS: return 'Launch'
    if 'marketplace' in url or h.startswith(('apps.shopify.', 'appexchange.')) or h in {'rapidapi.com', 'microacquire.com', 'acquire.com'}: return 'Marketplace'
    if h in {'morningbrew.com', 'bensbites.com', 'therundown.ai', 'webtoolsweekly.com', 'letterlist.com'}: return 'Newsletter'
    if any(x in text for x in ['design', 'landingfolio', 'land-book', 'uplabs', 'screenshots']): return 'Design'
    if h.endswith('.ai') or any(x in text for x in ['aitool', 'ai tool', 'aiagent', 'llm', 'artificial intelligence']): return 'AI'
    if any(x in text for x in ['devhunt', 'devpage', 'developer', 'opensource', 'open-source', 'github', 'devresourc', 'sourceforge', 'devpost']): return 'Developer'
    return 'Directory'

def parse_dr(value):
    if value in ('', None): return None
    if isinstance(value, bool): raise ValueError('DR must be numeric')
    n = float(value)
    if not 0 <= n <= 100: raise ValueError('DR must be between 0 and 100')
    return int(n) if n.is_integer() else n

def build_record(url, dr=None, link='unknown', price='unknown', name='', source=SOURCE, submission_url='', source_date=None, source_id='brandfactory', **extras):
    original_url = url
    url = clean_url(url); host = host_of(url); key = identity(url)
    name = name or host
    flags = []
    if host in SUSPECT_HOSTS or '[source' in name or 'malformed' in name: flags.append('Suspect source data')
    if any(url.rstrip('/').endswith(x) for x in BAD_ENDINGS) or "'" in original_url or ';' in url or '‹' in original_url:
        flags.append('Submission path may be truncated')
    if urlsplit(url).scheme == 'http': flags.append('Source uses HTTP')
    if urlsplit(url).path not in ('', '/') and not submission_url:
        flags.append('Source path requires review')
    dr = parse_dr(dr)
    if link not in LINKS: link = 'unknown'
    if price not in {'free','freemium','paid','unknown'}: price='unknown'
    record = dict(id=stable_id(key), key=key, name=name, website=url, domain=host,
        submission_url=clean_url(submission_url), category=infer_category(url,name),
        category_basis='editorial heuristic', pricing=price, reported_dr=dr,
        reported_link=link, metric_provider=('Not supplied by source' if dr is None else 'Unverified; source describes Ahrefs-style DR' if source_id=='brandfactory' else 'Ahrefs (source-reported)'),
        source_url=source, source_retrieved_at=TODAY, measured_at=None,
        source_snapshot_date=source_date, route_status='source-reported' if submission_url else 'needs-research',
        flags=flags, eligibility='', notes='', manual_priority=0, claims=[dict(source=source, source_id=source_id, retrieved_at=TODAY,
            snapshot_date=source_date, measured_at=None, dr=dr, link=link, pricing=price, url=original_url, submission_url=submission_url)],
        observed_link='unknown', evidence_url='', observed_at=None)
    record.update(extras)
    return record

def merge_records(rows):
    merged={}
    for r in rows:
        key=r['key']
        if key not in merged:
            merged[key]=r.copy(); merged[key]['claims']=list(r['claims']); continue
        old=merged[key]
        for claim in r['claims']:
            if claim not in old['claims']: old['claims'].append(claim)
        old['flags']=list(dict.fromkeys(old['flags']+r['flags']))
        if r.get('submission_url') and not old.get('submission_url'):
            old['submission_url']=r['submission_url']; old['route_status']=r['route_status']
        if 'awesome-submitlist' in r.get('source_url',''):
            for field in ('name','reported_link','pricing','eligibility','category','category_basis'):
                if r.get(field) not in (None,'','unknown'): old[field]=r[field]
            if r['reported_dr'] is not None:
                for field in ('reported_dr','metric_provider','source_url','source_snapshot_date','measured_at','source_retrieved_at'):
                    old[field]=r.get(field)
        elif old['reported_dr'] is None and r['reported_dr'] is not None:
            old['reported_dr']=r['reported_dr']; old['metric_provider']=r['metric_provider']; old['source_url']=r['source_url']
        if old['pricing']=='unknown' and r['pricing']!='unknown': old['pricing']=r['pricing']
        if old['reported_link']=='unknown' and r['reported_link']!='unknown': old['reported_link']=r['reported_link']
    for r in merged.values():
        drs={c['dr'] for c in r['claims'] if c.get('dr') is not None}
        links={c['link'] for c in r['claims'] if c.get('link') not in (None,'unknown')}
        if len(drs)>1: r['flags'].append('DR sources disagree')
        if len(links)>1: r['flags'].append('Link sources disagree')
        r['flags']=list(dict.fromkeys(r['flags']))
    return list(merged.values())

def initial_state(catalog):
    return {'schema_version':1, 'catalog':catalog, 'products':[
        {'id':'codevetter','name':'CodeVetter','url':'','tags':['Developer','AI'],'tagline':'','description':''},
        {'id':'posttrainllm','name':'PostTrainLLM','url':'','tags':['AI','Developer'],'tagline':'','description':''},
        {'id':'storagedaddy','name':'Storage Daddy','url':'','tags':['Developer'],'tagline':'','description':''}
        ], 'submissions':{}, 'active_product':'codevetter'}

if __name__ == '__main__':
    from tools.build_catalog import main
    main()
