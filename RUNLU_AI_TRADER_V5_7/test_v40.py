import unittest
from dataclasses import replace
from vendor_readiness import VendorRecord, assess_vendors, VendorReadinessError

def vendor(name,feed):
    return VendorRecord(name,'https://example.com/docs','https://example.com/terms',True,True,True,900,'CAD','contract-001',feed)

class VendorTests(unittest.TestCase):
    def test_review_only(self):
        r=assess_vendors([vendor('A','Feed A'),vendor('B','Feed B')]); self.assertEqual(r['status'],'MANUAL_DUE_DILIGENCE_REQUIRED'); self.assertFalse(r['trading_authorized'])
    def test_repeatable_hash(self):
        x=[vendor('A','A'),vendor('B','B')]; self.assertEqual(assess_vendors(x)['sha256'],assess_vendors(x)['sha256'])
    def test_duplicate_vendor(self): self.assertEqual(assess_vendors([vendor('A','X'),vendor('A','Y')])['status'],'BLOCKED')
    def test_same_feed(self): self.assertEqual(assess_vendors([vendor('A','X'),vendor('B','X')])['status'],'BLOCKED')
    def test_missing_contract(self): self.assertEqual(assess_vendors([replace(vendor('A','A'),legal_terms_url='http://example.com'),vendor('B','B')])['status'],'BLOCKED')
    def test_tsx_missing(self): self.assertEqual(assess_vendors([replace(vendor('A','A'),tsx_coverage_confirmed=False),vendor('B','B')])['status'],'BLOCKED')
    def test_automation_missing(self): self.assertEqual(assess_vendors([replace(vendor('A','A'),automated_use_permitted=False),vendor('B','B')])['status'],'BLOCKED')
    def test_redistribution_missing(self): self.assertEqual(assess_vendors([replace(vendor('A','A'),redistribution_rights_confirmed=False),vendor('B','B')])['status'],'BLOCKED')
    def test_bad_delay(self): self.assertEqual(assess_vendors([replace(vendor('A','A'),delay_seconds=-1),vendor('B','B')])['status'],'BLOCKED')
    def test_bad_currency(self): self.assertEqual(assess_vendors([replace(vendor('A','A'),currency='USD'),vendor('B','B')])['status'],'BLOCKED')
    def test_invalid_count(self):
        with self.assertRaises(VendorReadinessError): assess_vendors([vendor('A','A')])
    def test_missing_feed(self): self.assertEqual(assess_vendors([replace(vendor('A','A'),underlying_feed=''),vendor('B','B')])['status'],'BLOCKED')
