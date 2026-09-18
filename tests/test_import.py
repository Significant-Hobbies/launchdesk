import json, tempfile, unittest
from pathlib import Path
from catalog import build_record, initial_state
from store import validate_state
from tools.import_catalog import enrich, load_records

class ImportTests(unittest.TestCase):
    def seed(self):
        return initial_state([build_record('https://example.com',10,'unknown',name='Example')])
    def test_enrichment_keeps_submission(self):
        s=self.seed(); i=s['catalog'][0]['id']
        s['submissions']['codevetter::'+i]={'status':'live','notes':'Do not lose'}
        new,r=enrich(s,[{'domain':'example.com','dr':'0'}],'https://ahrefs.com/','2026-09-18',True)
        self.assertEqual(new['catalog'][0]['reported_dr'],0)
        self.assertEqual(new['submissions'],s['submissions'])
        self.assertEqual(s['catalog'][0]['reported_dr'],10)
        self.assertEqual(r['updated'],1)
    def test_bad_rows_are_atomic(self):
        s=self.seed()
        n,r=enrich(s,[{'domain':'example.com','dr':55,'submission_url':'https://user:pass@example.com'}],'https://source.example')
        self.assertEqual(n,s);self.assertEqual(r['skipped'],1)
    def test_unknown_dr_not_zero(self):
        n,r=enrich(self.seed(),[{'domain':'other.example'}],'https://source.example')
        self.assertIsNone(n['catalog'][-1]['reported_dr']);self.assertEqual(r['added'],1)
    def test_dr_only_unknown_domain_skipped(self):
        n,r=enrich(self.seed(),[{'domain':'other.example','dr':55}],'https://source.example',dr_only=True)
        self.assertEqual(r['skipped'],1);self.assertEqual(len(n['catalog']),1)
    def test_duplicate_headers_and_da_rejected(self):
        for text in ['domain,dr,dr\nx,1,2\n','domain,da\nx,99\n']:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'a.csv';p.write_text(text)
                with self.assertRaises(ValueError):load_records(p)
    def test_incorrect_identity_rejected(self):
        s=self.seed();s['catalog'][0]['key']='made-up'
        with self.assertRaises(ValueError):validate_state(s)
