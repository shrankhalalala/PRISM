"""Train a reproducible Phase 2 Q-table on the committed synthetic scenario."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from prism.config import DATA_DIR, ROOT
from prism.dispatch.q_learning import QLearningAgent, TrainingConfig
from prism.grid.model import load_grid
from prism.simulation import FaultEvent, GridEnvironment, quarter_hour_profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/q_learning/phase2_q_table.json",
    )
    arguments = parser.parse_args()

    topology = load_grid(DATA_DIR / "raw/grid.json")
    measurements = pd.read_csv(DATA_DIR / "processed/measurements.csv")
    profile = quarter_hour_profile(measurements, hours=24)
    faults = [FaultEvent(step=48, asset_id="gas", duration_steps=8)]

    def environment_factory() -> GridEnvironment:
        return GridEnvironment(topology, profile=profile, faults=faults, seed=arguments.seed)

    config = TrainingConfig(episodes=arguments.episodes, seed=arguments.seed)
    agent = QLearningAgent(config)
    history = agent.train(environment_factory)
    agent.save(
        arguments.output,
        metadata={
            "data_source": "synthetic_seed_42",
            "profile_hours": 24,
            "fault": {"step": 48, "asset_id": "gas", "duration_steps": 8},
            "final_episode_return": history[-1]["return"],
        },
    )
    print(f"Saved {config.episodes}-episode Q-table to {arguments.output}")
    print(f"Final episode return: {history[-1]['return']}")


if __name__ == "__main__":
    main()
