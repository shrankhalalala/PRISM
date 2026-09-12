"""Deterministic aggregate dispatch prototype, not an operational optimizer."""
import math
from dataclasses import asdict
from prism.simulation.environment import Observation, Action


def validate_observation(state: Observation) -> None:
    """Reject invalid magnitudes, nonfinite inputs, and wrong field types."""
    for key, value in asdict(state).items():
        if key == "fault_present":
            if not isinstance(value, bool):
                raise ValueError("fault_present must be boolean")
        elif isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    if min(state.demand_mw,state.generation_mw,state.reserve_mw) < 0:
        raise ValueError("Power and reserve must be nonnegative")
    if not 0 <= state.battery_soc <= 1:
        raise ValueError("battery_soc must be between 0 and 1")
    if not -1 <= state.renewable_trend <= 1:
        raise ValueError("renewable_trend must be between -1 and 1")


def recommend(state: Observation) -> dict:
    """Suggest an aggregate adjustment; feasibility is limited to reserve only."""
    validate_observation(state)
    gap = state.demand_mw-state.generation_mw
    if abs(gap) <= 1:
        action, amount, reason, feasible = Action.HOLD, 0, "Supply and demand are within the 1 MW demo deadband.", True
    elif gap > 0 and state.reserve_mw > 0:
        action, amount = Action.INCREASE_GENERATION, min(gap,state.reserve_mw)
        feasible = gap <= state.reserve_mw
        reason = "Use available controllable reserve; any residual shortage needs further planning."
    elif gap > 0:
        action, amount, reason, feasible = Action.SHED, gap, "No reserve available; eligible load must be checked before shedding.", False
    else:
        action, amount, reason, feasible = Action.DECREASE_GENERATION, -gap, "Surplus exists; minimum output and ramp limits must be checked.", False
    return dict(policy="rule_based_prototype", action=action.value, requested_mw=amount, reason=reason, feasible=feasible,
                feasibility_scope="aggregate_reserve_only", executable=False, unmet_gap_mw=max(0,gap-(amount if action==Action.INCREASE_GENERATION else 0)))


def encode_state(state: Observation) -> tuple[int, int, int, int, int]:
    """Proposed fixed bins: 5 gap × 3 trend × 3 SOC × 3 reserve × 2 fault = 270."""
    validate_observation(state)
    ratio=(state.demand_mw-state.generation_mw)/max(state.demand_mw,1)
    gap=sum(ratio > boundary for boundary in [-0.1,-0.02,0.02,0.1])
    trend=0 if state.renewable_trend < -0.05 else 2 if state.renewable_trend > 0.05 else 1
    soc=0 if state.battery_soc < 0.2 else 2 if state.battery_soc > 0.8 else 1
    reserve_ratio=state.reserve_mw/max(state.demand_mw,1)
    reserve=0 if reserve_ratio < 0.05 else 2 if reserve_ratio > 0.2 else 1
    return gap,trend,soc,reserve,int(state.fault_present)
