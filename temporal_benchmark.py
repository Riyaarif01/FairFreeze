"""Lock feature/model selection on HI windows before reading LI holdout labels."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from core import FEATURES,estimator,prepare,threshold_for_precision,counts,grouped_shap
from build_features import build
from temporal_features import build_temporal,TEMPORAL
from ibm_benchmark import adapt
ROOT=Path(__file__).resolve().parent

def window(raw,start,end):
    parts=[]
    for d in pd.read_csv(raw,chunksize=250000,dtype={'From Bank':str,'To Bank':str,'Account':str,'Account.1':str}):
        z=d[(d['Payment Currency']=='Rupee')&(d['Receiving Currency']=='Rupee')&(d['Amount Paid']==d['Amount Received'])].copy()
        z['Timestamp']=pd.to_datetime(z.Timestamp,format='%Y/%m/%d %H:%M');z=z[(z.Timestamp>=start)&(z.Timestamp<end)]
        if len(z):parts.append(z)
    t=adapt(pd.concat(parts));base=build(t);temporal=build_temporal(t);merged=base.merge(temporal,on='account_id',validate='one_to_one')
    return merged,dict(transactions=len(t),positive_transfers=int(t.is_fraud_chain.sum()),accounts=len(base),positive_accounts=int(base.is_fraud_chain.sum()),truncated_path_accounts=int(temporal.path_search_truncated.sum()))

def run(hi,li):
    train,trainstats=window(hi,'2022-09-01','2022-09-04');val,valstats=window(hi,'2022-09-04','2022-09-07')
    config={'RF_baseline':('RF',FEATURES),'RF_temporal':('RF',FEATURES+TEMPORAL),'RF_flow_only':('RF',[f for f in FEATURES if f not in ['amount_mean','amount_std','spike_ratio','hub_score','authority_score']]+TEMPORAL),'LR_temporal':('LR',FEATURES+TEMPORAL)}
    models={};validation={};yv=val.is_fraud_chain.astype(int).to_numpy()
    for name,(kind,fs) in config.items():
        model=estimator(kind);model.fit(prepare(train,fs),train.is_fraud_chain.astype(int));s=model.predict_proba(prepare(val,fs))[:,1];th=threshold_for_precision(yv,s,.8)
        validation[name]=dict(average_precision=float(average_precision_score(yv,s)),threshold=None if not np.isfinite(th) else th,threshold_status='selected' if np.isfinite(th) else 'target_unattainable',**counts(yv,s>=th))
        models[name]=(model,fs,th);print('VALIDATION',name,validation[name],flush=True)
    selected=max(validation,key=lambda n:validation[n]['average_precision'])
    policy=dict(selected_model=selected,selection_rule='Highest HI validation average precision; no LI data consulted',target_precision=.8,min_validation_flags=5,features=config[selected][1],training_window='HI Sep 1–3 2022',validation_window='HI Sep 4–6 2022',holdout_window='LI Sep 7–9 2022',validation=validation,search_bounds=dict(max_hops=5,max_states=100,max_branch=12,horizon_hours=72,amount_ratio_min=.2,amount_ratio_max=1.05))
    text=json.dumps(policy,indent=2,allow_nan=False);(ROOT/'reports/temporal_policy.json').write_text(text);lock_hash=hashlib.sha256(text.encode()).hexdigest();print('LOCKED policy',lock_hash,flush=True)
    test,teststats=window(li,'2022-09-07','2022-09-10');yt=test.is_fraud_chain.astype(int).to_numpy();result={}
    # Predeclared baseline and validation-selected candidate only; no selection on test.
    for name in dict.fromkeys(['RF_baseline',selected]):
        model,fs,th=models[name];s=model.predict_proba(prepare(test,fs))[:,1];order=np.lexsort((test.account_id.to_numpy(),-s))
        result[name]=dict(average_precision=float(average_precision_score(yt,s)),threshold=None if not np.isfinite(th) else th,**counts(yt,s>=th),top_k={str(k):dict(caught=int(yt[order[:k]].sum()),precision=float(yt[order[:k]].mean())) for k in [20,50,100]})
    model,fs,th=models[selected];xt=prepare(test,fs);training=prepare(train,fs)
    imputer=model.steps[0][1];predictor=model[1:];bg=imputer.transform(training.sample(n=min(24,len(training)),random_state=42))
    named_groups={'structure':[f for f in fs if f in ['fan_ratio_structural','fan_ratio_volume','passthrough_distance_7d','passthrough_has_signal']], 'amount_behavior':[f for f in fs if f in ['amount_mean','amount_std','spike_ratio','round_amount_fraction']], 'graph':[f for f in fs if f in ['hub_score','authority_score']], 'temporal_flow':[f for f in fs if f in TEMPORAL]}
    named_groups={n:g for n,g in named_groups.items() if g};index_groups=[[fs.index(f) for f in g] for g in named_groups.values()];score=model.predict_proba(xt)[:,1];examples=[]
    for label,mask in [('highest_ranked_positive',yt==1),('highest_ranked_negative',yt==0)]:
        ix=np.flatnonzero(mask)
        if not len(ix):continue
        idx=int(ix[np.argmax(score[ix])]);row=imputer.transform(xt.iloc[[idx]])[0];base,phi,value=grouped_shap(predictor,row,bg,index_groups)
        examples.append(dict(account_id=test.iloc[idx].account_id,example_type=label,model=selected,baseline=base,score=value,review_flag=bool(value>=th),proposed_hold_amount=None,groups=[dict(group=n,features=g,contribution=float(v)) for (n,g),v in zip(named_groups.items(),phi)],observed_features={f:None if pd.isna(xt.iloc[idx][f]) else float(xt.iloc[idx][f]) for f in fs},method='Exact empirical interventional Shapley for feature GROUPS, not individual features; 24 HI-training background accounts. Explanations describe scores, not criminal intent.'))
    (ROOT/'reports/temporal_explanations.json').write_text(json.dumps(examples,indent=2,allow_nan=False))
    report=dict(selected_model=selected,policy_sha256=lock_hash,data_sha256={p.name:hashlib.file_digest(open(p,'rb'),'sha256').hexdigest() for p in [hi,li]},train=trainstats,validation=valstats,holdout=teststats,test_results=result,acceptance='No threshold-based flags permitted when validation target is unattainable.',limitations=['Both datasets come from the same IBM simulator; separate LI source is fresh to this work, not independently adjudicated banking ground truth.','HI validation outcomes have been explored previously; LI outcomes are inspected only after policy selection; reruns reproduce the fixed policy rather than tune it.','Rupee single-currency subset discards other-currency context.','Window-end retrospective features, not transaction-time prediction.','Nearest-incoming matching is heuristic; paths and cycles do not establish disputed fund ownership.','Search is capped and truncation reported; path counts are not exhaustive.','One source/window holdout with rare positives; no real-world deployment claim.'])
    (ROOT/'reports/temporal_benchmark.json').write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hi',type=Path,required=True);p.add_argument('--li',type=Path,required=True);a=p.parse_args();run(a.hi,a.li)
