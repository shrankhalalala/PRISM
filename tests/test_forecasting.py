"""Tests for Phase 2 forecasting baselines and chronological evaluation helpers."""

import unittest

import pandas as pd

from prism.forecasting import AutoregressiveForecaster, forecast_metrics, persistence_forecast


class ForecastingTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            {
                "demand_mw": [100 + index * 2 for index in range(40)],
                "solar_mw": [max(0, 20 - abs(20 - index)) for index in range(40)],
                "wind_mw": [30 + index % 4 for index in range(40)],
            }
        )

    def test_persistence_repeats_latest_value(self):
        self.assertEqual(persistence_forecast(self.frame, "demand_mw", 3), [178.0] * 3)

    def test_autoregression_fits_and_forecasts_without_negative_power(self):
        model = AutoregressiveForecaster(lags=6, ridge=0.1).fit(self.frame, "demand_mw")
        forecast = model.predict(self.frame, horizon=4)
        self.assertEqual(len(forecast), 4)
        self.assertTrue(all(value >= 0 for value in forecast))
        self.assertAlmostEqual(forecast[0], 180, delta=1)

    def test_metrics_and_validation(self):
        self.assertEqual(forecast_metrics([1, 2], [2, 2]), {"mae": 0.5, "rmse": 0.707107})
        with self.assertRaises(ValueError):
            persistence_forecast(self.frame, "unknown")
        with self.assertRaises(RuntimeError):
            AutoregressiveForecaster(lags=2).predict(self.frame)


if __name__ == "__main__":
    unittest.main()
