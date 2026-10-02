import copy
import json
import unittest
from pathlib import Path
from case_app import trace_case, decision_record

class CaseAppTests(unittest.TestCase):
    def setUp(self):
        self.case=json.loads((Path(__file__).resolve().parents[1]/'examples/sample_case.json').read_text())
        self.review=dict(decision='draft_hold',reviewer='Test reviewer',authority_reference='TEST',rationale='Synthetic evidence checked',account_id='A',current_balance='500',external_verification_confirmed=True,allocations=[dict(account_id='A',claim_id='C1',transaction_ref='DEMO_T1',amount='600',verified=True)])
    def test_sample_mixed_funds(self):
        t=trace_case(self.case)['trace']
        self.assertEqual([x['simulated_disputed_exposure'] for x in t['accounts']],['600.00','100.00','300.00'])
    def test_review_cap(self):
        r=decision_record(dict(case=self.case,review=self.review))
        self.assertEqual(r['draft']['proposed_amount_limited_hold'],'500.00')
        self.assertIn('Unsigned',r['status'])
    def test_verification_required(self):
        self.review['external_verification_confirmed']=False
        with self.assertRaises(ValueError):decision_record(dict(case=self.case,review=self.review))
    def test_duplicate_claim_rejected(self):
        self.review['allocations']*=2
        with self.assertRaises(ValueError):decision_record(dict(case=self.case,review=self.review))
    def test_untraced_account_rejected(self):
        self.review['account_id']='VICTIM'
        with self.assertRaises(ValueError):decision_record(dict(case=self.case,review=self.review))
    def test_defer_has_no_hold(self):
        self.review['decision']='defer'
        self.assertNotIn('draft',decision_record(dict(case=self.case,review=self.review)))
    def test_recompute_rejects_bad_ledger(self):
        self.case['opening_balances']['VICTIM']=0
        with self.assertRaises(ValueError):decision_record(dict(case=self.case,review=self.review))
    def test_hash_stable(self):
        self.assertEqual(trace_case(self.case)['input_sha256'],trace_case(copy.deepcopy(self.case))['input_sha256'])
