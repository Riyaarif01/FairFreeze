import pandas as pd
import numpy as np
import random

random.seed(42)
np.random.seed(42)

INPUT_PATH = r"D:\payguard\data\synthetic\fraudchain_dataset_v2.csv"
OUTPUT_PATH = r"D:\payguard\data\synthetic\fraudchain_dataset_v3.csv"

N_NEW_CHAINS = 15
MIN_HOPS = 2
MAX_HOPS = 5

print("Loading existing dataset...")
df = pd.read_csv(INPUT_PATH, low_memory=False)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
print(f"Loaded {len(df)} rows.")

existing_fraud_accounts = set(
    df[df["is_fraud_chain"] == True]["sender_account"].tolist() +
    df[df["is_fraud_chain"] == True]["receiver_account"].tolist()
)
all_accounts = list(set(df["sender_account"]) | set(df["receiver_account"]))
available_accounts = [a for a in all_accounts if a not in existing_fraud_accounts]

date_min = df["timestamp"].min()
date_max = df["timestamp"].max()

new_rows = []
used_accounts_this_run = set()

for chain_id in range(N_NEW_CHAINS):
    n_hops = random.randint(MIN_HOPS, MAX_HOPS)
    candidates = [a for a in available_accounts if a not in used_accounts_this_run]
    if len(candidates) < n_hops + 1:
        print(f"Not enough available accounts left for chain {chain_id}, stopping.")
        break
    chain_accounts = random.sample(candidates, n_hops + 1)
    used_accounts_this_run.update(chain_accounts)

    start_amount = random.uniform(20000, 80000)
    start_time = date_min + (date_max - date_min) * random.random()

    current_time = start_time
    current_amount = start_amount

    for hop in range(n_hops):
        sender = chain_accounts[hop]
        receiver = chain_accounts[hop + 1]
        cut = random.uniform(0.05, 0.15)
        amount = current_amount * (1 - cut)
        gap_hours = random.uniform(3, 48)
        current_time = current_time + pd.Timedelta(hours=gap_hours)

        new_rows.append({
            "sender_account": sender,
            "receiver_account": receiver,
            "amount": round(amount, 2),
            "timestamp": current_time,
            "bank_name": "Yes Bank Ltd.",
            "merchant_category": "Not Applicable (P2P)",
            "transaction_type": "P2P",
            "hour": current_time.hour,
            "is_late_night": 1 if current_time.hour < 6 or current_time.hour >= 23 else 0,
            "is_new_device": 0,
            "is_new_merchant": 0,
            "outcome": "SUCCESS",
            "is_fraud": 1,
            "is_fraud_chain": True,
            "hop_number": hop + 1,
        })
        current_amount = amount

print(f"Generated {len(new_rows)} new fraud-chain transaction rows across up to {N_NEW_CHAINS} chains.")

new_df = pd.DataFrame(new_rows)
new_df["timestamp"] = pd.to_datetime(new_df["timestamp"])

for col in df.columns:
    if col not in new_df.columns:
        new_df[col] = np.nan

new_df = new_df[df.columns]

combined = pd.concat([df, new_df], ignore_index=True)
combined["timestamp"] = pd.to_datetime(combined["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

combined.to_csv(OUTPUT_PATH, index=False)

print(f"Saved: {OUTPUT_PATH}")
print(f"Total rows: {len(combined)}")
print(f"Total fraud-chain rows: {combined['is_fraud_chain'].sum()}")
n_fraud_accounts = len(set(combined[combined['is_fraud_chain']==True]['sender_account']) |
                        set(combined[combined['is_fraud_chain']==True]['receiver_account']))
print(f"Total unique fraud-involved accounts: {n_fraud_accounts}")

verify = pd.read_csv(OUTPUT_PATH, low_memory=False)
verify["ts_check"] = pd.to_datetime(verify["timestamp"], errors="coerce")
print(f"Verification: {verify['ts_check'].isna().sum()} unparseable timestamps after fix (should be 0)")
