import unittest, tempfile, json
from pathlib import Path
from source_provenance import receipt,verify,file_receipt,ProvenanceError

class ReceiptTests(unittest.TestCase):
    def make(self):return receipt(b'[{"date":"2026-11-01"}]',symbol='CSU',source_kind='USER_FILE',source_label='local fixture',captured_at='2026-11-07T12:00:00-06:00')
    def test_verify(self):self.assertTrue(verify(b'[{"date":"2026-11-01"}]',self.make()))
    def test_payload_tamper(self):
        with self.assertRaises(ProvenanceError):verify(b'changed',self.make())
    def test_receipt_tamper(self):
        x=self.make();x['source_label']='other'
        with self.assertRaises(ProvenanceError):verify(b'[{"date":"2026-11-01"}]',x)
    def test_authentication_cannot_be_forged(self):
        x=self.make();x['source_authenticated']=True
        with self.assertRaises(ProvenanceError):verify(b'[{"date":"2026-11-01"}]',x)
    def test_reproducible(self):self.assertEqual(self.make(),self.make())
    def test_utc(self):self.assertEqual(self.make()['captured_at'],'2026-11-07T18:00:00+00:00')
    def test_naive_time(self):
        with self.assertRaises(ProvenanceError):receipt(b'x',symbol='CSU',source_kind='USER_FILE',source_label='a',captured_at='2026-11-07T12:00:00')
    def test_bad_symbol(self):
        with self.assertRaises(ProvenanceError):receipt(b'x',symbol='BAD',source_kind='USER_FILE',source_label='a',captured_at='2026-11-07T12:00:00Z')
    def test_bad_kind(self):
        with self.assertRaises(ProvenanceError):receipt(b'x',symbol='CSU',source_kind='SCRAPED',source_label='a',captured_at='2026-11-07T12:00:00Z')
    def test_empty(self):
        with self.assertRaises(ProvenanceError):receipt(b'',symbol='CSU',source_kind='USER_FILE',source_label='a',captured_at='2026-11-07T12:00:00Z')
    def test_control_char(self):
        with self.assertRaises(ProvenanceError):receipt(b'x',symbol='CSU',source_kind='USER_FILE',source_label='a\nsecret',captured_at='2026-11-07T12:00:00Z')
    def test_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'raw.json');p.write_bytes(b'[]')
            x=file_receipt(p,symbol='VFV',source_label='manual',captured_at='2026-11-07T12:00:00Z')
            self.assertTrue(verify(b'[]',x))
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'raw');p.write_bytes(b'[]');q=Path(d,'link');q.symlink_to(p)
            with self.assertRaises(ProvenanceError):file_receipt(q,symbol='VFV',source_label='manual',captured_at='2026-11-07T12:00:00Z')
    def test_extra_field(self):
        x=self.make();x['license_note']='approved'
        with self.assertRaises(ProvenanceError):verify(b'[{"date":"2026-11-01"}]',x)

if __name__=='__main__':unittest.main()
