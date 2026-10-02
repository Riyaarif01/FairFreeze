"""Complaint-seeded chronological proportional allocation for simulations.
Not a legal determination of fund ownership. Complete opening balances required.
"""
from decimal import Decimal,ROUND_HALF_UP

def money(value):
    d=Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    if not d.is_finite() or d<0:raise ValueError('Money must be finite and non-negative')
    return d

def trace(transactions,opening_balances,complaint,cutoff=None):
    required={'transaction_id','timestamp','sender','receiver','amount','currency'}
    if any(not required.issubset(t) for t in transactions):raise ValueError('Incomplete transaction fields')
    if not complaint.get('complaint_id') or not complaint.get('authority_reference'):raise ValueError('Complaint and authority references required')
    currency=complaint['currency'];seed_id=complaint['seed_transaction_id'];seed_amount=money(complaint['disputed_amount'])
    if not seed_amount:raise ValueError('Disputed amount must be positive')
    if len({t['transaction_id'] for t in transactions})!=len(transactions):raise ValueError('Duplicate transaction IDs')
    # ISO UTC timestamp strings only; input order breaks equal-timestamp ties.
    from datetime import datetime
    def dt(s):
        v=datetime.fromisoformat(s.replace('Z','+00:00'))
        if v.tzinfo is None:raise ValueError('Timezone-aware timestamps required')
        return v
    bound=dt(cutoff) if cutoff else None
    ordered=sorted(enumerate(transactions),key=lambda x:(dt(x[1]['timestamp']),x[0]))
    balances={a:money(v) for a,v in opening_balances.items()};taint={a:Decimal('0') for a in balances};events=[];seed_found=False
    for seq,t in ordered:
        if bound and dt(t['timestamp'])>bound:continue
        if t['currency']!=currency:raise ValueError('Cross-currency allocation requires verified FX treatment')
        u,v=t['sender'],t['receiver'];amount=money(t['amount'])
        if u not in balances or v not in balances:raise ValueError('Opening balance missing for account')
        if amount>balances[u]:raise ValueError('Insufficient balance; incomplete ledger or invalid transaction')
        if u==v:
            if t['transaction_id']==seed_id:raise ValueError('Self-transfer cannot be complaint seed')
            continue
        moved=(taint[u]*amount/balances[u]).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if balances[u] else Decimal('0')
        moved=min(moved,taint[u],amount)
        if t['transaction_id']==seed_id:
            if seed_found or moved:raise ValueError('Ambiguous seed')
            if seed_amount>amount:raise ValueError('Dispute exceeds seed transfer')
            moved=seed_amount;seed_found=True
        elif moved:taint[u]-=moved
        balances[u]-=amount;balances[v]+=amount;taint[v]+=moved
        if moved:events.append(dict(transaction_id=t['transaction_id'],timestamp=t['timestamp'],sender=u,receiver=v,transfer_amount=str(amount),allocated_disputed_amount=str(moved),currency=currency,source='complaint_seed' if t['transaction_id']==seed_id else 'proportional_mixing_assumption'))
        if any(taint[a]>balances[a] or taint[a]<0 for a in balances):raise AssertionError('Allocation bounds failed')
        if sum(taint.values())!=(seed_amount if seed_found else Decimal('0')):raise AssertionError('Disputed funds not conserved')
    if not seed_found:raise ValueError('Seed absent before cutoff')
    exposure=[dict(account_id=a,balance=str(balances[a]),simulated_disputed_exposure=str(taint[a]),currency=currency,proposed_hold_amount=None) for a in sorted(balances) if taint[a]>0]
    return dict(complaint=complaint,cutoff=cutoff,method='Chronological proportional mixing rounded to currency cents',limitations=['Allocation is a simulation assumption, not proof of legal ownership.','Complete opening balances and all ledger movements required.','Equal-time transfers use supplied input order; unresolved real ordering requires review.','No automatic hold, criminal intent inference or bank instruction.'],events=events,accounts=exposure,total_allocated=str(sum(taint.values())),seed_disputed_amount=str(seed_amount))
