"""Versioned scenarios and paired policy evaluation for Phase 2."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Callable

import pandas as pd

from prism.dispatch.baseline import recommend
from prism.dispatch.q_learning import QLearningAgent
from prism.simulation import Action, GridEnvironment, Observation, SimulationConfig, quarter_hour_profile


Policy = Callable[[Observation, tuple[Action, ...]], Action]


def load_scenario_suite(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema_version") != "1.0" or not isinstance(payload.get("scenarios"), list):
        raise ValueError("Unsupported scenario-suite schema")
    required = {"normal_day", "renewable_ramp", "plant_fault", "line_fault", "concurrent_fault"}
    identifiers = {item.get("id") for item in payload["scenarios"]}
    if identifiers != required:
        raise ValueError("Scenario suite must contain the five declared Phase 2 scenarios")
    return payload


def scenario_profile(frame: pd.DataFrame, specification: dict) -> list[dict[str, float]]:
    start = int(specification["start_hour"])
    hours = (int(specification["steps"]) + 3) // 4
    selected = frame.iloc[start : start + hours]
    if len(selected) != hours:
        raise ValueError(f"Scenario {specification['id']} exceeds the measurement fixture")
    profile = quarter_hour_profile(selected, hours=hours)[: int(specification["steps"])]
    beginning = float(specification.get("renewable_scale_start", 1.0))
    ending = float(specification.get("renewable_scale_end", beginning))
    for index, point in enumerate(profile):
        fraction = index / max(1, len(profile) - 1)
        scale = beginning + fraction * (ending - beginning)
        point["solar_mw"] *= scale
        point["wind_mw"] *= scale
    return profile


def make_environment(topology: dict, frame: pd.DataFrame, specification: dict, seed: int) -> GridEnvironment:
    return GridEnvironment(
        topology,
        profile=scenario_profile(frame, specification),
        faults=specification.get("faults", []),
        config=SimulationConfig(episode_steps=int(specification["steps"])),
        seed=seed,
    )


def baseline_action(observation: Observation, valid_actions: tuple[Action, ...]) -> Action:
    candidate = Action(recommend(observation)["action"])
    return candidate if candidate in valid_actions else Action.HOLD


def q_action(agent: QLearningAgent) -> Policy:
    return lambda observation, valid_actions: agent.action(observation, valid_actions)


def run_policy(environment: GridEnvironment, policy: Policy, seed: int, include_trajectory: bool = False) -> dict:
    observation = Observation(**environment.reset(seed=seed))
    totals = {"return": 0.0, "unserved_mwh": 0.0, "curtailed_mwh": 0.0, "operating_cost": 0.0, "emissions_kg": 0.0, "constraint_violations": 0.0}
    trajectory: list[dict] = []
    while True:
        action = policy(observation, environment.valid_actions())
        next_raw, reward, terminated, info = environment.step(action)
        totals["return"] += reward
        for key in totals.keys() - {"return"}:
            totals[key] += info["metrics"][key]
        if include_trajectory:
            trajectory.append({"observation": asdict(observation), "reward": reward, **info})
        observation = Observation(**next_raw)
        if terminated:
            break
    result = {"steps": environment.horizon, "totals": {key: round(value, 6) for key, value in totals.items()}, "final_observation": asdict(observation)}
    if include_trajectory:
        result["trajectory"] = trajectory
    return result
