import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from research_gate import create_lock, verify_lock

class ResearchGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); datasets={}
        for symbol in ('CSU','VFV'):
            path=self.root/f'{symbol}.csv'
            with path.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['Date','Open','High','Low','Close','Volume'])
                w.writerow(['2026-10-01',100,102,99,101,1000]);w.writerow(['2026-10-02',101,103,100,102,1100])
            datasets[symbol]={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'exchange':'TSX','currency':'CAD','provider':'Licensed Feed X','retrieved_on':'2026-11-04',
                'license_note':'User confirms research rights'}
        self.manifest=self.root/'manifest.json';self.lock=self.root/'lock.json'
        self.manifest.write_text(json.dumps({'schema_version':'1.6','datasets':datasets}))
    def test_create_and_verify(self):
        x=create_lock(self.manifest,self.lock)
        self.assertFalse(x['research_approved'])
        self.assertEqual(verify_lock(self.manifest,self.lock)['common_sessions'],2)
    def test_csv_mutation_fails(self):
        create_lock(self.manifest,self.lock)
        (self.root/'CSU.csv').write_text((self.root/'CSU.csv').read_text()+'\n')
        with self.assertRaises(ValueError):verify_lock(self.manifest,self.lock)
    def test_manifest_mutation_fails(self):
        create_lock(self.manifest,self.lock)
        self.manifest.write_text(self.manifest.read_text()+' ')
        with self.assertRaises(ValueError):verify_lock(self.manifest,self.lock)
    def test_lock_mutation_fails(self):
        create_lock(self.manifest,self.lock)
        obj=json.loads(self.lock.read_text());obj['common_sessions']=999;self.lock.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):verify_lock(self.manifest,self.lock)
    def test_missing_provider_fails(self):
        obj=json.loads(self.manifest.read_text());obj['datasets']['CSU']['provider']='  ';self.manifest.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):create_lock(self.manifest,self.lock)
    def test_placeholder_provider_fails(self):
        obj=json.loads(self.manifest.read_text());obj['datasets']['CSU']['provider']='unknown';self.manifest.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):create_lock(self.manifest,self.lock)
    def test_review_findings_block(self):
        path=self.root/'CSU.csv';lines=path.read_text().replace('101,103,100,102,1100','200,203,199,202,1100');path.write_text(lines)
        obj=json.loads(self.manifest.read_text());obj['datasets']['CSU']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();self.manifest.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):create_lock(self.manifest,self.lock)
    def test_refuse_overwrite_input(self):
        with self.assertRaises(ValueError):create_lock(self.manifest,self.manifest)
