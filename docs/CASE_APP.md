# Complaint review dashboard

Run `python case_app.py` from the project folder; open http://127.0.0.1:8765. No additional UI dependency is required. Stop with Ctrl+C.

1. Load the synthetic example or upload a JSON case (maximum 2 MB).
2. Inspect account exposures, balances and time-ordered transfer allocations.
3. Choose defer, or separately enter externally verified allocations and current balance for an amount-limited draft.
4. Supply reviewer reference, authority reference and reasons. Export JSON.

`examples/sample_case.json` defines the input structure. Use timezone-aware timestamps, one currency, unique transaction IDs, complete opening balances, and every movement needed to reconcile the ledger. Equal-time transfers follow input order. This can change a simulated allocation and must be resolved in a real case.

The example begins with INR 1,000 disputed funds and INR 1,000 legitimate funds in account A. Final simulated exposures are A 600, B 100 and C 300. These are accounting assumptions, not automatic verified allocations. The reviewer can defer. Drafting requires non-overlapping claim references, externally checked amounts and an independently checked current balance.

Cases are held in browser/server memory during requests, not persisted. Export intentionally contains case references and evidence; handle it accordingly. The canonical SHA-256 input hash supports reproducibility, not authenticity. Decision records are unsigned assertions: reviewer names and verification checkboxes are not authenticated. No model score influences the hold draft. No bank connection exists.

The server binds only to loopback, rejects cross-origin JSON writes and invalid hosts, limits request size, and does not enable CORS. User-controlled strings render via textContent. This is not a production web service.

Validation: 32 Python tests cover existing models and tracing plus sample mixed funds, stable hashes, review caps, missing verification, duplicate claims, non-traced accounts, defer and ledger recalculation. HTTP trace/review and cross-origin rejection smoke tests pass. Browser script syntax checked; full visual/browser interaction has not been verified.
