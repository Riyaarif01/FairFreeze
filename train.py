"""Run nested chain-grouped validation; no automatic freeze decisions."""
import argparse,json,hashlib,platform
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import average_precision_score
from core import FEATURES,chain_groups,prepare,estimator,threshold_for_precision,counts,exact_shap
ROOT=Path(__file__).resolve().parent

def run(target=.8):
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    a=pd.read_csv(ROOT/'data/accounts.csv');t=pd.read_csv(ROOT/'data/transactions.csv',low_memory=False)
    if a.account_id.duplicated().any():raise ValueError('Duplicate accounts')
    groups=chain_groups(a,t);y=a.is_fraud_chain.astype(int).to_numpy()
    outer=list(StratifiedGroupKFold(5,shuffle=True,random_state=42).split(a,y,groups))
    variants={'RF':('RF',FEATURES),'RF_no_round':('RF',[f for f in FEATURES if f!='round_amount_fraction']), 'RF_no_amount_or_HITS':('RF',[f for f in FEATURES if f not in ['amount_mean','amount_std','spike_ratio','hub_score','authority_score']]),'LR':('LR',FEATURES)}
    rows=[];predictions={};fold_models={}
    for name,(kind,features) in variants.items():
        x=prepare(a,features);scores=np.zeros(len(a));flags=np.zeros(len(a),dtype=bool)
        for fold,(tr,te) in enumerate(outer):
            inner=StratifiedGroupKFold(3,shuffle=True,random_state=100+fold)
            val=np.zeros(len(tr))
            for it,iv in inner.split(x.iloc[tr],y[tr],groups[tr]):
                model=estimator(kind);model.fit(x.iloc[tr[it]],y[tr[it]])
                val[iv]=model.predict_proba(x.iloc[tr[iv]])[:,1]
            threshold=threshold_for_precision(y[tr],val,target)
            model=estimator(kind);model.fit(x.iloc[tr],y[tr]);s=model.predict_proba(x.iloc[te])[:,1]
            scores[te]=s;flags[te]=s>=threshold
            rows.append(dict(model=name,fold=fold+1,test_positives=int(y[te].sum()),average_precision=float(average_precision_score(y[te],s)),threshold=threshold if np.isfinite(threshold) else None,threshold_status='selected' if np.isfinite(threshold) else 'target_unattainable',**counts(y[te],s>=threshold)))
            if name=='RF':fold_models[fold]=(model,tr,te,threshold)
            print(name,'fold',fold+1,'AP',round(rows[-1]['average_precision'],4),'flags',rows[-1]['flagged'],flush=True)
        predictions[name]=(scores,flags)
    summary={}
    for name,(scores,flags) in predictions.items():
        r=[v for v in rows if v['model']==name];order=np.lexsort((a.account_id.to_numpy(),-scores))
        summary[name]=dict(mean_fold_AP=float(np.mean([v['average_precision'] for v in r])),min_fold_AP=min(v['average_precision'] for v in r),max_fold_AP=max(v['average_precision'] for v in r),pooled_AP=float(average_precision_score(y,scores)),top_k={str(k):dict(caught=int(y[order[:k]].sum()),precision=float(y[order[:k]].mean())) for k in [20,50,100]},**counts(y,flags))
    scored=a[['account_id','is_fraud_chain']].copy();scored['chain_group']=groups
    for name,(scores,flags) in predictions.items():scored[name+'_score']=scores;scored[name+'_review_flag']=flags
    scored.to_csv(out/'account_scores.csv',index=False);pd.DataFrame(rows).to_csv(out/'fold_metrics.csv',index=False)
    # Choose diagnostic examples using RF OUT-OF-FOLD scores, not a full-data fit.
    s,flags=predictions['RF'];chosen=[]
    for label,mask in [('true_positive',(y==1)&flags),('false_positive',(y==0)&flags),('missed_positive',(y==1)&~flags),('highest_ranked_positive',y==1),('highest_ranked_negative',y==0)]:
        ix=np.flatnonzero(mask)
        if len(ix):chosen.append((label,int(ix[np.argmax(s[ix])])) )
    explanations=[];x=prepare(a)
    for label,idx in chosen:
        fold=next(k for k,v in fold_models.items() if idx in v[2]);model,tr,te,threshold=fold_models[fold]
        imputer=model.steps[0][1];rf=model.steps[-1][1]
        bg_indices=np.random.default_rng(42).choice(tr,size=min(24,len(tr)),replace=False)
        bg=imputer.transform(x.iloc[bg_indices]);row=imputer.transform(x.iloc[[idx]])[0]
        base,phi,score=exact_shap(rf,row,bg)
        account=a.iloc[idx].account_id
        transfers=t.loc[(t.sender_account==account)|(t.receiver_account==account),['sender_account','receiver_account','amount','timestamp']].copy()
        transfers['transaction_ref']=['SYNTH_ROW_'+str(i) for i in transfers.index]
        contributions=[dict(feature=f,value=None if pd.isna(x.iloc[idx][f]) else float(x.iloc[idx][f]),contribution=float(v)) for f,v in zip(FEATURES,phi)]
        contributions.sort(key=lambda r:abs(r['contribution']),reverse=True)
        explanations.append(dict(account_id=account,example_type=label,outer_fold=fold+1,score=score,baseline=base,review_flag=bool(flags[idx]),threshold=None if not np.isfinite(threshold) else threshold,background_size=len(bg),contributions=contributions,transactions=transfers.to_dict('records'),decision='Human review only',proposed_hold_amount=None,reason='No complaint-linked seed, account balance, or verified fund allocation supplied.'))
    (out/'explanations.json').write_text(json.dumps(explanations,indent=2,allow_nan=False))
    # Controlled sensitivity tests: aggregate feature perturbations, not new realistic data.
    model,tr,te,threshold=fold_models[0];base=x.iloc[te].copy();checks=[]
    for label,mask,factor in [('smaller_positive_amounts',y[te]==1,.1),('larger_negative_amounts',y[te]==0,10.)]:
        changed=base.copy();changed.loc[mask,['amount_mean','amount_std']]*=factor
        before=model.predict_proba(base)[:,1];after=model.predict_proba(changed)[:,1]
        checks.append(dict(scenario=label,accounts=int(mask.sum()),mean_score_before=float(before[mask].mean()),mean_score_after=float(after[mask].mean()),average_precision_after=float(average_precision_score(y[te],after)),limitation='Account-level sensitivity only; graph and flow features fixed; not a regenerated transaction dataset.'))
    metadata=dict(seed=42,target_precision=target,min_inner_flags=5,accounts=len(a),positives=int(y.sum()),chain_components=len(set(groups[y==1])),python=platform.python_version(),sklearn=sklearn.__version__,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'data/accounts.csv',ROOT/'data/transactions.csv']},metrics=summary,sensitivity=checks,threshold_policy='Inner grouped OOF threshold maximizes recall at target precision; outer fold remains untouched. No fixed deployment threshold established.')
    (out/'results.json').write_text(json.dumps(metadata,indent=2,allow_nan=False))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve
    fig,ax=plt.subplots(figsize=(7,5))
    for name,(scores,_) in predictions.items():p,r,_=precision_recall_curve(y,scores);ax.step(r,p,where='post',label=name)
    ax.axhline(y.mean(),color='gray',linestyle='--',label='Prevalence');ax.set(xlabel='Recall',ylabel='Precision',title='FairFreeze: pooled chain-grouped out-of-fold scores');ax.legend();fig.tight_layout();fig.savefig(out/'precision_recall.png',dpi=160);plt.close(fig)
    from dashboard import build
    build(out)
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--target-precision',type=float,default=.8);args=p.parse_args()
    if not 0<args.target_precision<=1:p.error('Precision must be in (0, 1]')
    run(args.target_precision)
