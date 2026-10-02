import unittest
import pandas as pd
from temporal_features import build_temporal

def frame(edges):
    return pd.DataFrame([dict(sender_account=a,receiver_account=b,amount=v,timestamp='2026-01-01 '+time) for a,b,v,time in edges])
class Tests(unittest.TestCase):
    def test_ordered_cut_chain(self):
        r=build_temporal(frame([('A','B',100,'10:00'),('B','C',90,'11:00'),('C','D',80,'12:00')])).set_index('account_id')
        self.assertEqual(r.loc['A','temporal_max_hops'],3);self.assertEqual(r.loc['B','matched_out_fraction'],1)
    def test_reverse_time_not_chain(self):
        r=build_temporal(frame([('A','B',100,'12:00'),('B','C',90,'11:00')])).set_index('account_id');self.assertEqual(r.loc['A','temporal_max_hops'],0)
    def test_no_label_dependency(self):
        t=frame([('A','B',100,'10:00'),('B','C',90,'11:00')]);a=build_temporal(t);t['is_fraud_chain']=True;pd.testing.assert_frame_equal(a,build_temporal(t))
    def test_cycle(self):
        r=build_temporal(frame([('A','B',100,'10:00'),('B','A',90,'11:00')])).set_index('account_id');self.assertEqual(r.loc['A','temporal_cycle_signal'],1)
    def test_cap_flag(self):
        r=build_temporal(frame([('A','B',100,'10:00'),('B','C',90,'11:00')]),max_states=1).set_index('account_id');self.assertEqual(r.loc['A','path_search_truncated'],1)
    def test_equal_timestamps_not_sequence(self):
        r=build_temporal(frame([('A','B',100,'10:00'),('B','C',90,'10:00')])).set_index('account_id');self.assertEqual(r.loc['A','temporal_max_hops'],0)
