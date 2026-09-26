"""Deterministic Phase 2 grid simulation with explicit simplifying assumptions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from enum import Enum
import math
import random
from typing import Iterable, Mapping, Sequence

import networkx as nx

from prism.grid.model import grid_summary, validate_grid


class Action(str, Enum):
    HOLD = "hold"
    INCREASE_GENERATION = "increase_generation"
    DECREASE_GENERATION = "decrease_generation"
    CHARGE = "charge_battery"
    DISCHARGE = "discharge_battery"
    SHED = "shed_load"


@dataclass(frozen=True)
class Observation:
    """Aggregate inputs shared by the baseline and Q-learning policy."""

    demand_mw: float
    generation_mw: float
    reserve_mw: float
    battery_soc: float = 0.5
    renewable_trend: float = 0.0
    fault_present: bool = False


@dataclass(frozen=True)
class SimulationConfig:
    """Synthetic operating assumptions used by the Phase 2 teaching simulator."""

    step_minutes: int = 15
    episode_steps: int = 96
    command_mw: float = 25.0
    battery_capacity_mwh: float = 100.0
    battery_power_mw: float = 50.0
    battery_efficiency: float = 0.95
    initial_battery_soc: float = 0.5
    coal_ramp_mw_per_step: float = 20.0
    gas_ramp_mw_per_step: float = 40.0
    coal_minimum_fraction: float = 0.40
    gas_minimum_fraction: float = 0.20

    def __post_init__(self) -> None:
        positive = {
            "step_minutes": self.step_minutes,
            "episode_steps": self.episode_steps,
            "command_mw": self.command_mw,
            "battery_capacity_mwh": self.battery_capacity_mwh,
            "battery_power_mw": self.battery_power_mw,
            "coal_ramp_mw_per_step": self.coal_ramp_mw_per_step,
            "gas_ramp_mw_per_step": self.gas_ramp_mw_per_step,
        }
        if any(isinstance(value, bool) or value <= 0 for value in positive.values()):
            raise ValueError("Simulation magnitudes and episode length must be positive")
        if not 0 < self.battery_efficiency <= 1:
            raise ValueError("battery_efficiency must be in (0, 1]")
        if not 0 <= self.initial_battery_soc <= 1:
            raise ValueError("initial_battery_soc must be between 0 and 1")
        if not 0 <= self.coal_minimum_fraction <= 1 or not 0 <= self.gas_minimum_fraction <= 1:
            raise ValueError("Generator minimum fractions must be between 0 and 1")


@dataclass(frozen=True)
class FaultEvent:
    """An asset outage beginning at ``step`` and restored after its duration."""

    step: int
    asset_id: str
    duration_steps: int = 4

    def __post_init__(self) -> None:
        if isinstance(self.step, bool) or not isinstance(self.step, int) or self.step < 0:
            raise ValueError("Fault step must be a nonnegative integer")
        if (
            isinstance(self.duration_steps, bool)
            or not isinstance(self.duration_steps, int)
            or self.duration_steps <= 0
        ):
            raise ValueError("Fault duration must be positive")
        if not isinstance(self.asset_id, str) or not self.asset_id:
            raise ValueError("Fault asset_id must be a nonempty string")


class GridEnvironment:
    """Small deterministic simulator for policy development, not a power-flow tool.

    Profiles contain aggregate demand, solar, and wind values. Generator actions
    obey capacity, synthetic minimum-output, and per-step ramp constraints. Battery
    actions obey power, energy, and efficiency constraints. Runtime outages may
    disconnect assets, so initial-topology validation is not repeated after faults.
    """

    def __init__(
        self,
        topology: dict,
        profile: Sequence[Mapping[str, float]] | None = None,
        faults: Iterable[FaultEvent | Mapping[str, object]] | None = None,
        config: SimulationConfig | None = None,
        seed: int = 42,
    ):
        validate_grid(topology)
        self._initial = deepcopy(topology)
        self.config = config or SimulationConfig()
        self._profile = self._validate_profile(profile)
        self._faults = self._validate_faults(faults or [])
        self._seed = seed
        self._rng = random.Random(seed)
        self.topology: dict = {}
        self.current_step = 0
        self.battery_soc = self.config.initial_battery_soc
        self._active_faults: dict[str, int] = {}
        self._pre_fault_state: dict[str, dict[str, object]] = {}
        self._terminated = False
        self.reset()

    @property
    def horizon(self) -> int:
        return min(len(self._profile), self.config.episode_steps)

    def _validate_profile(
        self, profile: Sequence[Mapping[str, float]] | None
    ) -> list[dict[str, float]]:
        if profile is None:
            totals = grid_summary(self._initial)
            solar = sum(
                node.get("output_mw", 0.0)
                for node in self._initial["nodes"]
                if node.get("fuel") == "solar"
            )
            wind = sum(
                node.get("output_mw", 0.0)
                for node in self._initial["nodes"]
                if node.get("fuel") == "wind"
            )
            return [
                {"demand_mw": totals["demand_mw"], "solar_mw": solar, "wind_mw": wind}
                for _ in range(self.config.episode_steps)
            ]
        if not profile:
            raise ValueError("Simulation profile must contain at least one point")
        checked: list[dict[str, float]] = []
        for index, point in enumerate(profile):
            row: dict[str, float] = {}
            for field in ("demand_mw", "solar_mw", "wind_mw"):
                value = point.get(field)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"Profile {field} at index {index} must be numeric")
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"Profile {field} at index {index} must be finite and nonnegative")
                row[field] = float(value)
            checked.append(row)
        return checked

    def _validate_faults(
        self, faults: Iterable[FaultEvent | Mapping[str, object]]
    ) -> list[FaultEvent]:
        asset_ids = {node["id"] for node in self._initial["nodes"]}
        asset_ids.update(edge["id"] for edge in self._initial["edges"])
        checked: list[FaultEvent] = []
        for raw in faults:
            try:
                event = raw if isinstance(raw, FaultEvent) else FaultEvent(**raw)
            except TypeError as error:
                raise ValueError("Faults require step, asset_id, and optional duration_steps") from error
            if event.asset_id not in asset_ids:
                raise ValueError(f"Unknown fault asset: {event.asset_id}")
            if event.step >= min(len(self._profile), self.config.episode_steps):
                raise ValueError("Fault step must be inside the episode horizon")
            checked.append(event)
        return sorted(checked, key=lambda event: (event.step, event.asset_id))

    def reset(self, seed: int | None = None) -> dict:
        """Restore an independent initial state and return the first observation."""

        if seed is not None:
            self._seed = seed
        self._rng = random.Random(self._seed)
        self.topology = deepcopy(self._initial)
        self.current_step = 0
        self.battery_soc = self.config.initial_battery_soc
        self._active_faults = {}
        self._pre_fault_state = {}
        self._terminated = False
        self._synchronize_profile(0)
        self._update_faults(0)
        return asdict(self.observation())

    def observation(self) -> Observation:
        totals = grid_summary(self.topology)
        return Observation(
            demand_mw=totals["demand_mw"],
            generation_mw=totals["generation_mw"],
            reserve_mw=self._controllable_reserve(),
            battery_soc=self.battery_soc,
            renewable_trend=self._renewable_trend(),
            fault_present=bool(self._active_faults),
        )

    def valid_actions(self) -> tuple[Action, ...]:
        """Return physically available action categories for the current state."""

        if self._terminated:
            return ()
        actions = [Action.HOLD]
        if self._dispatchable_capacity(increase=True) > 0:
            actions.append(Action.INCREASE_GENERATION)
        if self._dispatchable_capacity(increase=False) > 0:
            actions.append(Action.DECREASE_GENERATION)
        if self._battery_charge_limit() > 0:
            actions.append(Action.CHARGE)
        if self._battery_discharge_limit() > 0:
            actions.append(Action.DISCHARGE)
        if self._sheddable_demand() > 0:
            actions.append(Action.SHED)
        return tuple(actions)

    def step(self, action: Action | str) -> tuple[dict, float, bool, dict]:
        """Apply one constrained action and advance one deterministic time step."""

        if self._terminated:
            raise RuntimeError("Episode has terminated; call reset before stepping again")
        try:
            selected = action if isinstance(action, Action) else Action(action)
        except ValueError as error:
            raise ValueError(f"Unknown action: {action}") from error

        valid_before = self.valid_actions()
        if selected not in valid_before:
            raise ValueError(f"Action {selected.value} is unavailable in the current state")

        applied_mw = 0.0
        battery_charge_mw = 0.0
        battery_discharge_mw = 0.0
        shed_mw = 0.0
        if selected == Action.INCREASE_GENERATION:
            applied_mw = self._adjust_dispatchable(self.config.command_mw, increase=True)
        elif selected == Action.DECREASE_GENERATION:
            applied_mw = self._adjust_dispatchable(self.config.command_mw, increase=False)
        elif selected == Action.CHARGE:
            battery_charge_mw = self._charge_battery()
            applied_mw = battery_charge_mw
        elif selected == Action.DISCHARGE:
            battery_discharge_mw = self._discharge_battery()
            applied_mw = battery_discharge_mw
        elif selected == Action.SHED:
            shed_mw = min(self.config.command_mw, self._sheddable_demand())
            applied_mw = shed_mw

        totals = grid_summary(self.topology)
        effective_generation = totals["generation_mw"] + battery_discharge_mw - battery_charge_mw
        disconnected_mw = self._disconnected_demand()
        connected_demand = max(0.0, totals["demand_mw"] - disconnected_mw - shed_mw)
        connected_shortage_mw = max(0.0, connected_demand - effective_generation)
        unserved_mw = disconnected_mw + shed_mw + connected_shortage_mw
        surplus_mw = max(0.0, effective_generation - connected_demand)
        metrics = self._metrics(unserved_mw, surplus_mw)
        reward = self._reward(metrics)

        info = {
            "step": self.current_step,
            "action": selected.value,
            "applied_mw": round(applied_mw, 6),
            "valid_actions": [item.value for item in valid_before],
            "battery_charge_mw": round(battery_charge_mw, 6),
            "battery_discharge_mw": round(battery_discharge_mw, 6),
            "shed_mw": round(shed_mw, 6),
            "unserved_mw": round(unserved_mw, 6),
            "surplus_mw": round(surplus_mw, 6),
            "disconnected_demand_mw": round(disconnected_mw, 6),
            "active_faults": sorted(self._active_faults),
            "metrics": {key: round(value, 6) for key, value in metrics.items()},
            "assurance": "synthetic aggregate simulation; no AC/DC power flow",
        }

        self.current_step += 1
        self._terminated = self.current_step >= self.horizon
        if not self._terminated:
            self._synchronize_profile(self.current_step)
            self._update_faults(self.current_step)
        next_observation = asdict(self.observation())
        return next_observation, reward, self._terminated, info

    def _synchronize_profile(self, step: int) -> None:
        point = self._profile[step]
        loads = [node for node in self.topology["nodes"] if node["kind"] == "load"]
        initial_total = sum(
            node["demand_mw"] for node in self._initial["nodes"] if node["kind"] == "load"
        )
        for node in loads:
            initial = next(item for item in self._initial["nodes"] if item["id"] == node["id"])
            node["demand_mw"] = point["demand_mw"] * initial["demand_mw"] / initial_total
        renewable = {"solar": point["solar_mw"], "wind": point["wind_mw"]}
        for fuel, available in renewable.items():
            plants = [node for node in self.topology["nodes"] if node.get("fuel") == fuel]
            capacity = sum(node["capacity_mw"] for node in plants)
            for node in plants:
                share = node["capacity_mw"] / capacity if capacity else 0.0
                node["output_mw"] = (
                    min(node["capacity_mw"], available * share)
                    if node["status"] == "online"
                    else 0.0
                )

    def _update_faults(self, step: int) -> None:
        for asset_id, restore_step in list(self._active_faults.items()):
            if step >= restore_step:
                self._restore_asset(asset_id)
        for event in self._faults:
            if event.step == step:
                self._fail_asset(event.asset_id, step + event.duration_steps)

    def _find_asset(self, asset_id: str) -> dict:
        for collection in (self.topology["nodes"], self.topology["edges"]):
            for asset in collection:
                if asset["id"] == asset_id:
                    return asset
        raise ValueError(f"Unknown asset: {asset_id}")

    def _fail_asset(self, asset_id: str, restore_step: int) -> None:
        asset = self._find_asset(asset_id)
        if asset_id not in self._active_faults:
            self._pre_fault_state[asset_id] = {
                "status": asset["status"],
                "output_mw": asset.get("output_mw"),
            }
        asset["status"] = "offline"
        if "output_mw" in asset:
            asset["output_mw"] = 0.0
        self._active_faults[asset_id] = max(
            restore_step, self._active_faults.get(asset_id, restore_step)
        )

    def _restore_asset(self, asset_id: str) -> None:
        asset = self._find_asset(asset_id)
        state = self._pre_fault_state.pop(asset_id)
        asset["status"] = state["status"]
        if state["output_mw"] is not None:
            asset["output_mw"] = state["output_mw"]
        del self._active_faults[asset_id]
        if not self._terminated:
            self._synchronize_profile(self.current_step)

    def _controllable_plants(self) -> list[dict]:
        return [
            node
            for node in self.topology["nodes"]
            if node["kind"] == "plant"
            and node.get("fuel") in {"coal", "gas"}
            and node["status"] == "online"
        ]

    def _ramp_limit(self, node: dict) -> float:
        return (
            self.config.gas_ramp_mw_per_step
            if node.get("fuel") == "gas"
            else self.config.coal_ramp_mw_per_step
        )

    def _minimum_output(self, node: dict) -> float:
        fraction = (
            self.config.gas_minimum_fraction
            if node.get("fuel") == "gas"
            else self.config.coal_minimum_fraction
        )
        return node["capacity_mw"] * fraction

    def _dispatchable_capacity(self, increase: bool) -> float:
        total = 0.0
        for node in self._controllable_plants():
            physical = (
                node["capacity_mw"] - node["output_mw"]
                if increase
                else node["output_mw"] - self._minimum_output(node)
            )
            total += max(0.0, min(physical, self._ramp_limit(node)))
        return total

    def _adjust_dispatchable(self, requested_mw: float, increase: bool) -> float:
        remaining = requested_mw
        plants = sorted(
            self._controllable_plants(),
            key=lambda node: (
                node.get("fuel") != "gas" if increase else node.get("fuel") != "coal",
                node["id"],
            ),
        )
        for node in plants:
            physical = (
                node["capacity_mw"] - node["output_mw"]
                if increase
                else node["output_mw"] - self._minimum_output(node)
            )
            amount = min(remaining, max(0.0, physical), self._ramp_limit(node))
            node["output_mw"] += amount if increase else -amount
            remaining -= amount
            if remaining <= 1e-9:
                break
        return requested_mw - remaining

    def _battery_charge_limit(self) -> float:
        duration = self.config.step_minutes / 60
        energy_room = (1 - self.battery_soc) * self.config.battery_capacity_mwh
        return max(
            0.0,
            min(self.config.battery_power_mw, energy_room / (duration * self.config.battery_efficiency)),
        )

    def _battery_discharge_limit(self) -> float:
        duration = self.config.step_minutes / 60
        available = self.battery_soc * self.config.battery_capacity_mwh
        return max(
            0.0,
            min(self.config.battery_power_mw, available * self.config.battery_efficiency / duration),
        )

    def _charge_battery(self) -> float:
        power = min(self.config.command_mw, self._battery_charge_limit())
        duration = self.config.step_minutes / 60
        self.battery_soc += (
            power * duration * self.config.battery_efficiency / self.config.battery_capacity_mwh
        )
        self.battery_soc = min(1.0, self.battery_soc)
        return power

    def _discharge_battery(self) -> float:
        power = min(self.config.command_mw, self._battery_discharge_limit())
        duration = self.config.step_minutes / 60
        self.battery_soc -= (
            power * duration / (self.config.battery_efficiency * self.config.battery_capacity_mwh)
        )
        self.battery_soc = max(0.0, self.battery_soc)
        return power

    def _sheddable_demand(self) -> float:
        return sum(
            node["demand_mw"]
            for node in self.topology["nodes"]
            if node["kind"] == "load"
            and node["status"] == "online"
            and node.get("priority") != "critical"
        )

    def _controllable_reserve(self) -> float:
        return sum(
            max(0.0, node["capacity_mw"] - node["output_mw"])
            for node in self._controllable_plants()
        )

    def _renewable_trend(self) -> float:
        if self.current_step + 1 >= self.horizon:
            return 0.0
        current = self._profile[self.current_step]["solar_mw"] + self._profile[self.current_step]["wind_mw"]
        future = self._profile[self.current_step + 1]["solar_mw"] + self._profile[self.current_step + 1]["wind_mw"]
        return max(-1.0, min(1.0, (future - current) / max(current, 1.0)))

    def _disconnected_demand(self) -> float:
        graph = nx.Graph()
        online_nodes = {
            node["id"] for node in self.topology["nodes"] if node["status"] == "online"
        }
        graph.add_nodes_from(online_nodes)
        for edge in self.topology["edges"]:
            if (
                edge["status"] == "online"
                and edge["source"] in online_nodes
                and edge["target"] in online_nodes
            ):
                graph.add_edge(edge["source"], edge["target"])
        plants = {
            node["id"]
            for node in self.topology["nodes"]
            if node["kind"] == "plant" and node["status"] == "online"
        }
        disconnected = 0.0
        for node in self.topology["nodes"]:
            if node["kind"] != "load":
                continue
            connected = node["id"] in graph and any(
                nx.has_path(graph, node["id"], plant) for plant in plants
            )
            if node["status"] != "online" or not connected:
                disconnected += node["demand_mw"]
        return disconnected

    def _metrics(self, unserved_mw: float, surplus_mw: float) -> dict[str, float]:
        duration = self.config.step_minutes / 60
        cost_rates = {"coal": 45.0, "gas": 70.0}
        emission_rates = {"coal": 900.0, "gas": 450.0}
        cost = sum(
            node["output_mw"] * duration * cost_rates.get(node.get("fuel"), 0.0)
            for node in self._controllable_plants()
        )
        emissions = sum(
            node["output_mw"] * duration * emission_rates.get(node.get("fuel"), 0.0)
            for node in self._controllable_plants()
        )
        return {
            "unserved_mwh": unserved_mw * duration,
            "curtailed_mwh": surplus_mw * duration,
            "operating_cost": cost,
            "emissions_kg": emissions,
            "constraint_violations": 0.0,
        }

    def _reward(self, metrics: Mapping[str, float]) -> float:
        demand_reference = max(
            self.observation().demand_mw * self.config.step_minutes / 60, 1.0
        )
        cost_reference = max(demand_reference * 100.0, 1.0)
        emissions_reference = max(demand_reference * 1000.0, 1.0)
        penalty = (
            10.0 * metrics["unserved_mwh"] / demand_reference
            + 0.5 * metrics["curtailed_mwh"] / demand_reference
            + metrics["operating_cost"] / cost_reference
            + 0.5 * metrics["emissions_kg"] / emissions_reference
            + 20.0 * metrics["constraint_violations"]
        )
        return round(-penalty, 8)
