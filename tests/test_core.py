import unittest
import numpy as np
import pandas as pd
from core import chain_groups,threshold_for_precision,exact_shap,prepare
class Toy:
    def predict_proba(self,x):
        p=np.asarray(x)@np.array([.2,.3]);return np.column_stack([1-p,p])
class Tests(unittest.TestCase):
    def test_shap_known_linear(self):
        base,phi,score=exact_shap(Toy(),[1,1],[[0,0],[1,0]])
        np.testing.assert_allclose(phi,[.1,.3]);self.assertAlmostEqual(base+phi.sum(),score)
    def test_no_target(self):
        self.assertTrue(np.isinf(threshold_for_precision(np.array([0,1,0]),np.array([.9,.8,.7]),.9,1)))
    def test_threshold_counts_ties(self):
        y=np.array([1,0,1]);s=np.array([.9,.9,.8]);self.assertTrue(np.isinf(threshold_for_precision(y,s,.8,1)))
    def test_chain_overlap(self):
        a=pd.DataFrame({'account_id':['A','B','C','D'],'is_fraud_chain':[True,True,True,False]});t=pd.DataFrame({'sender_account':['A','C'],'receiver_account':['B','B'],'is_fraud_chain':[True,True]});g=chain_groups(a,t);self.assertEqual(g[0],g[2]);self.assertNotEqual(g[0],g[3])
    def test_sentinel(self):
        d=pd.DataFrame({'passthrough_distance_7d':[999,0.2],'passthrough_has_signal':[False,True]});x=prepare(d,list(d.columns));self.assertTrue(np.isnan(x.iloc[0,0]));self.assertEqual(x.iloc[1,0],.2)
if __name__=='__main__':unittest.main()
