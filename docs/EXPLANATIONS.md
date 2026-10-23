# Attribution and graph investigation

`python -m scripts.build_explanation_background` reproduces 100 rows sampled only
from surrogate training episodes. The artifact records row positions, feature
schema, sampling seed, training partition and model hash.
`POST /api/explain` takes the same `{observation, valid_actions}` as the surrogate.
Interventional TreeSHAP explains the selected surrogate class in raw-margin space.
The returned base score plus ten contributions must reproduce the actual XGBoost
raw score within 1e-4; failure returns unavailable. Q and surrogate actions, their
agreement, abstention and model/background hashes remain visible. If actions
disagree, the explanation still describes the surrogate, not the Q action.

`python -m scripts.evaluate_explanations` times 100 actual uncached explanations
with a 100-row background. The first includes lazy imports/model initialization;
warm calls still compute prediction and TreeSHAP, without response caching. Cold
latency and warm p50/p95/max are separate; a warm sub-100ms result does not erase
cold startup cost. Attribution signs are contributions to a model score, not
physical causes. Counterfactual equipment switching is not supported.

`POST /api/diagnose` accepts `{dataset: reference|synthetic, alarms: [{asset_id,
observed_at}]}` (1–100 alarms). It ranks investigation hypotheses using BFS paths,
alarm timing consistency under an explicitly heuristic nonnegative equal-hop-delay
model, and PageRank damping 0.85 for ten iterations. The last-iteration residual
is reported, including nonconvergence. Constant structural edge weight 1 lies in
[0,1] but is not calibrated risk. Paths retain source evidence. Reference mode
excludes planned assets and 2019-only circuit records; the remaining dated
reference still does not establish current switching or power flows.

All relationships in this diagnostic projection are undirected CONNECTED_TO.
SUPPLIES_TO/SERVES flow direction is not fabricated for reference circuits whose
current direction is unknown. The original immutable Neo4j evidence graph remains
separate. Local previews compute from the validated export. The composed deployment reads
the actual immutable Neo4j snapshot, independently verifies all records and endpoint
relations, then runs the documented NetworkX algorithms. The immutable snapshot cache is version-bound and initialized before production
readiness. A failed initial database verification returns unavailable; an already
verified cached reference is not a claim of current database or grid state.
Readiness independently probes current database connectivity. Neo4j GDS/PageRank execution is not claimed.

The evaluation uses procedural graph-distance alarm fixtures. The hidden source
is excluded from engine input; this checks behavior under declared toy assumptions.
It does not supply real fault/cascade ground truth or prove a causal success rate.
Operator agreement/trust, physical frequency control and full fault-to-cause workflow
latency require independent evidence. The committed report preserves these limits.
