"""Independent seeded synthetic stress snapshot; not real-world validation."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from build_features import build
from core import estimator,prepare,threshold_for_precision,counts
ROOT=Path(__file__).resolve().parent

def run():
    rng=np.random.default_rng(2026);source=pd.read_csv(ROOT/'data/transactions.csv',low_memory=False)
    amounts=source.loc[~source.is_fraud_chain,'amount'].to_numpy();ids=np.array([f'STRESS_{i:05d}' for i in range(20000)])
    n=100000;start=pd.Timestamp('2026-01-01');send=rng.integers(0,len(ids),n);recv=rng.integers(0,len(ids),n)
    recv=np.where(recv==send,(recv+1)%len(ids),recv)
    t=pd.DataFrame(dict(sender_account=ids[send],receiver_account=ids[recv],amount=rng.choice(amounts,n),timestamp=start+pd.to_timedelta(rng.uniform(0,60*24,n),unit='h'),is_fraud_chain=False,scenario='background'))
    available=rng.permutation(ids);cursor=0;extra=[]
    for scenario,low,high,fraud in [('low_value_fraud',100,2000,True),('high_value_fraud',20000,80000,True),('legitimate_large_chain',20000,80000,False),('legitimate_round_chain',20000,80000,False)]:
        for chain in range(15):
            hops=int(rng.integers(2,6));accounts=available[cursor:cursor+hops+1];cursor+=hops+1
            amount=rng.uniform(low,high);time=start+pd.Timedelta(hours=float(rng.uniform(0,45*24)))
            for hop in range(hops):
                amount*=1-rng.uniform(.05,.15);time+=pd.Timedelta(hours=float(rng.uniform(3,48)))
                value=round(amount/1000)*1000 if scenario=='legitimate_round_chain' else round(amount,2)
                extra.append(dict(sender_account=accounts[hop],receiver_account=accounts[hop+1],amount=value,timestamp=time,is_fraud_chain=fraud,scenario=scenario))
    t=pd.concat([t,pd.DataFrame(extra)],ignore_index=True);a=build(t);y=a.is_fraud_chain.astype(int).to_numpy()
    scenario_accounts={name:set(g.sender_account)|set(g.receiver_account) for name,g in t[t.scenario!='background'].groupby('scenario')}
    original=pd.read_csv(ROOT/'data/accounts.csv');oof=pd.read_csv(ROOT/'reports/account_scores.csv');results={}
    for kind in ['RF','LR']:
        threshold=threshold_for_precision(oof.is_fraud_chain.astype(int).to_numpy(),oof[kind+'_score'].to_numpy(),.8)
        model=estimator(kind);model.fit(prepare(original),original.is_fraud_chain.astype(int));s=model.predict_proba(prepare(a))[:,1];flags=s>=threshold
        groups={}
        for name,accounts in scenario_accounts.items():
            mask=a.account_id.isin(accounts).to_numpy();groups[name]=dict(accounts=int(mask.sum()),flagged=int(flags[mask].sum()),mean_score=float(s[mask].mean()))
        results[kind]=dict(average_precision=float(average_precision_score(y,s)),threshold=None if not np.isfinite(threshold) else threshold,**counts(y,flags),scenarios=groups)
    metadata=dict(seed=2026,accounts=len(a),positive_accounts=int(y.sum()),transactions=len(t),results=results,scope='Independent synthetic IDs, topology and sampled transactions; background amounts bootstrapped from original non-chain marginal distribution. All features recomputed. Original models trained on full development snapshot; thresholds from development OOF predictions. Stress labels not used in fitting.',limitation='Legitimate chains deliberately share observable fraud patterns. Labels alone cannot make identical behavior identifiable. This is generator stress testing, not real-world accuracy.')
    (ROOT/'reports/generator_stress.json').write_text(json.dumps(metadata,indent=2,allow_nan=False));print(json.dumps(metadata,indent=2))
if __name__=='__main__':run()
