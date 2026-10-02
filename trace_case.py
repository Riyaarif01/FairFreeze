"""CLI: explicit complaint and opening balances, no inferred freeze authority."""
import argparse,json
from pathlib import Path
from tracing import trace
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('case',type=Path);p.add_argument('output',type=Path);p.add_argument('--cutoff');a=p.parse_args();case=json.loads(a.case.read_text());result=trace(case['transactions'],case['opening_balances'],case['complaint'],a.cutoff);a.output.write_text(json.dumps(result,indent=2));print('Wrote simulation exposure and transfer audit. No bank action executed.')
