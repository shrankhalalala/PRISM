"""Evaluate Phase 2 persistence and autoregressive forecasts chronologically."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from prism.config import DATA_DIR, ROOT
from prism.forecasting import AutoregressiveForecaster, forecast_metrics
from prism.forecasting.models import TARGETS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-hours", type=int, default=48)
    parser.add_argument("--lags", type=int, default=24)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/forecasting/phase2_baselines.json",
    )
    arguments = parser.parse_args()
    frame = pd.read_csv(DATA_DIR / "processed/measurements.csv")
    if not arguments.lags < len(frame) - arguments.test_hours:
        raise ValueError("Training period must contain more observations than the lag window")
    if arguments.test_hours < 1:
        raise ValueError("test-hours must be positive")

    split = len(frame) - arguments.test_hours
    train = frame.iloc[:split].copy()
    test = frame.iloc[split:].copy()
    results = {
        "schema_version": "1.0",
        "data_source": "synthetic_seed_42",
        "split": {"training_rows": len(train), "test_rows": len(test)},
        "targets": {},
    }
    for target in TARGETS:
        model = AutoregressiveForecaster(lags=arguments.lags).fit(train, target)
        autoregressive = model.predict(train, horizon=len(test))
        persistence = [float(train[target].iloc[-1])] * len(test)
        results["targets"][target] = {
            "persistence": forecast_metrics(test[target], persistence),
            "autoregressive": forecast_metrics(test[target], autoregressive),
        }

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    print(f"Saved evaluation to {arguments.output}")


if __name__ == "__main__":
    main()
