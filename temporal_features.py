"""Label-free temporal signals with explicit bounded-search truncation."""
from collections import defaultdict
from bisect import bisect_right
import numpy as np
import pandas as pd
TEMPORAL=['quick_out_1h_fraction','quick_out_24h_fraction','quick_out_72h_fraction','matched_out_fraction','matched_amount_distance','median_forward_delay_hours','temporal_path_count','temporal_max_hops','temporal_cycle_signal','path_search_truncated']

def build_temporal(transactions,max_hops=5,max_states=100,max_branch=12):
    """Uses transfers available inside a supplied observation window only.
    Matching means nearest strictly earlier incoming transfer within 72 hours;
    it is a behavioral heuristic, not allocation of funds or legal evidence.
    Paths require strictly increasing timestamps, <=72h from first transfer,
    and next/previous amount in [.2,1.05]. No labels read.
    """
    if not 2<=max_hops<=5 or max_states<1 or max_branch<1:raise ValueError('Invalid search bounds')
    t=transactions[['sender_account','receiver_account','amount','timestamp']].copy()
    t['timestamp']=pd.to_datetime(t.timestamp,format='mixed',errors='raise')
    if t.amount.isna().any() or not np.isfinite(t.amount).all() or (t.amount<=0).any():raise ValueError('Amounts must be finite and positive')
    ids=sorted(set(t.sender_account)|set(t.receiver_account));r=pd.DataFrame(0.,index=ids,columns=TEMPORAL);r.index.name='account_id'
    r['matched_amount_distance']=np.nan;r['median_forward_delay_hours']=np.nan
    incoming={};outgoing=defaultdict(list)
    nonself=t[t.sender_account!=t.receiver_account].sort_values('timestamp',kind='stable')
    for account,g in nonself.groupby('receiver_account',sort=False):incoming[account]=(g.timestamp.astype('int64').to_numpy(),g.amount.to_numpy())
    for account,g in nonself.groupby('sender_account',sort=False):
        times=g.timestamp.astype('int64').to_numpy();amounts=g.amount.to_numpy()
        outgoing[account]=list(zip(times,g.receiver_account,amounts))
        if account not in incoming:continue
        it,ia=incoming[account];pos=np.searchsorted(it,times,side='left')-1;valid=pos>=0;safe=np.maximum(pos,0)
        delays=(times-it[safe])/3.6e12;ratios=amounts/ia[safe]
        for hours,name in [(1,'quick_out_1h_fraction'),(24,'quick_out_24h_fraction'),(72,'quick_out_72h_fraction')]:r.loc[account,name]=np.mean(valid&(delays<=hours))
        match=valid&(delays<=72)&(ratios>=.2)&(ratios<=1.05)
        r.loc[account,'matched_out_fraction']=match.mean()
        if match.any():r.loc[account,'matched_amount_distance']=np.min(abs(1-ratios[match]));r.loc[account,'median_forward_delay_hours']=np.median(delays[match])
    edge_times={a:[e[0] for e in es] for a,es in outgoing.items()}
    horizon=int(72*3.6e12)
    for root,edges in outgoing.items():
        truncated=len(edges)>max_branch;stack=[];count=0;maxdepth=0;cycle=False;states=0
        for tm,dst,amt in reversed(edges[:max_branch]):stack.append((dst,tm,tm,amt,1,(root,dst)))
        while stack and states<max_states:
            current,last,start,amt,depth,path=stack.pop();states+=1
            if depth>=2:count+=1;maxdepth=max(maxdepth,depth)
            if depth>=max_hops:continue
            es=outgoing.get(current,[]);ts=edge_times.get(current,[]);lo=bisect_right(ts,last);hi=bisect_right(ts,start+horizon)
            candidates=[e for e in es[lo:hi] if .2<=e[2]/amt<=1.05]
            if len(candidates)>max_branch:truncated=True
            for tm,dst,nextamt in reversed(candidates[:max_branch]):
                if dst in path:
                    cycle=True;count+=1;maxdepth=max(maxdepth,depth+1)
                else:stack.append((dst,tm,start,nextamt,depth+1,path+(dst,)))
        truncated=truncated or bool(stack)
        r.loc[root,['temporal_path_count','temporal_max_hops','temporal_cycle_signal','path_search_truncated']]=[count,maxdepth,int(cycle),int(truncated)]
    return r.reset_index()
