"""Tests for Phase 2 tabular Q-learning and artifact persistence."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from prism.dispatch.q_learning import (
    ACTION_ORDER,
    QLearningAgent,
    STATE_COUNT,
    TrainingConfig,
    state_index,
)
from prism.grid.model import synthetic_grid
from prism.simulation import Action, GridEnvironment, Observation, SimulationConfig


class QLearningTests(unittest.TestCase):
    def environment_factory(self):
        profile = [
            {"demand_mw": 760, "solar_mw": 100, "wind_mw": 60},
            {"demand_mw": 740, "solar_mw": 110, "wind_mw": 70},
            {"demand_mw": 700, "solar_mw": 120, "wind_mw": 80},
        ]
        return GridEnvironment(
            synthetic_grid(),
            profile=profile,
            config=SimulationConfig(episode_steps=3),
        )

    def test_state_index_covers_documented_space(self):
        index = state_index(Observation(700, 700, 350))
        self.assertGreaterEqual(index, 0)
        self.assertLess(index, STATE_COUNT)

    def test_training_is_reproducible_and_updates_table(self):
        config = TrainingConfig(episodes=8, seed=7)
        first = QLearningAgent(config)
        second = QLearningAgent(config)
        history = first.train(self.environment_factory)
        second.train(self.environment_factory)
        self.assertEqual(len(history), 8)
        self.assertFalse(np.allclose(first.q_values, 0))
        np.testing.assert_allclose(first.q_values, second.q_values)

    def test_policy_masks_unavailable_actions(self):
        values = np.zeros((STATE_COUNT, len(ACTION_ORDER)))
        observation = Observation(700, 700, 350)
        values[state_index(observation), ACTION_ORDER.index(Action.SHED)] = 100
        agent = QLearningAgent(q_values=values)
        selected = agent.action(observation, (Action.HOLD, Action.INCREASE_GENERATION))
        self.assertEqual(selected, Action.HOLD)

    def test_round_trip_policy_artifact(self):
        agent = QLearningAgent(TrainingConfig(episodes=2, seed=11))
        agent.train(self.environment_factory)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            agent.save(path, metadata={"purpose": "test"})
            loaded = QLearningAgent.load(path)
        np.testing.assert_allclose(agent.q_values, loaded.q_values)
        self.assertEqual(loaded.config, agent.config)

    def test_hyperparameter_validation(self):
        with self.assertRaises(ValueError):
            TrainingConfig(episodes=0)
        with self.assertRaises(ValueError):
            TrainingConfig(epsilon_start=0.1, epsilon_end=0.2)


if __name__ == "__main__":
    unittest.main()
