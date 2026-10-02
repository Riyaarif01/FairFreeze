import unittest
from review import review_hold
class Tests(unittest.TestCase):
    def test_partial_hold(self):
        r=review_hold('A',1000,[dict(account_id='A',claim_id='C',transaction_ref='T',amount=200,verified=True)],'AUTH','Reviewer')
        self.assertEqual(r['proposed_amount_limited_hold'],'200.00');self.assertEqual(r['remaining_available'],'800.00')
    def test_duplicate(self):
        x=dict(account_id='A',claim_id='C',transaction_ref='T',amount=200,verified=True)
        with self.assertRaises(ValueError):review_hold('A',1000,[x,x],'AUTH','Reviewer')
    def test_unverified(self):
        with self.assertRaises(ValueError):review_hold('A',1000,[dict(account_id='A',claim_id='C',transaction_ref='T',amount=200,verified=False)],'AUTH','Reviewer')
