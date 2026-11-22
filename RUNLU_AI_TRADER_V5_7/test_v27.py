import unittest
from agent_runtime import ResearchContext, run_council, AgentError, ROLE_SEQUENCE

DIGEST='a'*64
CTX=ResearchContext('VFV',DIGEST,'source-1',True,True)

def provider(role,ctx,notes):
    out={'message':f'{role} reviewed {ctx.symbol}'}
    if role=='Pitch':
        out['proposal']={'symbol':'VFV','bucket':'core','strategy':'cash_equity',
            'cash_required_usd':'50.00','thesis':'test only','evidence_id':'source-1','max_loss_usd':'50.00'}
    return out

class V27Tests(unittest.TestCase):
    def test_seven_roles_and_audit(self):
        a=run_council(CTX,provider); self.assertEqual(len(a['roles']),7)
        self.assertEqual([x['role'] for x in a['roles']],list(ROLE_SEQUENCE))
        self.assertEqual(len(a['audit_sha256']),64)
    def test_no_live_authorization_even_if_verified(self):
        a=run_council(CTX,provider)
        self.assertEqual(a['outcome']['status'],'BLOCKED')
        self.assertFalse(a['outcome']['order_submitted'])
    def test_bad_digest(self):
        with self.assertRaises(AgentError): run_council(ResearchContext('VFV','bad','source-1'),provider)
    def test_provenance_mismatch(self):
        def fake(role,ctx,notes):
            o=provider(role,ctx,notes)
            if role=='Pitch':o['proposal']['evidence_id']='fake'
            return o
        a=run_council(CTX,fake); self.assertEqual(a['outcome']['status'],'BLOCKED')
        self.assertIn('Pitch',a['outcome']['reasons'][0])
    def test_provider_invalid_response(self):
        a=run_council(CTX,lambda *args: {'message':' '})
        self.assertEqual(a['outcome']['status'],'BLOCKED')
    def test_missing_market_verification(self):
        a=run_council(ResearchContext('VFV',DIGEST,'source-1'),provider)
        self.assertEqual(a['outcome']['status'],'BLOCKED')
    def test_no_budget_reservation_when_blocked(self):
        a=run_council(CTX,provider)
        self.assertEqual(a['budget']['buckets']['core']['reserved_usd'],'0')
    def test_deterministic_audit(self):
        self.assertEqual(run_council(CTX,provider)['audit_sha256'],run_council(CTX,provider)['audit_sha256'])
    def test_reject_oversize_text(self):
        a=run_council(CTX,lambda role,ctx,notes:{'message':'x'*2001})
        self.assertEqual(a['outcome']['status'],'BLOCKED')
