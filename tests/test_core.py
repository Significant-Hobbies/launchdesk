import copy,json,sys,socket,threading,unittest,tempfile,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import clean_url,identity,parse_dr,build_record,merge_records,initial_state
from safeweb import analyze_html,public_target,FetchError,Page,verify
from store import Store,ConflictError,validate_state
from server import AppServer

def row(url='https://example.com/'):
 return build_record(url,0,'unknown',name='Example')

class CatalogTests(unittest.TestCase):
 def test_missing_and_zero(self):
  self.assertIsNone(parse_dr(''));self.assertEqual(parse_dr(0),0)
 def test_bad_dr(self):
  for x in [-1,101,float('nan'),float('inf'),True]:
   with self.subTest(x=x),self.assertRaises(ValueError):parse_dr(x)
 def test_identity(self):
  self.assertEqual(identity('http://www.example.com/a'),identity('https://example.com/b'))
  self.assertNotEqual(identity('https://reddit.com/r/a'),identity('https://reddit.com/r/b'))
 def test_bad_url(self):
  for u in ['javascript://alert(1)','https://user:password@example.com','https://example.com/<x>','ftp://example.com']:
   with self.subTest(u=u),self.assertRaises(ValueError):clean_url(u)
 def test_conflicts_preserve_claims(self):
  a=row();b=build_record('http://www.example.com',70,'nofollow',source='https://source.example/a')
  m=merge_records([a,b]);self.assertEqual(len(m),1);self.assertEqual(len(m[0]['claims']),2);self.assertIn('DR sources disagree',m[0]['flags'])

class LinkTests(unittest.TestCase):
 def scan(self,h,headers=None):return analyze_html(h,'https://directory.example/list','https://product.example',headers)
 def test_follow(self):self.assertEqual(self.scan('<a href="https://product.example">p</a>')['link_type'],'follow')
 def test_nofollow(self):self.assertEqual(self.scan('<a href="https://product.example" rel="nofollow noopener">p</a>')['link_type'],'nofollow')
 def test_ugc(self):self.assertEqual(self.scan('<a href="https://product.example" rel="ugc">p</a>')['link_type'],'ugc')
 def test_sponsored(self):self.assertEqual(self.scan('<a href="https://product.example" rel="sponsored">p</a>')['link_type'],'sponsored')
 def test_mixed(self):self.assertEqual(self.scan('<a href="https://product.example"></a><a href="https://product.example/a" rel="nofollow"></a>')['link_type'],'mixed')
 def test_page_directives(self):
  r=self.scan('<meta name="robots" content="noindex,nofollow"><a href="https://product.example"></a>')
  self.assertEqual(r['link_type'],'nofollow');self.assertTrue(r['page_noindex'])
 def test_header_directives(self):self.assertEqual(self.scan('<a href="https://product.example"></a>',{'x-robots-tag':'nofollow'})['link_type'],'nofollow')
 def test_deceptive_domain(self):self.assertEqual(self.scan('<a href="https://product.example.attacker.com"></a>')['link_type'],'not_found')
 def test_base_and_subdomain(self):self.assertEqual(self.scan('<base href="https://app.product.example/"><a href="/x"></a>')['link_type'],'follow')
 def test_protocol_relative(self):self.assertEqual(self.scan('<a href="//product.example/a"></a>')['link_type'],'follow')
 def test_no_links_caveat(self):self.assertIn('JavaScript',self.scan('<div>app</div>')['message'])
 def test_private_dns(self):
  for ip in ['127.0.0.1','10.0.0.1','169.254.169.254','::1','::ffff:127.0.0.1']:
   with self.subTest(ip=ip),patch('safeweb.socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))]),self.assertRaises(FetchError):public_target('https://product.example')
 def test_mixed_public_private_dns(self):
  with patch('safeweb.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('127.0.0.1',443))]),self.assertRaises(FetchError):public_target('https://product.example')
 def test_public_dns_pinned_result(self):
  with patch('safeweb.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):self.assertEqual(public_target('https://product.example')[-1],'8.8.8.8')
 def test_local_and_port(self):
  for u in ['http://localhost/','http://foo.local/','https://example.com:8080/']:
   with self.subTest(u=u),self.assertRaises(FetchError):public_target(u)
 def test_blocked_is_unknown(self):
  with patch('safeweb.robots_policy',return_value=(True,1,'allowed')),patch('safeweb.pace'),patch('safeweb.fetch_public',return_value=Page('https://d.example',403,{'content-type':'text/html'},'',[])):
   self.assertEqual(verify('https://d.example','https://product.example')['link_type'],'unknown')
 def test_robots_denied_no_fetch(self):
  with patch('safeweb.robots_policy',return_value=(False,1,'Denied')),patch('safeweb.fetch_public') as f:
   self.assertEqual(verify('https://d.example','https://product.example')['link_type'],'unknown');f.assert_not_called()
 def test_redirect_guard_supplied_and_denies(self):
  def fake_fetch(url,redirect_guard=None,**kwargs):
   self.assertIsNotNone(redirect_guard);redirect_guard('https://blocked.example/list');raise AssertionError('Must stop')
  with patch('safeweb.robots_policy',side_effect=[(True,1,'Allowed'),(False,1,'Denied')]),patch('safeweb.pace'),patch('safeweb.fetch_public',side_effect=fake_fetch):
   r=verify('https://d.example','https://product.example');self.assertEqual(r['link_type'],'unknown');self.assertIn('Redirect target',r['message'])

class StorageTests(unittest.TestCase):
 def test_atomic_revisions_persistence_and_recovery(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'workspace.sqlite3';store=Store(p,[row()]);rev,s=store.read();self.assertEqual(rev,0)
   s['products'][0]['tagline']='Before save';self.assertEqual(store.write(s,rev),1)
   with self.assertRaises(ConflictError):store.write(s,0)
   self.assertEqual(Store(p,[row()]).read()[1]['products'][0]['tagline'],'Before save')
   self.assertEqual(json.loads((Path(tmp)/'last-good-workspace.json').read_text())['products'][0]['tagline'],'')
 def test_duplicate_identity_rejected(self):
  s=initial_state([row()]);r=copy.deepcopy(s['catalog'][0]);r['id']='other';s['catalog'].append(r)
  with self.assertRaises(ValueError):validate_state(s)
 def test_unknown_submission_rejected(self):
  s=initial_state([row()]);s['submissions']['bad::bad']={'status':'live'}
  with self.assertRaises(ValueError):validate_state(s)
 def test_product_scoped_status(self):
  s=initial_state([row()]);i=s['catalog'][0]['id'];s['submissions'][f'codevetter::{i}']={'status':'queued'};s['submissions'][f'posttrainllm::{i}']={'status':'live'};validate_state(s)
  self.assertNotEqual(s['submissions'][f'codevetter::{i}'],s['submissions'][f'posttrainllm::{i}'])

class APITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.server=AppServer(0,Store(Path(self.tmp.name)/'db.sqlite3',[row()]));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def req(self,path='/',method='GET',headers=None,data=None):
  try:
   with urllib.request.urlopen(urllib.request.Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers=headers or {},method=method),timeout=5) as r:return r.status,r.read()
  except urllib.error.HTTPError as e:return e.code,e.read()
 def test_static_whitelist(self):
  self.assertEqual(self.req('/')[0],200);self.assertEqual(self.req('/data/workspace.sqlite3')[0],404);self.assertEqual(self.req('/../store.py')[0],404)
 def test_host_origin_rejection(self):
  self.assertEqual(self.req('/api/workspace',headers={'Host':'attacker.example'})[0],403);self.assertEqual(self.req('/api/workspace',headers={'Origin':'https://attacker.example'})[0],403)
 def test_token_and_revision(self):
  code,body=self.req('/api/workspace');j=json.loads(body);s=j['state'];h={'Content-Type':'application/json','If-Match':'0'}
  self.assertEqual(self.req('/api/workspace','PUT',h,s)[0],403);h['X-LaunchDesk-Token']=j['token'];self.assertEqual(self.req('/api/workspace','PUT',h,s)[0],200);self.assertEqual(self.req('/api/workspace','PUT',h,s)[0],409)

if __name__=='__main__':unittest.main(verbosity=2)
