"""Phase 1 environment contract. Dynamics are intentionally unimplemented."""
from copy import deepcopy
from dataclasses import dataclass, asdict
from enum import Enum
from prism.grid.model import validate_grid, grid_summary


class Action(str, Enum):
    HOLD = "hold"
    INCREASE_GENERATION = "increase_generation"
    DECREASE_GENERATION = "decrease_generation"
    CHARGE = "charge_battery"
    DISCHARGE = "discharge_battery"
    SHED = "shed_load"


@dataclass(frozen=True)
class Observation:
    """Aggregate inputs shared by baseline and future Q-learning policy."""
    demand_mw: float
    generation_mw: float
    reserve_mw: float
    battery_soc: float = 0.5
    renewable_trend: float = 0.0
    fault_present: bool = False


class GridEnvironment:
    """Own an isolated topology snapshot; future step returns obs,reward,done,info."""
    def __init__(self, topology: dict):
        validate_grid(topology)
        self._initial = deepcopy(topology)
        self.topology = deepcopy(topology)

    def reset(self) -> dict:
        """Restore independent initial state and return aggregate observation."""
        self.topology = deepcopy(self._initial)
        totals = grid_summary(self.topology)
        reserve = sum(n["capacity_mw"]-n["output_mw"] for n in self.topology["nodes"] if n["kind"]=="plant" and n.get("fuel") in {"coal","gas"} and n["status"]=="online")
        return asdict(Observation(totals["demand_mw"], totals["generation_mw"], reserve))

    def step(self, action: Action):
        """Placeholder until Phase 2 implements physical state transitions."""
        raise NotImplementedError("State transitions and rewards are scheduled for Phase 2")
