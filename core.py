"""Evaluation and exact empirical interventional Shapley attribution."""
import math
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve, confusion_matrix
FEATURES=['fan_ratio_structural','fan_ratio_volume','amount_mean','amount_std','spike_ratio','round_amount_fraction','passthrough_distance_7d','passthrough_has_signal','hub_score','authority_score']

def chain_groups(accounts,transactions):
    edges=transactions.loc[transactions.is_fraud_chain.eq(True)]
    parent={}
    def find(a):
        parent.setdefault(a,a)
        if parent[a]!=a: parent[a]=find(parent[a])
        return parent[a]
    for a,b in zip(edges.sender_account,edges.receiver_account):parent[find(a)]=find(b)
    if set(parent)!=set(accounts.loc[accounts.is_fraud_chain,'account_id']):
        raise ValueError('Transaction-derived chain labels disagree with account labels')
    roots={r:i for i,r in enumerate(sorted({find(a) for a in parent}))}
    return np.array(['chain_'+str(roots[find(a)]) if a in parent else 'normal_'+a for a in accounts.account_id])

def prepare(df,features=FEATURES):
    x=df[features].copy()
    if 'passthrough_distance_7d' in x:
        x.loc[~df.passthrough_has_signal.astype(bool),'passthrough_distance_7d']=np.nan
    return x.astype(float)

def estimator(kind,seed=42):
    steps=[SimpleImputer(strategy='median',keep_empty_features=True)]
    if kind=='LR':steps += [StandardScaler(),LogisticRegression(class_weight='balanced',max_iter=3000,random_state=seed)]
    else:steps += [RandomForestClassifier(n_estimators=120,max_depth=8,class_weight='balanced',random_state=seed,n_jobs=-1)]
    return make_pipeline(*steps)

def threshold_for_precision(y,scores,target=.8,min_flags=5):
    precision,recall,thresholds=precision_recall_curve(y,scores)
    counts=np.array([(scores>=t).sum() for t in thresholds])
    valid=np.flatnonzero((precision[:-1]>=target)&(counts>=min_flags))
    if not len(valid): return float('inf')
    # Maximum validation recall, highest threshold when tied.
    best=valid[np.lexsort((-thresholds[valid],-recall[valid]))[0]]
    return float(thresholds[best])

def counts(y,pred):
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return dict(tp=int(tp),fp=int(fp),fn=int(fn),tn=int(tn),flagged=int(tp+fp),precision=float(tp/(tp+fp)) if tp+fp else None,recall=float(tp/(tp+fn)) if tp+fn else None)

def exact_shap(model,row,background):
    """Enumerate all coalitions: exact Shapley values for a finite background.
    Interventional masking breaks dependencies; attribution is not causal evidence.
    Input is already imputed. Prediction units are raw class-1 model scores.
    """
    row=np.asarray(row);bg=np.asarray(background);d=len(row);n=len(bg)
    masks=((np.arange(2**d)[:,None]>>np.arange(d))&1).astype(bool)
    samples=np.where(masks[:,None,:],row[None,None,:],bg[None,:,:])
    values=model.predict_proba(samples.reshape(-1,d))[:,1].reshape(2**d,n).mean(1)
    phi=np.zeros(d)
    for j in range(d):
        for mask in range(2**d):
            if mask&(1<<j):continue
            k=mask.bit_count();w=1/(d*math.comb(d-1,k))
            phi[j]+=w*(values[mask|(1<<j)]-values[mask])
    if not np.isclose(values[0]+phi.sum(),values[-1],atol=1e-8):raise AssertionError('Shapley additivity failed')
    return float(values[0]),phi,float(values[-1])

def grouped_shap(model,row,background,groups):
    """Exact interventional Shapley over a complete partition of feature indices."""
    row=np.asarray(row);bg=np.asarray(background);d=len(groups)
    flat=[i for g in groups for i in g]
    if sorted(flat)!=list(range(len(row))):raise ValueError('Groups must partition features exactly once')
    values=[]
    for mask in range(2**d):
        samples=bg.copy()
        for j,g in enumerate(groups):
            if mask&(1<<j):samples[:,g]=row[g]
        values.append(model.predict_proba(samples)[:,1].mean())
    phi=np.zeros(d)
    for j in range(d):
        for mask in range(2**d):
            if mask&(1<<j):continue
            k=mask.bit_count();phi[j]+=(values[mask|(1<<j)]-values[mask])/(d*math.comb(d-1,k))
    if not np.isclose(values[0]+phi.sum(),values[-1],atol=1e-8):raise AssertionError('Grouped Shapley additivity failed')
    return float(values[0]),phi,float(values[-1])
