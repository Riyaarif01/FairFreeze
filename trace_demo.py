import json
from pathlib import Path
from tracing import trace
from review import review_hold
p=Path(__file__).resolve().parent
transactions=[dict(transaction_id='DEMO_T1',timestamp='2026-01-01T10:00:00+00:00',sender='VICTIM',receiver='A',amount=1000,currency='INR'),dict(transaction_id='DEMO_T2',timestamp='2026-01-01T11:00:00+00:00',sender='A',receiver='B',amount=800,currency='INR'),dict(transaction_id='DEMO_T3',timestamp='2026-01-01T12:00:00+00:00',sender='B',receiver='C',amount=600,currency='INR')]
complaint=dict(complaint_id='SIM_COMPLAINT',authority_reference='SIM_AUTHORITY',seed_transaction_id='DEMO_T1',disputed_amount=1000,currency='INR')
r=trace(transactions,{'VICTIM':1000,'A':1000,'B':0,'C':0},complaint)
r['review_example']=review_hold('A',1200,[dict(account_id='A',claim_id='SIM_COMPLAINT',transaction_ref='DEMO_T1',amount=600,verified=True)],'SIM_AUTHORITY','SIM_REVIEWER')
r['review_example']['provenance']='Synthetic demonstration of externally confirmed allocation; not inferred approval from trace output.'
(p/'reports/tracing_demo.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r,indent=2))
