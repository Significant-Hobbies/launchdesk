#!/usr/bin/env python3
"""Compile sourced facts, quarantine suspect rows, and generate the offline app."""
from __future__ import annotations
import csv, io, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import ROOT, SOURCE, TODAY, build_record, merge_records, initial_state, host_of

# Conservative editorial exclusions: an upstream list can accidentally capture
# a badge, a software product, an author profile, or an affiliate book link.
# These are retained in the audit data, not recommended as submission targets.
NON_DESTINATIONS=set('awesome.re plausible.io genpage.ai junia.ai makelanding.ai poper.ai simple.ink adsby.co astronuts.io backlinkgpt.com boilermat.es byedispute.com charmui.com chromekit.dev clobbr.app cocomail.io codesnap.dev competitoresearch.com coolors.co creatica.app daito.io dashcam.io designbuddy.net detachless.com faqpopup.com fastfluttertemplate.com flows.sh gdprvalidator.eu ghostkode.com hydrozen.io iconbuddy.com indie-starter.dev kobble.io larafast.com launchfa.st litefeedback.com liveupx.com marvinbot.com metaexplorer.co modalcast.com nextjet.dev outblog.me picassoapp.ca pika.style pirsch.io poopup.co pulsetic.com qrcode.ing rankonbing.com rapidlaunch.it referralapi.com salespopup.io scaletozeroaws.com searchsocket.com seo-programming.com sharpapi.com shipaifast.com shipped.club snowball.club speedmeter.app staarter.dev stablepush.dev star-history.com static.app suremeet.io swiftylaun.ch tapmention.com tinyimg.cc unicornplatform.com useplunk.com wrapfa.st xhost.live zenvoice.io 30x500.com alexwest.co amzn.to anchor.fm createanything.com devmarketing.xyz'.split())

def main():
    rows=[]; errors=[]
    specs=[('brandfactory.tsv',SOURCE,'brandfactory',None),('submitlist.tsv','https://github.com/alvinunreal/awesome-submitlist/blob/main/data/destinations.json','submitlist','2026-09-14'),('launchdb.tsv','https://github.com/theshubh77/awesome-saas-directories','launchdb',None),('extra-routes.tsv','https://github.com/rushout09/directory-submission-sites','route-source',None),('ai-directories.tsv','https://github.com/best-of-ai/ai-directories/blob/main/README.md','bestofai',None)]
    for filename,source,sid,stamp in specs:
        path=ROOT/'data'/'sources'/filename
        if not path.exists(): continue
        for no,line in enumerate(path.read_text().splitlines(),1):
            if not line.strip() or line.startswith('#'): continue
            try:
                cells=line.split('|')
                if len(cells)<5: raise ValueError('Not enough columns')
                url,dr,link,price,name=cells[:5]
                submission=cells[5] if len(cells)>5 else ''
                category=cells[6] if len(cells)>6 else ''
                eligibility=cells[7] if len(cells)>7 else ''
                row=build_record(url,dr,{'D':'follow','N':'nofollow','U':'ugc','S':'sponsored','M':'mixed'}.get(link,'unknown'),{'F':'free','M':'freemium','P':'paid'}.get(price,'unknown'),name,source,submission,stamp,sid)
                row['eligibility']=eligibility
                if category: row['category']=category; row['category_basis']='source category / editorial adaptation'
                if sid in {'launchdb','route-source','bestofai'}: row['metric_provider']='Source-reported DR; provider not independently verified' if sid=='launchdb' else 'No DR supplied by this source'
                row['quarantined']=row['domain'] in NON_DESTINATIONS or any('Suspect source data'==f for f in row['flags'])
                if row['domain'] in NON_DESTINATIONS: row['flags'].append('Possible non-destination captured by source; excluded')
                if not eligibility and row['category']=='Press': row['eligibility']='Editorial/media prospect, not a guaranteed submission form. Find a relevant angle and the current pitch policy.'
                rows.append(row)
            except Exception as e: errors.append({'file':filename,'line':no,'error':str(e),'raw':line})
    catalog=merge_records(rows)
    for r in catalog:
        # A second source with an actual route can resolve a conservative
        # non-destination exclusion, but never silently clear suspect-URL flags.
        if r.get('submission_url') and not any(f=='Suspect source data' for f in r['flags']):
            r['quarantined']=False
    catalog.sort(key=lambda r:r['name'].casefold())
    data=ROOT/'data'; data.mkdir(exist_ok=True)
    (data/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    active=[r for r in catalog if not r.get('quarantined')]
    manifest={'generated_at':TODAY,'source_rows':len(rows),'catalog_records':len(catalog),'active_prospects':len(active),'excluded_records':len(catalog)-len(active),'reported_dr_known':sum(r['reported_dr'] is not None for r in active),'reported_link_known':sum(r['reported_link']!='unknown' for r in active),'submission_routes':sum(bool(r['submission_url']) for r in active),'independently_verified_seed_rows':0,'metric_measurement_dates_known':sum(bool(r.get('measured_at')) for r in active),'source_conflicts':sum(any('disagree' in f for f in r['flags']) for r in active),'build_errors':errors}
    (data/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    headers=['id','name','website','submission_url','domain','reported_dr','reported_link','category','pricing','metric_provider','source_url','source_retrieved_at','source_snapshot_date','measured_at','route_status','eligibility','flags','quarantined']
    def write_csv(path,records):
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f); w.writerow(headers)
            for r in records:
                out=[]
                for k in headers:
                    v=r.get(k); v='; '.join(v) if isinstance(v,list) else '' if v is None else str(v)
                    if v.lstrip().startswith(('=','+','-','@')): v="'"+v
                    out.append(v)
                w.writerow(out)
    write_csv(data/'destinations.csv',active)
    write_csv(data/'excluded-source-records.csv',[r for r in catalog if r.get('quarantined')])
    write_csv(data/'all-source-records.csv',catalog)
    seed='window.LAUNCHDESK_SEED='+json.dumps(initial_state(catalog),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+';\n'
    (ROOT/'web'/'seed.js').write_text(seed)
    html=(ROOT/'web'/'index.html').read_text()
    html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+(ROOT/'web'/'styles.css').read_text()+'</style>')
    html=html.replace('<script src="seed.js"></script>','<script>'+seed+'</script>')
    html=html.replace('<script src="app.js"></script>','<script>'+(ROOT/'web'/'app.js').read_text().replace('</script','<\\/script')+'</script>')
    (ROOT/'LaunchDesk.html').write_text(html)
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
