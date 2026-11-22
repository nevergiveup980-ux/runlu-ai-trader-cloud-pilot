import csv, hashlib, json, tempfile, unittest
from pathlib import Path
from intake_bundle import verify_bundle

class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        data={}
        for symbol in ('CSU','VFV'):
            p=self.root/f'{symbol}.csv'
            with p.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['Date','Open','High','Low','Close','Volume'])
                w.writerow(['2026-11-02',100,102,99,101,1000]);w.writerow(['2026-11-03',101,103,100,102,1200])
            data[symbol]={'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'exchange':'TSX','currency':'CAD','provider':'SAMPLE ONLY','retrieved_on':'2026-11-04','license_note':'synthetic test'}
        self.manifest=self.root/'manifest.json';self.raw={'schema_version':'1.6','datasets':data};self.save()
    def save(self):self.manifest.write_text(json.dumps(self.raw))
    def test_valid_structure(self):
        r=verify_bundle(self.manifest);self.assertEqual(r['status'],'STRUCTURE_CHECKS_PASSED');self.assertEqual(r['common_sessions'],2);self.assertFalse(r['research_approved'])
    def test_tamper(self):
        (self.root/'CSU.csv').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'SHA-256'):verify_bundle(self.manifest)
    def test_wrong_currency(self):
        self.raw['datasets']['VFV']['currency']='USD';self.save()
        with self.assertRaisesRegex(ValueError,'TSX/CAD'):verify_bundle(self.manifest)
    def test_missing_symbol(self):
        del self.raw['datasets']['CSU'];self.save()
        with self.assertRaisesRegex(ValueError,'exactly CSU and VFV'):verify_bundle(self.manifest)
    def test_path_escape(self):
        self.raw['datasets']['CSU']['file']='../outside.csv';self.save()
        with self.assertRaisesRegex(ValueError,'escapes'):verify_bundle(self.manifest)
    def test_calendar_review(self):
        p=self.root/'VFV.csv';p.write_text(p.read_text().replace('2026-11-03','2026-11-04'))
        self.raw['datasets']['VFV']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();self.save()
        with self.assertRaisesRegex(ValueError,'at least two common'):verify_bundle(self.manifest)
    def test_price_anomaly_blocks(self):
        p=self.root/'CSU.csv';p.write_text(p.read_text().replace('101,103,100,102,1200','201,203,200,202,1200'))
        self.raw['datasets']['CSU']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();self.save()
        self.assertEqual(verify_bundle(self.manifest)['status'],'BLOCKED_REVIEW_REQUIRED')
        self.assertEqual(verify_bundle(self.manifest,allow_review=True)['status'],'REVIEW_REQUIRED')
    def test_invalid_manifest(self):
        self.raw['schema_version']='wrong';self.save()
        with self.assertRaisesRegex(ValueError,'schema'):verify_bundle(self.manifest)
