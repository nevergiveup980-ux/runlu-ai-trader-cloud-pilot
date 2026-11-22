import unittest
from datetime import datetime,timezone,timedelta
from vendor_evidence import review_evidence,EvidenceError,CATEGORIES
NOW='2026-11-06T18:00:00Z'
def record(**kwargs):
    r=dict(vendor='Example Vendor',category='tsx_coverage',source_url='https://example.com/tsx',checked_at_utc='2026-11-05T18:00:00Z',excerpt='Example text, not verified',reviewer='Researcher')
    r.update(kwargs);return r
class TestEvidence(unittest.TestCase):
    def test_review(self):
        x=review_evidence([record()],now=NOW);self.assertFalse(x['trading_authorized']);self.assertEqual(len(x['missing_categories']['Example Vendor']),7)
    def test_deterministic(self):self.assertEqual(review_evidence([record()],now=NOW)['sha256'],review_evidence([record()],now=NOW)['sha256'])
    def test_stale(self):self.assertEqual(review_evidence([record(checked_at_utc='2026-01-01T00:00:00Z')],now=NOW)['evidence'][0]['status'],'STALE_RECHECK_REQUIRED')
    def test_future(self):
        with self.assertRaises(EvidenceError):review_evidence([record(checked_at_utc='2027-01-01T00:00:00Z')],now=NOW)
    def test_insecure(self):
        with self.assertRaises(EvidenceError):review_evidence([record(source_url='http://example.com')],now=NOW)
    def test_credentials(self):
        with self.assertRaises(EvidenceError):review_evidence([record(source_url='https://x:y@example.com')],now=NOW)
    def test_category(self):
        with self.assertRaises(EvidenceError):review_evidence([record(category='fake')],now=NOW)
    def test_excerpt(self):
        with self.assertRaises(EvidenceError):review_evidence([record(excerpt='')],now=NOW)
    def test_reviewer(self):
        with self.assertRaises(EvidenceError):review_evidence([record(reviewer='')],now=NOW)
    def test_duplicate(self):
        with self.assertRaises(EvidenceError):review_evidence([record(),record()],now=NOW)
    def test_full_checklist_never_authorized(self):
        x=review_evidence([record(category=c,source_url='https://example.com/'+c) for c in sorted(CATEGORIES)],now=NOW)
        self.assertEqual(x['missing_categories']['Example Vendor'],[]);self.assertFalse(x['license_verified'])
    def test_naive_time(self):
        with self.assertRaises(EvidenceError):review_evidence([record(checked_at_utc='2026-11-05T00:00:00')],now=NOW)
