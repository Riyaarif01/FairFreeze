"""Independent IBM synthetic AML benchmark, Rupee-only chronological windows."""
import argparse,json,hashlib,urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from build_features import build
from core import prepare,estimator,threshold_for_precision,counts
ROOT=Path(__file__).resolve().parent
URL='https://www.kaggle.com/api/v1/datasets/download/ealtman2019/ibm-transactions-for-anti-money-laundering-aml/HI-Small_Trans.csv'
SOURCE='https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml'

def adapt(d):
    return pd.DataFrame(dict(sender_account='IBM_'+d['From Bank'].astype(str)+'_'+d['Account'].astype(str),receiver_account='IBM_'+d['To Bank'].astype(str)+'_'+d['Account.1'].astype(str),amount=d['Amount Paid'],timestamp=pd.to_datetime(d.Timestamp,format='%Y/%m/%d %H:%M'),is_fraud_chain=d['Is Laundering'].eq(1)))
def run(raw):
    selected=[];total=0
    for d in pd.read_csv(raw,chunksize=250000,dtype={'From Bank':str,'To Bank':str,'Account':str,'Account.1':str}):
        total+=len(d);z=d[(d['Payment Currency']=='Rupee')&(d['Receiving Currency']=='Rupee')&(d['Amount Paid']==d['Amount Received'])];selected.append(z)
    d=pd.concat(selected);t=adapt(d);parts={};stats={}
    for name,start,end in [('train','2022-09-01','2022-09-04'),('validation','2022-09-04','2022-09-07'),('test','2022-09-07','2022-09-10')]:
        subset=t[(t.timestamp>=start)&(t.timestamp<end)];a=build(subset);parts[name]=a;stats[name]=dict(start=start,end_exclusive=end,transactions=len(subset),laundering_transactions=int(subset.is_fraud_chain.sum()),accounts=len(a),positive_accounts=int(a.is_fraud_chain.sum()))
        print('BUILT',name,stats[name],flush=True)
    old=pd.read_csv(ROOT/'data/accounts.csv');results={}
    for kind in ['RF','LR']:
        # Cross-generator transfer: original snapshot-trained model, frozen threshold.
        oof=pd.read_csv(ROOT/'reports/account_scores.csv');th=threshold_for_precision(oof.is_fraud_chain.astype(int).to_numpy(),oof[kind+'_score'].to_numpy(),.8)
        legacy=estimator(kind);legacy.fit(prepare(old),old.is_fraud_chain.astype(int));test=parts['test'];y=test.is_fraud_chain.astype(int).to_numpy();s=legacy.predict_proba(prepare(test))[:,1]
        transfer=dict(average_precision=float(average_precision_score(y,s)),threshold=None if not np.isfinite(th) else th,**counts(y,s>=th))
        # Native chronological backtest: labels in training window only; validation threshold.
        model=estimator(kind);model.fit(prepare(parts['train']),parts['train'].is_fraud_chain.astype(int));val=model.predict_proba(prepare(parts['validation']))[:,1]
        threshold=threshold_for_precision(parts['validation'].is_fraud_chain.astype(int).to_numpy(),val,.8)
        score=model.predict_proba(prepare(test))[:,1];order=np.argsort(-score,kind='stable')
        results[kind]=dict(cross_generator_transfer=transfer,ibm_chronological=dict(average_precision=float(average_precision_score(y,score)),threshold=None if not np.isfinite(threshold) else threshold,threshold_status='selected' if np.isfinite(threshold) else 'target_unattainable',**counts(y,score>=threshold),precision_at_100=float(y[order[:100]].mean())))
    report=dict(source=SOURCE,download_url=URL,dataset='HI-Small_Trans.csv',dataset_sha256=hashlib.file_digest(open(raw,'rb'),'sha256').hexdigest(),raw_transactions=total,rupee_equal_amount_transactions=len(t),rupee_laundering_transactions=int(t.is_fraud_chain.sum()),windows=stats,models=results,label_definition='An account is positive when sender or receiver of any IBM-labeled laundering transfer within that window. This is involvement, not adjudicated fraud or culpability.',evaluation='Three non-overlapping three-day transaction windows; score at end of window. Account identities may repeat, and label-derived IDs are excluded. Features and graph rebuilt from each window only. Native models fit train only, threshold selected validation only, test untouched.',limitations=['Synthetic AML labels are not adjudicated Indian fraud labels.','Rupee is a synthetic currency field; this does not establish an Indian population.','Single temporal split and few positives; no deployment validation.','Window-end retrospective screening, not transaction-time prospective prediction.','Currency filter excludes FX and other-currency context.','Unobserved laundering is not inferred; negatives mean no labeled laundering in this selected window.','No complaint seeds or opening balances are supplied by this benchmark; it cannot validate hold amounts.'],data_license='CDLA-Sharing-1.0; raw IBM data not bundled in project repository.')
    (ROOT/'reports/ibm_benchmark.json').write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--csv',type=Path);p.add_argument('--download',action='store_true');a=p.parse_args()
    raw=a.csv or ROOT/'external_data/HI-Small_Trans.csv'
    if a.download:
        raw.parent.mkdir(exist_ok=True);urllib.request.urlretrieve(URL,raw)
    if not raw.exists():p.error('Supply --csv PATH or --download (approximately 476 MB)')
    run(raw)
