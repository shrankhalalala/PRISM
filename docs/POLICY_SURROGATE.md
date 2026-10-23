# Frozen Q-policy and six-action surrogate

`python -m scripts.train_surrogate` labels states using the unchanged reviewed
Phase 2 Q-table, and trains XGBoost `multi:softprob` with all six action slots.
Entire chronological synthetic day episodes are split 63/13/14 (70/15/15 rounded
to complete days). Seeds 5000–5089 are separate from Q-training seeds. Valid random
rollouts provide state coverage; each label is the frozen Q-policy's masked action.
The maximum depth and boosting length are selected using validation log loss;
test data does not select the model. Data, episodes, policy and model identities
are saved. Temporal correlation and synthetic dynamics limit generalization.

The explicit ten-feature schema comprises six observation fields plus imbalance,
generation/demand ratio, reserve/demand ratio and the caller-supplied valid-action
bitmask. This resolves the report's inconsistent nine/ten-feature lists without
inventing coal/gas available MW. Runtime masks must come from separately checked
constraints; an arbitrary user mask is not electrical feasibility evidence.

All six output classes remain fixed even if a split lacks a class. The committed
run has test support for every action; confusion matrices and support counts are
reported. The uncalibrated softprob score uses the report's 0.75 threshold for
abstention. Report accepted coverage as well as accepted agreement; never call
this score operator trust or a calibrated probability. Masking excludes invalid
actions without inflating scores by renormalization.

`POST /api/dispatch/surrogate` accepts `{observation, valid_actions}` and reports
the Q action, surrogate action, agreement, six scores, mask, abstention and hashes.
The recommendation remains the Q-policy action. Both policies are advisory and
are not eligible for the reference Delhi electrical network. Paired held-out
episodes compare baseline, Q-policy and surrogate on their own trajectories using
identical initial seeds/profiles/faults. Their returns, unserved energy, cost,
emissions and constraint violations are separate from state-pool fidelity.

The committed state-pool test agreement is 97.62%; scores >=0.75 cover 96.28% of
states with 99.46% agreement within that subset. These are surrogate fidelity
measurements, not proof the Q-policy is good or better than the baseline. The
original Phase 2 negative comparisons remain intact. Real measurements do not
supply counterfactual dispatch dynamics, so live-policy retraining stays gated.
