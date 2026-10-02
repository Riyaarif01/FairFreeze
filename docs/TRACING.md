# Complaint-seeded tracing

`python trace_demo.py` produces a three-hop simulated case. `python trace_case.py case.json result.json --cutoff 2026-01-01T12:00:00+00:00` processes a supplied case file.

Case JSON must contain `opening_balances` (account-to-amount mapping), `transactions` (unique transaction_id, timezone-aware timestamp, sender, receiver, amount, currency), and `complaint` (complaint_id, authority_reference, seed_transaction_id, disputed_amount, currency). Use the demo source for a concrete example.

Only one complaint seed is supported per case. Opening balances must refer to the beginning of the supplied complete transaction ledger. All movements and accounts must be included. Insufficient balances, unknown accounts, invalid amounts, duplicate references, cross-currency transactions and absent seeds are errors; opening funds are never invented to make a case pass.

After injecting the confirmed disputed slice at its seed transfer, each subsequent outgoing payment carries a proportional share of the sender's currently allocated exposure. Amounts round to cents, with residual exposure retained in the sender. Every transfer conserves total allocated disputed funds and bounds each account's exposure by its balance. Cycles remain chronological ledger movements; they do not create additional exposure. Equal-time transfer order follows input order, a simulation assumption that must be reviewed in real cases.

The trace is an accounting model, not proof of ownership. Mixed-fund legal treatment might differ by case; multiple complaints may overlap and cannot be independently summed. Exposure output leaves proposed hold amount null. Only externally verified non-overlapping allocations with a current balance, reviewer and authority reference can enter the separate review policy. The demo's review allocation is explicitly a synthetic manually confirmed example.

Verified invariants do not establish real-world evidentiary sufficiency or lawful power to freeze. No bank action API is present.
