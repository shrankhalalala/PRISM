"""Train multiple Q-learning seeds and compare them on held-out scenarios."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

import pandas as pd

from prism.config import DATA_DIR, ROOT
from prism.dispatch.evaluation import baseline_action, load_scenario_suite, make_environment, q_action, run_policy
from prism.dispatch.q_learning import QLearningAgent, TrainingConfig
from prism.grid.model import load_grid


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--seeds", default="11,23,42,67,89")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/phase2_dispatch.json")
    parser.add_argument("--policy", type=Path, default=ROOT / "models/q_learning/phase2_policy.json")
    arguments = parser.parse_args()
    seeds = [int(value) for value in arguments.seeds.split(",")]
    if len(set(seeds)) < 2:
        raise ValueError("At least two independent seeds are required")
    topology = load_grid(DATA_DIR / "raw/grid.json")
    frame = pd.read_csv(DATA_DIR / "processed/measurements.csv")
    suite_path = DATA_DIR / "scenarios/phase2_scenarios.json"
    suite = load_scenario_suite(suite_path)
    training = [item for item in suite["scenarios"] if item["partition"] == "train"]
    validation = [item for item in suite["scenarios"] if item["partition"] == "validation"]
    test = [item for item in suite["scenarios"] if item["partition"] == "test"]
    trained: list[tuple[int, QLearningAgent, float]] = []
    seed_results: list[dict] = []
    for seed in seeds:
        counter = {"episode": 0}
        def factory() -> object:
            specification = training[counter["episode"] % len(training)]
            counter["episode"] += 1
            return make_environment(topology, frame, specification, seed)
        agent = QLearningAgent(TrainingConfig(episodes=arguments.episodes, seed=seed))
        history = agent.train(factory)
        validation_results = [run_policy(make_environment(topology, frame, item, seed), q_action(agent), seed) for item in validation]
        score = statistics.mean(result["totals"]["return"] for result in validation_results)
        trained.append((seed, agent, score))
        scenarios = []
        for item in test:
            learned = run_policy(make_environment(topology, frame, item, seed), q_action(agent), seed)
            baseline = run_policy(make_environment(topology, frame, item, seed), baseline_action, seed)
            scenarios.append({"scenario": item["id"], "baseline": baseline["totals"], "q_learning": learned["totals"]})
        seed_results.append({"seed": seed, "validation_return": round(score, 6), "final_training_return": history[-1]["return"], "test_scenarios": scenarios})
    selected_seed, selected_agent, selected_score = max(trained, key=lambda item: item[2])
    selected_agent.save(arguments.policy, metadata={"status": "reviewed_phase2_recommendation", "selected_on": "validation_return", "selected_seed": selected_seed, "validation_return": selected_score, "scenario_suite": str(suite_path.relative_to(ROOT)), "episodes": arguments.episodes})
    metrics = ["return", "unserved_mwh", "curtailed_mwh", "operating_cost", "emissions_kg", "constraint_violations"]
    summary: dict[str, dict] = {}
    for metric in metrics:
        for policy in ("baseline", "q_learning"):
            values = [statistics.mean(scenario[policy][metric] for scenario in item["test_scenarios"]) for item in seed_results]
            summary[f"{policy}_{metric}"] = {"mean": round(statistics.mean(values), 6), "standard_deviation_across_training_seeds": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0}
    report = {
        "schema_version": "1.0", "data_source": "synthetic_seed_42", "scenario_suite": str(suite_path.relative_to(ROOT)), "scenario_suite_sha256": _sha256(suite_path),
        "training": {"episodes_per_seed": arguments.episodes, "seeds": seeds, "training_scenarios": [item["id"] for item in training], "validation_scenarios": [item["id"] for item in validation], "test_scenarios": [item["id"] for item in test]},
        "selection": {"seed": selected_seed, "validation_return": round(selected_score, 6), "policy_artifact": str(arguments.policy.relative_to(ROOT))},
        "policy_sha256": _sha256(arguments.policy), "per_seed": seed_results, "paired_test_summary": summary,
        "summary_unit": "Per-seed mean across the two held-out scenarios; dispersion is across five independent training seeds.",
        "interpretation": "Synthetic aggregate simulation evidence only; the selected policy emits non-executable recommendations.",
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Saved selected seed {selected_seed} policy to {arguments.policy}")


if __name__ == "__main__":
    main()
