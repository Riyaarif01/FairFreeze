"""Local complaint review UI. No persistence, authentication, or bank connection."""
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime, timezone
from tracing import trace, money
from review import review_hold

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 2_000_000

def trace_case(case):
    result = trace(case['transactions'], case['opening_balances'], case['complaint'], case.get('cutoff'))
    digest = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'input_sha256': digest, 'trace': result}

def decision_record(payload):
    # Recompute the ledger on every review; never trust browser-supplied trace results.
    bundle = trace_case(payload['case'])
    review = payload['review']
    if review.get('decision') not in ('defer', 'draft_hold'):
        raise ValueError('Choose defer or draft_hold')
    for field in ('reviewer', 'rationale', 'authority_reference'):
        if not isinstance(review.get(field), str) or not review[field].strip():
            raise ValueError(f'{field} required')
    if review['decision'] == 'draft_hold':
        if review.get('external_verification_confirmed') is not True:
            raise ValueError('External verification acknowledgement required')
        accounts = {a['account_id'] for a in bundle['trace']['accounts']}
        if review['account_id'] not in accounts:
            raise ValueError('Select an account in the trace')
        allocations = review['allocations']
        if not allocations or not any(money(a['amount']) > 0 for a in allocations):
            raise ValueError('Positive externally verified allocation required')
        bundle['draft'] = review_hold(review['account_id'], review['current_balance'], allocations,
                                     review['authority_reference'], review['reviewer'])
    bundle['review'] = review
    bundle['recorded_at_utc'] = datetime.now(timezone.utc).isoformat()
    bundle['status'] = 'Unsigned reviewer assertion; no bank action'
    bundle['verification_boundary'] = 'Names, references, balances and verification claims are user assertions. This app does not authenticate a reviewer or validate external evidence.'
    return bundle

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, mime='application/json'):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/':
            self.reply(200, (ROOT / 'case_app.html').read_text(), 'text/html; charset=utf-8')
        elif self.path == '/sample':
            self.reply(200, json.loads((ROOT / 'examples/sample_case.json').read_text()))
        else:
            self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        # JSON-only, loopback-only deployment, same-origin requests. No CORS.
        host = self.headers.get('Host', '')
        if host not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            self.reply(403, {'error': 'Invalid host'}); return
        origin = self.headers.get('Origin')
        if origin and origin != f'http://{host}':
            self.reply(403, {'error': 'Cross-origin request rejected'}); return
        try:
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('application/json required')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BYTES:
                raise ValueError('Case must be between 1 byte and 2 MB')
            data = json.loads(self.rfile.read(length))
            if self.path == '/trace': result = trace_case(data)
            elif self.path == '/review': result = decision_record(data)
            else: self.reply(404, {'error': 'Not found'}); return
            self.reply(200, result)
        except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError) as exc:
            self.reply(400, {'error': str(exc)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    print(f'Open http://127.0.0.1:{args.port} — local research review only', flush=True)
    HTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
