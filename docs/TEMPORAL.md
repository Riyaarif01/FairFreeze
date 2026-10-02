# Temporal feature experiment, version 3

Timing and amount features are computed without reading labels. For each outgoing transfer, find the nearest strictly earlier incoming transfer to that account, within 72 hours. Report outgoing fractions preceded by inflows within 1, 24 and 72 hours, matching fractions, minimum amount distance from a ratio of one and median forwarding delay. Matching accepts outgoing/incoming ratios from 0.2 to 1.05. This is a heuristic and is not fund allocation. Incoming funds from unrelated transactions can match by coincidence; a nearest incoming transfer is not necessarily the true funding source.

Bounded path search counts 2–5-hop paths with strictly increasing timestamps, total duration at most 72 hours and successive amount ratios between 0.2 and 1.05. It also detects time-respecting cycles. Bounds are 100 popped search states per originating account and 12 outgoing candidates per branch, including 12 initial edges. Counts are incomplete when capped; `path_search_truncated` exposes that limitation. Each path remains an investigation pattern, not culpability evidence. Dense legitimate activity can create many paths.

## Frozen evaluation

HI-Small Sep 1–3 trains models. HI Sep 4–6 selects among baseline RF, augmented RF, flow-only RF and augmented LR using validation average precision. An 80% precision threshold requires at least five validation flags, otherwise the model abstains. Feature definitions and model parameters are fixed before the first LI outcome inspection. A policy file and hash are written before the LI data is processed.

LI-Small Sep 7–9 is a fresh source/window holdout for this experiment. It is a different file from the same IBM simulator, not an independently adjudicated population. Later reproduction runs retain the same policy and do not tune using LI outcomes. Current LI data is now inspected; future model development needs another untouched holdout.

Features and graphs are rebuilt separately per window and use no transfers beyond the window end. Account IDs and labels are excluded from inputs. This is retrospective window-end screening; it does not test online transaction-time detection. Single-currency filtering discards other-currency context and limits ownership/allocation conclusions.

## Results

Validation AP: baseline RF 0.138; augmented RF 0.090; flow-only RF 0.021; augmented LR 0.008. The baseline wins validation, so temporal augmentation is not adopted as the selected detector. All validation precision targets are unattainable under the specified policy.

LI test: 108,453 selected transfers; 24,418 accounts; 63 involvement-positive accounts. The selected baseline RF has AP 0.0040 and catches 1/63 positives in its top 100. The policy abstains from threshold flags. Search truncates for 2,321 test accounts. This is a negative experiment, not an improvement claim. No operational acceptance is established.

Two held-out examples include exact empirical interventional Shapley attribution by feature groups, with 24 training-background accounts. Group attributions are not individual feature Shapley values; additivity is checked. Feature dependencies and independent masking remain explanation limitations.

## Reproduce

```bash
python fetch_ibm.py --variant both
python temporal_benchmark.py --hi external_data/HI-Small_Trans.csv --li external_data/LI-Small_Trans.csv
python dashboard.py
python -m unittest discover -s tests -v
```

Downloading both sources uses roughly 1.13 GB. They are excluded from the repository and archive. Publisher license and provenance are recorded in `docs/IBM_DATA.md`.
