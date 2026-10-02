import unittest
from tracing import trace
C=dict(complaint_id='C',authority_reference='AUTH',seed_transaction_id='T1',disputed_amount=100,currency='INR')
def tx(i,u,v,amount,time):return dict(transaction_id=i,sender=u,receiver=v,amount=amount,currency='INR',timestamp=f'2026-01-01T{time}:00+00:00')
class Tests(unittest.TestCase):
    def test_mixing_conservation(self):
        r=trace([tx('T1','V','A',100,'10:00'),tx('T2','A','B',100,'11:00')],{'V':100,'A':100,'B':0},C)
        self.assertEqual(r['total_allocated'],'100.00');self.assertEqual([a['simulated_disputed_exposure'] for a in r['accounts']],['50.00','50.00'])
        self.assertTrue(all(a['proposed_hold_amount'] is None for a in r['accounts']))
    def test_before_seed_not_tainted(self):
        r=trace([tx('T0','A','B',50,'09:00'),tx('T1','V','A',100,'10:00')],{'V':100,'A':50,'B':0},C)
        self.assertEqual(len(r['events']),1)
    def test_cutoff(self):
        r=trace([tx('T1','V','A',100,'10:00'),tx('T2','A','B',100,'11:00')],{'V':100,'A':0,'B':0},C,'2026-01-01T10:30:00+00:00');self.assertEqual(len(r['accounts']),1)
    def test_missing_balance(self):
        with self.assertRaises(ValueError):trace([tx('T1','V','A',100,'10:00')],{'V':100},C)
    def test_invalid_seed(self):
        with self.assertRaises(ValueError):trace([tx('T1','V','A',10,'10:00')],{'V':100,'A':0},C)
    def test_currency_rejected(self):
        t=tx('T1','V','A',100,'10:00');t['currency']='USD'
        with self.assertRaises(ValueError):trace([t],{'V':100,'A':0},C)
    def test_duplicate_id(self):
        t=tx('T1','V','A',100,'10:00')
        with self.assertRaises(ValueError):trace([t,t],{'V':200,'A':0},C)
    def test_randomized_ledger_conservation(self):
        import random
        rng=random.Random(42);initial={str(i):1000 for i in range(8)};balances=initial.copy()
        rows=[tx('T1','0','1',100,'00:00')];balances['0']-=100;balances['1']+=100
        for i in range(1,300):
            u,v=rng.sample(list(balances),2);amount=min(balances[u],rng.randrange(1,80));balances[u]-=amount;balances[v]+=amount
            from datetime import datetime,timedelta,timezone
            rows.append(dict(transaction_id=str(i),sender=u,receiver=v,amount=amount,currency='INR',timestamp=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=i)).isoformat()))
        r=trace(rows,initial,C);self.assertEqual(r['total_allocated'],'100.00')
