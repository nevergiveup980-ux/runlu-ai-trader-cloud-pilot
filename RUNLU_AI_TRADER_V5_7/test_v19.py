import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile, json
from evidence_reconcile import reconcile

class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.base={'schema_version':'1.8','manifest_sha256':'a'*64,'price_policy':'raw_unadjusted','datasets':{
            sym:{'source':'Provider A','source_url':'https://a.example/'+sym,'retrieved_on':'2026-11-04','coverage_attestation':'complete_claimed',
                 'events':[{'type':'split','ex_date':'2025-01-02','numerator':2,'denominator':1}]} for sym in ('CSU','VFV')}}
    def run_compare(self,alter=None):
        import copy
        a=copy.deepcopy(self.base);b=copy.deepcopy(self.base)
        for sym in ('CSU','VFV'):
            b['datasets'][sym]['source']='Provider B';b['datasets'][sym]['source_url']='https://b.example/'+sym
        if alter:alter(a,b)
        p=self.root/'a.json';q=self.root/'b.json';p.write_text(json.dumps(a));q.write_text(json.dumps(b))
        with patch('evidence_reconcile.inspect_actions',return_value={'issues':[]}):
            return reconcile('manifest','lock',p,q)
    def test_agreement_not_approval(self):
        r=self.run_compare();self.assertEqual(r['status'],'AGREEMENT_REQUIRES_INDEPENDENT_REVIEW');self.assertFalse(r['research_approved'])
    def test_event_missing(self):
        r=self.run_compare(lambda a,b:b['datasets']['CSU']['events'].clear());self.assertIn('missing',str(r['discrepancies']))
    def test_ratio_equivalence(self):
        r=self.run_compare(lambda a,b:b['datasets']['CSU']['events'][0].update(numerator=4,denominator=2));self.assertFalse(r['discrepancies'])
    def test_ratio_conflict(self):
        r=self.run_compare(lambda a,b:b['datasets']['CSU']['events'][0].update(numerator=3));self.assertIn('conflict',str(r['discrepancies']))
    def test_same_source(self):
        r=self.run_compare(lambda a,b:b['datasets']['CSU'].update(source=a['datasets']['CSU']['source']));self.assertIn('not distinct',str(r['discrepancies']))
    def test_empty_events(self):
        r=self.run_compare(lambda a,b:[x['datasets']['VFV']['events'].clear() for x in (a,b)]);self.assertIn('no events',str(r['discrepancies']))
    def test_incomplete(self):
        r=self.run_compare(lambda a,b:b['datasets']['CSU'].update(coverage_attestation='unknown'));self.assertIn('unknown',str(r['discrepancies']))
    def test_identical_file_rejected(self):
        p=self.root/'same.json';p.write_text(json.dumps(self.base))
        with self.assertRaisesRegex(ValueError,'distinct'):reconcile('m','l',p,p)
