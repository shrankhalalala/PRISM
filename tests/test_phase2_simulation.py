"""Behavioral tests for the first Phase 2 simulation increment."""

import unittest

import pandas as pd

from prism.grid.model import synthetic_grid
from prism.simulation import (
    Action,
    FaultEvent,
    GridEnvironment,
    SimulationConfig,
    quarter_hour_profile,
)


class ProfileTests(unittest.TestCase):
    def test_hourly_profile_is_interpolated_without_mutating_input(self):
        frame = pd.DataFrame(
            [
                {"demand_mw": 100, "solar_mw": 0, "wind_mw": 20},
                {"demand_mw": 200, "solar_mw": 40, "wind_mw": 40},
            ]
        )
        original = frame.copy(deep=True)
        profile = quarter_hour_profile(frame, hours=2)
        self.assertEqual(len(profile), 8)
        self.assertEqual(profile[1]["demand_mw"], 125)
        self.assertEqual(profile[4]["demand_mw"], 200)
        pd.testing.assert_frame_equal(frame, original)

    def test_profile_validation(self):
        with self.assertRaises(ValueError):
            quarter_hour_profile(pd.DataFrame([{"demand_mw": 1}]))
        with self.assertRaises(ValueError):
            GridEnvironment(synthetic_grid(), profile=[])


class DynamicsTests(unittest.TestCase):
    def make_environment(self, **kwargs):
        profile = [
            {"demand_mw": 700, "solar_mw": 120, "wind_mw": 80},
            {"demand_mw": 725, "solar_mw": 100, "wind_mw": 75},
            {"demand_mw": 750, "solar_mw": 80, "wind_mw": 70},
            {"demand_mw": 700, "solar_mw": 120, "wind_mw": 80},
        ]
        config = SimulationConfig(episode_steps=4)
        return GridEnvironment(synthetic_grid(), profile=profile, config=config, **kwargs)

    def test_generation_actions_obey_quantum_and_ramp(self):
        environment = self.make_environment()
        before = environment.observation().generation_mw
        observation, _, _, info = environment.step(Action.INCREASE_GENERATION)
        self.assertEqual(info["applied_mw"], 25)
        # The next profile reduces renewable availability by 25 MW, cancelling
        # the dispatch increase in the returned next-step observation.
        self.assertEqual(observation["generation_mw"], before)
        gas = next(node for node in environment.topology["nodes"] if node["id"] == "gas")
        self.assertEqual(gas["output_mw"], 125)

    def test_battery_energy_is_bounded_and_reset(self):
        environment = self.make_environment()
        initial = environment.observation().battery_soc
        _, _, _, info = environment.step(Action.DISCHARGE)
        self.assertEqual(info["battery_discharge_mw"], 25)
        self.assertLess(environment.battery_soc, initial)
        reset = environment.reset()
        self.assertEqual(reset["battery_soc"], initial)

    def test_fault_activates_and_restores_deterministically(self):
        environment = self.make_environment(
            faults=[FaultEvent(step=1, asset_id="gas", duration_steps=2)]
        )
        first, _, _, _ = environment.step(Action.HOLD)
        self.assertTrue(first["fault_present"])
        self.assertEqual(
            next(node for node in environment.topology["nodes"] if node["id"] == "gas")["status"],
            "offline",
        )
        environment.step(Action.HOLD)
        restored, _, _, _ = environment.step(Action.HOLD)
        self.assertFalse(restored["fault_present"])

    def test_line_outage_can_disconnect_load(self):
        environment = self.make_environment(
            faults=[FaultEvent(step=0, asset_id="line_09", duration_steps=1)]
        )
        _, _, _, info = environment.step(Action.HOLD)
        self.assertEqual(info["disconnected_demand_mw"], 160)
        self.assertGreaterEqual(info["unserved_mw"], 160)

    def test_episode_termination_and_post_terminal_guard(self):
        environment = self.make_environment()
        for index in range(4):
            _, _, terminated, _ = environment.step(Action.HOLD)
            self.assertEqual(terminated, index == 3)
        self.assertEqual(environment.valid_actions(), ())
        with self.assertRaises(RuntimeError):
            environment.step(Action.HOLD)

    def test_invalid_action_and_fault_inputs(self):
        environment = self.make_environment()
        with self.assertRaises(ValueError):
            environment.step("not_an_action")
        with self.assertRaises(ValueError):
            self.make_environment(faults=[{"step": 0, "asset_id": "unknown"}])
        with self.assertRaises(ValueError):
            self.make_environment(faults=[{"step": 0.5, "asset_id": "gas"}])


if __name__ == "__main__":
    unittest.main()
