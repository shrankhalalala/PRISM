"""Train and chronologically compare Phase 2 forecasting models."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pandas as pd

from prism.config import DATA_DIR, ROOT
from prism.forecasting import AutoregressiveForecaster, LSTMConfig, LSTMForecaster, forecast_metrics
from prism.forecasting.models import TARGETS


def _walk_forward(model, history: pd.DataFrame, test: pd.DataFrame, target: str) -> list[float]:
    working = history.copy()
    predictions: list[float] = []
    for _, row in test.iterrows():
        predictions.append(float(model.predict(working, horizon=1)[0]))
        working = pd.concat([working, row.to_frame().T], ignore_index=True)
    return predictions


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/phase2_forecasting.json")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models/forecasting")
    arguments = parser.parse_args()
    source = DATA_DIR / "processed/measurements.csv"
    frame = pd.read_csv(source)
    train_end = int(len(frame) * 0.70)
    validation_end = int(len(frame) * 0.85)
    train = frame.iloc[:train_end].copy()
    validation = frame.iloc[train_end:validation_end].copy()
    test = frame.iloc[validation_end:].copy()
    if len(train) <= 24 or validation.empty or test.empty:
        raise ValueError("Dataset is too short for the 70/15/15 chronological split")

    results = {
        "schema_version": "2.0",
        "data_source": "synthetic_seed_42",
        "data_sha256": _checksum(source),
        "split": {"method": "chronological_70_15_15", "training_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "evaluation": "one_step_walk_forward_with_actual_history",
        "targets": {},
    }
    for offset, target in enumerate(TARGETS):
        autoregressive = AutoregressiveForecaster(lags=24).fit(train, target)
        lstm = LSTMForecaster(LSTMConfig(epochs=arguments.epochs, seed=arguments.seed + offset)).fit(train, target)
        artifact = arguments.model_dir / f"{target}_lstm.json"
        lstm.save(artifact, metadata={"data_source": "synthetic_seed_42", "training_rows": len(train), "split": "chronological_70_15_15"})
        target_results: dict[str, object] = {"lstm_artifact": str(artifact.relative_to(ROOT)), "lstm_sha256": _checksum(artifact), "validation": {}, "test": {}}
        for split_name, preceding, held_out in (("validation", train, validation), ("test", frame.iloc[:validation_end].copy(), test)):
            persistence: list[float] = []
            working = preceding.copy()
            for _, row in held_out.iterrows():
                persistence.append(float(working[target].iloc[-1]))
                working = pd.concat([working, row.to_frame().T], ignore_index=True)
            target_results[split_name] = {
                "persistence": forecast_metrics(held_out[target], persistence),
                "autoregressive": forecast_metrics(held_out[target], _walk_forward(autoregressive, preceding, held_out, target)),
                "lstm": forecast_metrics(held_out[target], _walk_forward(lstm, preceding, held_out, target)),
            }
        target_results["lstm_training"] = {
            "config": asdict(lstm.config),
            "final_scaled_mse": lstm.loss_history[-1],
        }
        results["targets"][target] = target_results

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    print(f"Saved evaluation to {arguments.output}")


if __name__ == "__main__":
    main()
