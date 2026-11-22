import csv,hashlib,json,tempfile,unittest
from pathlib import Path
from research_gate import create_lock
from action_evidence import inspect_actions
class ActionEvidenceTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        ds={}
        for s in ('CSU','VFV'):
            p=self.root/(s+'.csv')
            with p.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['Date','Open','High','Low','Close','Volume']);w.writerows([['2026-10-01',100,102,99,101,1000],['2026-10-02',101,103,100,102,1100]])
            ds[s]={'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'exchange':'TSX','currency':'CAD','provider':'Authorized Test Feed','retrieved_on':'2026-11-04','license_note':'User supplied test'}
        self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps({'schema_version':'1.6','datasets':ds}))
        self.lock=self.root/'lock.json';create_lock(self.manifest,self.lock)
        self.evidence=self.root/'events.json'
        self.obj={'schema_version':'1.8','manifest_sha256':hashlib.sha256(self.manifest.read_bytes()).hexdigest(),'price_policy':'raw_unadjusted','datasets':{s:{'source':'Issuer records','source_url':'https://example.org/events','retrieved_on':'2026-11-04','coverage_attestation':'complete_claimed','events':[]} for s in ('CSU','VFV')}}
        self.save()
    def save(self):self.evidence.write_text(json.dumps(self.obj))
    def test_empty_events_still_not_approved(self):
        r=inspect_actions(self.manifest,self.lock,self.evidence);self.assertFalse(r['research_approved']);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertEqual(len(r['issues']),2)
    def test_valid_dividend(self):
        self.obj['datasets']['VFV']['events']=[{'type':'dividend','ex_date':'2026-10-01','pay_date':'2026-10-02','amount_per_share':'0.12','currency':'CAD'}];self.save()
        self.assertEqual(inspect_actions(self.manifest,self.lock,self.evidence)['event_counts']['VFV']['dividends'],1)
    def test_valid_split(self):
        self.obj['datasets']['CSU']['events']=[{'type':'split','ex_date':'2026-10-01','numerator':2,'denominator':1}];self.save()
        self.assertEqual(inspect_actions(self.manifest,self.lock,self.evidence)['event_counts']['CSU']['splits'],1)
    def test_reject_adjusted_price_policy(self):
        self.obj['price_policy']='adjusted';self.save()
        with self.assertRaises(ValueError):inspect_actions(self.manifest,self.lock,self.evidence)
    def test_reject_stale_manifest_hash(self):
        self.obj['manifest_sha256']='0'*64;self.save()
        with self.assertRaises(ValueError):inspect_actions(self.manifest,self.lock,self.evidence)
    def test_reject_duplicate(self):
        e={'type':'split','ex_date':'2026-10-01','numerator':2,'denominator':1}
        self.obj['datasets']['CSU']['events']=[e,e];self.save()
        with self.assertRaises(ValueError):inspect_actions(self.manifest,self.lock,self.evidence)
    def test_reject_negative_dividend(self):
        self.obj['datasets']['VFV']['events']=[{'type':'dividend','ex_date':'2026-10-01','pay_date':'2026-10-02','amount_per_share':'-1','currency':'CAD'}];self.save()
        with self.assertRaises(ValueError):inspect_actions(self.manifest,self.lock,self.evidence)
    def test_out_of_coverage_flag(self):
        self.obj['datasets']['CSU']['events']=[{'type':'split','ex_date':'2026-09-01','numerator':2,'denominator':1}];self.save()
        self.assertTrue(any('outside price coverage' in i for i in inspect_actions(self.manifest,self.lock,self.evidence)['issues']))
    def test_reject_pay_before_ex(self):
        self.obj['datasets']['VFV']['events']=[{'type':'dividend','ex_date':'2026-10-02','pay_date':'2026-10-01','amount_per_share':'0.12','currency':'CAD'}];self.save()
        with self.assertRaises(ValueError):inspect_actions(self.manifest,self.lock,self.evidence)
