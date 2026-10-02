"""Rebuild the documented snapshot features; fixed weekly buckets, weighted HITS."""
import argparse
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import svds
from core import FEATURES

def build(t):
    t=t.copy();t['timestamp']=pd.to_datetime(t.timestamp,format='mixed',errors='raise')
    ids=pd.Index(sorted(set(t.sender_account)|set(t.receiver_account)));a=pd.DataFrame(index=ids)
    oc=t.groupby('sender_account').size().reindex(ids,fill_value=0);ic=t.groupby('receiver_account').size().reindex(ids,fill_value=0)
    ou=t.groupby('sender_account').receiver_account.nunique().reindex(ids,fill_value=0);iu=t.groupby('receiver_account').sender_account.nunique().reindex(ids,fill_value=0)
    a['fan_ratio_structural']=ou/iu.replace(0,1);a['fan_ratio_volume']=oc/ic.replace(0,1)
    stats=t.groupby('sender_account').amount.agg(['mean','std','max'])
    a['amount_mean']=stats['mean'];a['amount_std']=stats['std'].fillna(0).reindex(ids,fill_value=0);a['spike_ratio']=(stats['max']/stats['mean'].replace(0,np.nan)).reindex(ids).fillna(0)
    a['round_amount_fraction']=t.assign(r=t.amount.mod(1000).eq(0)).groupby('sender_account').r.mean().reindex(ids,fill_value=0)
    t['window']=t.timestamp.dt.floor('168h')
    def flows(side,prefix):
        z=t.groupby([side,'window']).amount.agg(['sum','count']);z.index=z.index.set_names(['account','window']);return z.add_prefix(prefix)
    f=pd.concat([flows('sender_account','out_'),flows('receiver_account','in_')],axis=1).fillna(0)
    f=f[(f.out_sum>0)&(f.in_count>=2)&(f.out_count>=2)]
    dist=(f.in_sum/f.out_sum-1).abs().groupby('account').min().reindex(ids)
    a['passthrough_distance_7d']=dist.fillna(999);a['passthrough_has_signal']=dist.notna()
    mapping={v:i for i,v in enumerate(ids)}
    adj=coo_matrix((t.amount.to_numpy(),(t.sender_account.map(mapping),t.receiver_account.map(mapping))),shape=(len(ids),len(ids))).tocsr()
    # Dominant singular vectors implement weighted HITS. Sign is arbitrary.
    u,s,v=svds(adj,k=1,which='LM',v0=np.ones(len(ids)))
    h=np.abs(u[:,0]);auth=np.abs(v[0]);a['hub_score']=h/h.sum();a['authority_score']=auth/auth.sum()
    fraud=t.loc[t.is_fraud_chain.eq(True)];positive=set(fraud.sender_account)|set(fraud.receiver_account)
    a['is_fraud_chain']=[i in positive for i in ids];a.index.name='account_id'
    return a.reset_index()[['account_id']+FEATURES+['is_fraud_chain']]
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('transactions');p.add_argument('output');args=p.parse_args();build(pd.read_csv(args.transactions,low_memory=False)).to_csv(args.output,index=False)
