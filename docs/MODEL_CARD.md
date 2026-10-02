# Model card

FairFreeze ranks synthetic account-level chain involvement for human investigation. Labels indicate planted-chain participation, not criminal intent. All publication identifiers are synthetic. Real-world provenance of the supplied original development chain is unverified. Aggregate RBI/NPCI statistics are not labeled customer-level fraud evidence.

## Evaluation

Five outer grouped folds keep each of 16 labeled connected components together. Normal accounts receive individual groups. Three inner grouped folds select thresholds maximizing recall at an exploratory 80% precision target with at least five inner-validation flags. Unattainable targets produce no flags. Outer evaluation never chooses the threshold. This target is not a legal standard. There is no final deployment threshold or calibrated probability claim.

Account ID, hop number and fraud labels are excluded from inputs. Median imputation and LR scaling are learned inside folds. The 999 no-signal pass-through sentinel becomes missing before imputation; the indicator remains. Class balancing does not calibrate scores.

Average precision is distinct from trapezoidal PR-AUC. Pooled top-k compares different fold models' uncalibrated scores and is exploratory. Fold ranges illustrate instability; 16 chains limit statistical confidence. Feature selection has already observed the original chain. Full graph features use all unlabeled accounts in the snapshot, including test accounts: a transductive setting, not prospective detection. Background edges can still couple separate labeled chains.

## Generator shortcuts

Extra chains use 2–5 hops, starting amounts ₹20,000–80,000, 5–15% cuts, and gaps of 3–48 hours. Background amounts are much smaller. Banks and other metadata are hardcoded but excluded as features. The original generator iterates a set, so its seeds alone do not guarantee identical account selection. Snapshot hashes preserve the evaluated inputs. Feature-only amount sensitivity probes hold graph/flow features fixed and do not establish robustness on realistic regenerated transactions.

## Explanations

Exact empirical interventional Shapley attribution enumerates 1,024 coalitions for ten features over 24 sampled training accounts; no SHAP package dependency is needed. Explanations use outer-fold models that did not train on the example's chain. Additivity is verified in class-1 model score units. Imputed prediction inputs are used; missing raw values stay marked missing. Independent masking can create implausible combinations of correlated features. Background selection affects attribution. Contributions explain a prediction, not causality or culpability.

## Action boundary

Flags request human review. The snapshot has no verified complaint seed, opening/current balance, complaint-specific allocation or legal authority. Explanations therefore leave proposed hold amount unavailable. `review.py` can construct an amount-limited draft only from externally verified non-overlapping allocations, current balance and authority/reviewer references. It does not execute a bank instruction and does not multiply a score by a balance.

## Remaining work

Independent generators with legitimate large/round transfers and lower-value fraud; chronological evaluation with as-of graph/features; complaint-seeded time-respecting paths; validated mixed-funds accounting; bounded short cycles; independently adjudicated real-case labels; jurisdiction-specific legal review. No real-case accuracy, deployment readiness or court acceptance is claimed.
