"""Draft amount-limited holds from human-verified allocations; no bank action."""
from decimal import Decimal,ROUND_HALF_UP
def review_hold(account_id,balance,allocations,authority_reference,reviewer):
    if not authority_reference or not reviewer:raise ValueError('Authority and reviewer required')
    money=lambda v:Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    bal=money(balance)
    if not bal.is_finite() or bal<0:raise ValueError('Invalid balance')
    claims=set();total=Decimal('0')
    for x in allocations:
        if x['account_id']!=account_id or x.get('verified') is not True:raise ValueError('Unverified or mismatched allocation')
        if not x.get('claim_id') or not x.get('transaction_ref'):raise ValueError('Evidence required')
        if x['claim_id'] in claims:raise ValueError('Duplicate claim')
        claims.add(x['claim_id']);value=money(x['amount'])
        if not value.is_finite() or value<0:raise ValueError('Invalid allocation')
        total+=value
    hold=min(total,bal)
    return dict(account_id=account_id,reviewer=reviewer,authority_reference=authority_reference,verified_disputed_amount=str(total),proposed_amount_limited_hold=str(hold),remaining_available=str(bal-hold),evidence=allocations,status='Draft for authorized human review; no bank action',assumption='Reviewer verified non-overlapping allocations and current balance; model score is not used.')
