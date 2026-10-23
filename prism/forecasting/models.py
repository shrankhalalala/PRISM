"""Reproducible forecasting baselines that require only NumPy and pandas."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
import pandas as pd


TARGETS = ("demand_mw", "solar_mw", "wind_mw")


def _validated_series(frame: pd.DataFrame, target: str) -> np.ndarray:
    if target not in TARGETS:
        raise ValueError(f"target must be one of {', '.join(TARGETS)}")
    if target not in frame:
        raise ValueError(f"Missing target column: {target}")
    values = pd.to_numeric(frame[target], errors="coerce").to_numpy(dtype=float)
    if not len(values) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"{target} must contain finite nonnegative observations")
    return values



def contiguous_endpoints(frame: pd.DataFrame, window: int, include_target: bool = True) -> np.ndarray:
    """Return positional windows; timestamp gaps may never become adjacent samples."""
    end = len(frame) if include_target else len(frame)+1
    starts = np.arange(window, end)
    if 'timestamp' not in frame:
        return starts
    times = pd.to_datetime(frame['timestamp'], utc=True, errors='raise')
    if times.isna().any() or times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError('Timestamps must be unique and ordered')
    return np.asarray([i for i in starts if all(
        (times.iloc[j]-times.iloc[j-1]) == pd.Timedelta(hours=1)
        for j in range(i-window+1, i+1 if include_target else i))], dtype=int)


def require_recent_window(frame: pd.DataFrame, window: int) -> None:
    if len(frame) < window or len(frame) not in contiguous_endpoints(frame, window, False):
        raise ValueError('Latest input window is incomplete or contains timestamp gaps')


def persistence_forecast(frame: pd.DataFrame, target: str, horizon: int = 1) -> list[float]:
    """Repeat the latest observation as a transparent benchmark forecast."""

    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    values = _validated_series(frame, target)
    return [float(values[-1])] * horizon


@dataclass
class AutoregressiveForecaster:
    """Ridge-regularized univariate autoregression for Phase 2 comparison."""

    lags: int = 24
    ridge: float = 1.0
    coefficients: np.ndarray | None = None
    target: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.lags, bool) or not isinstance(self.lags, int) or self.lags < 1:
            raise ValueError("lags must be a positive integer")
        if not isinstance(self.ridge, (int, float)) or not math.isfinite(self.ridge) or self.ridge < 0:
            raise ValueError("ridge must be finite and nonnegative")

    def fit(self, frame: pd.DataFrame, target: str) -> "AutoregressiveForecaster":
        values = _validated_series(frame, target)
        if len(values) <= self.lags:
            raise ValueError(f"At least {self.lags + 1} observations are required")
        endpoints = contiguous_endpoints(frame, self.lags)
        if not len(endpoints):raise ValueError('No contiguous training windows')
        features = np.asarray([values[index-self.lags:index] for index in endpoints])
        response = values[endpoints]
        design = np.column_stack([np.ones(len(features)), features])
        penalty = np.eye(design.shape[1]) * self.ridge
        penalty[0, 0] = 0.0
        self.coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ response)
        self.target = target
        return self

    def predict(self, history: pd.DataFrame, horizon: int = 1) -> list[float]:
        if self.coefficients is None or self.target is None:
            raise RuntimeError("Fit the forecaster before predicting")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
            raise ValueError("horizon must be a positive integer")
        values = _validated_series(history, self.target).tolist()
        if len(values) < self.lags:
            raise ValueError(f"At least {self.lags} history observations are required")
        require_recent_window(history, self.lags)
        predictions: list[float] = []
        for _ in range(horizon):
            features = np.asarray([1.0, *values[-self.lags :]])
            prediction = max(0.0, float(features @ self.coefficients))
            values.append(prediction)
            predictions.append(prediction)
        return predictions


def forecast_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    """Return MAE and RMSE without unsafe percentage-error assumptions."""

    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    if actual_values.shape != predicted_values.shape or actual_values.size == 0:
        raise ValueError("actual and predicted must be nonempty and have the same shape")
    if not np.isfinite(actual_values).all() or not np.isfinite(predicted_values).all():
        raise ValueError("forecast inputs must be finite")
    errors = predicted_values - actual_values
    return {
        "mae": round(float(np.mean(np.abs(errors))), 6),
        "rmse": round(float(np.sqrt(np.mean(errors**2))), 6),
    }
