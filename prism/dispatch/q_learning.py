"""Tabular Q-learning for the constrained PRISM simulation environment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
from typing import Callable

import numpy as np

from prism.dispatch.baseline import encode_state
from prism.simulation.environment import Action, GridEnvironment, Observation


ACTION_ORDER = tuple(Action)
STATE_SHAPE = (5, 3, 3, 3, 2)
STATE_COUNT = int(np.prod(STATE_SHAPE))


@dataclass(frozen=True)
class TrainingConfig:
    """Hyperparameters saved with every trained Q-table."""

    episodes: int = 500
    alpha: float = 0.1
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    seed: int = 42

    def __post_init__(self) -> None:
        if isinstance(self.episodes, bool) or self.episodes <= 0:
            raise ValueError("episodes must be positive")
        if not 0 < self.alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if not 0 <= self.gamma <= 1:
            raise ValueError("gamma must be between 0 and 1")
        if not 0 <= self.epsilon_end <= self.epsilon_start <= 1:
            raise ValueError("epsilon must satisfy 0 <= end <= start <= 1")


def state_index(observation: Observation) -> int:
    """Flatten the documented five-dimensional encoding into [0, 269]."""

    return int(np.ravel_multi_index(encode_state(observation), STATE_SHAPE))


class QLearningAgent:
    """Seeded tabular learner that never selects a masked action."""

    def __init__(
        self,
        config: TrainingConfig | None = None,
        q_values: np.ndarray | None = None,
    ) -> None:
        self.config = config or TrainingConfig()
        self._rng = random.Random(self.config.seed)
        expected = (STATE_COUNT, len(ACTION_ORDER))
        if q_values is None:
            self.q_values = np.zeros(expected, dtype=float)
        else:
            values = np.asarray(q_values, dtype=float)
            if values.shape != expected or not np.isfinite(values).all():
                raise ValueError(f"q_values must be a finite array with shape {expected}")
            self.q_values = values.copy()

    def action(self, observation: Observation, valid_actions: tuple[Action, ...]) -> Action:
        """Choose the best valid action with deterministic action-order tie breaking."""

        if not valid_actions:
            raise ValueError("At least one valid action is required")
        row = self.q_values[state_index(observation)]
        valid_indices = [ACTION_ORDER.index(action) for action in valid_actions]
        best_index = max(valid_indices, key=lambda index: (row[index], -index))
        return ACTION_ORDER[best_index]

    def train(
        self,
        environment_factory: Callable[[], GridEnvironment],
    ) -> list[dict[str, float]]:
        """Train for the configured episodes and return per-episode evidence."""

        history: list[dict[str, float]] = []
        self._rng = random.Random(self.config.seed)
        for episode in range(self.config.episodes):
            environment = environment_factory()
            raw_state = environment.reset(seed=self.config.seed + episode)
            observation = Observation(**raw_state)
            epsilon = self._epsilon(episode)
            total_reward = 0.0
            steps = 0
            while True:
                valid = environment.valid_actions()
                action = self._explore_or_exploit(observation, valid, epsilon)
                next_raw, reward, terminated, _ = environment.step(action)
                next_observation = Observation(**next_raw)
                self._update(
                    observation,
                    action,
                    reward,
                    next_observation,
                    () if terminated else environment.valid_actions(),
                    terminated,
                )
                total_reward += reward
                steps += 1
                observation = next_observation
                if terminated:
                    break
            history.append(
                {
                    "episode": episode + 1,
                    "epsilon": round(epsilon, 8),
                    "return": round(total_reward, 8),
                    "steps": steps,
                }
            )
        return history

    def _epsilon(self, episode: int) -> float:
        if self.config.episodes == 1:
            return self.config.epsilon_end
        fraction = episode / (self.config.episodes - 1)
        return self.config.epsilon_start + fraction * (
            self.config.epsilon_end - self.config.epsilon_start
        )

    def _explore_or_exploit(
        self,
        observation: Observation,
        valid_actions: tuple[Action, ...],
        epsilon: float,
    ) -> Action:
        if not valid_actions:
            raise RuntimeError("Environment exposed no valid action")
        if self._rng.random() < epsilon:
            return self._rng.choice(valid_actions)
        return self.action(observation, valid_actions)

    def _update(
        self,
        observation: Observation,
        action: Action,
        reward: float,
        next_observation: Observation,
        next_valid_actions: tuple[Action, ...],
        terminated: bool,
    ) -> None:
        row = state_index(observation)
        column = ACTION_ORDER.index(action)
        target = reward
        if not terminated:
            next_row = self.q_values[state_index(next_observation)]
            valid_indices = [ACTION_ORDER.index(item) for item in next_valid_actions]
            target += self.config.gamma * max(next_row[index] for index in valid_indices)
        current = self.q_values[row, column]
        self.q_values[row, column] = current + self.config.alpha * (target - current)

    def save(self, path: str | Path, metadata: dict | None = None) -> None:
        """Write a portable, human-inspectable policy artifact."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "algorithm": "tabular_q_learning",
            "state_shape": list(STATE_SHAPE),
            "actions": [action.value for action in ACTION_ORDER],
            "training_config": asdict(self.config),
            "metadata": metadata or {},
            "q_values": self.q_values.tolist(),
        }
        target.write_text(json.dumps(payload, indent=2) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "QLearningAgent":
        """Load and validate a policy created by :meth:`save`."""

        payload = json.loads(Path(path).read_text())
        if payload.get("schema_version") != "1.0":
            raise ValueError("Unsupported Q-table schema version")
        if payload.get("actions") != [action.value for action in ACTION_ORDER]:
            raise ValueError("Q-table action order does not match this implementation")
        if payload.get("state_shape") != list(STATE_SHAPE):
            raise ValueError("Q-table state shape does not match this implementation")
        return cls(TrainingConfig(**payload["training_config"]), np.asarray(payload["q_values"]))
