"""Small NumPy LSTM used for reproducible Phase 2 forecasting experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from prism.forecasting.models import _validated_series


@dataclass(frozen=True)
class LSTMConfig:
    """Training settings kept deliberately small for a local academic prototype."""

    window: int = 24
    hidden_size: int = 8
    epochs: int = 12
    learning_rate: float = 0.01
    max_windows_per_epoch: int = 384
    seed: int = 42

    def __post_init__(self) -> None:
        integer_fields = (self.window, self.hidden_size, self.epochs, self.max_windows_per_epoch)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in integer_fields):
            raise ValueError("LSTM sizes, epochs, and sample limit must be positive integers")
        if not isinstance(self.learning_rate, (int, float)) or not math.isfinite(self.learning_rate) or self.learning_rate <= 0:
            raise ValueError("learning_rate must be finite and positive")


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30.0, 30.0)))


class LSTMForecaster:
    """Single-layer univariate LSTM with deterministic clipped SGD training.

    This implementation avoids a heavyweight framework while retaining the four
    standard LSTM gates and back-propagation through the complete input window.
    It is intended for reproducible comparison, not production-scale training.
    """

    def __init__(self, config: LSTMConfig | None = None) -> None:
        self.config = config or LSTMConfig()
        self.target: str | None = None
        self.mean = 0.0
        self.scale = 1.0
        self.loss_history: list[float] = []
        self._initialize()

    def _initialize(self) -> None:
        rng = np.random.default_rng(self.config.seed)
        hidden = self.config.hidden_size
        limit = 1.0 / math.sqrt(hidden + 1)
        self.weights = rng.uniform(-limit, limit, size=(4 * hidden, hidden + 1))
        self.bias = np.zeros(4 * hidden, dtype=float)
        self.bias[hidden : 2 * hidden] = 1.0
        self.output_weights = rng.uniform(-limit, limit, size=hidden)
        self.output_bias = 0.0

    def fit(self, frame: pd.DataFrame, target: str) -> "LSTMForecaster":
        values = _validated_series(frame, target)
        if len(values) <= self.config.window:
            raise ValueError(f"At least {self.config.window + 1} observations are required")
        self.target = target
        self.mean = float(values.mean())
        self.scale = float(values.std()) or 1.0
        scaled = (values - self.mean) / self.scale
        starts = np.arange(self.config.window, len(scaled))
        rng = np.random.default_rng(self.config.seed)
        self.loss_history = []
        for _ in range(self.config.epochs):
            order = rng.permutation(starts)
            selected = order[: self.config.max_windows_per_epoch]
            total_loss = 0.0
            for endpoint in selected:
                sequence = scaled[endpoint - self.config.window : endpoint]
                expected = float(scaled[endpoint])
                prediction, cache = self._forward(sequence)
                error = float(np.clip(prediction - expected, -5.0, 5.0))
                total_loss += error * error
                self._backward(cache, error)
            self.loss_history.append(round(total_loss / len(selected), 8))
        return self

    def _forward(self, sequence: np.ndarray) -> tuple[float, list[tuple]]:
        hidden = np.zeros(self.config.hidden_size, dtype=float)
        cell = np.zeros(self.config.hidden_size, dtype=float)
        cache: list[tuple] = []
        size = self.config.hidden_size
        for raw in sequence:
            previous_hidden = hidden
            previous_cell = cell
            joined = np.concatenate(([float(raw)], previous_hidden))
            gates = self.weights @ joined + self.bias
            input_gate = _sigmoid(gates[:size])
            forget_gate = _sigmoid(gates[size : 2 * size])
            output_gate = _sigmoid(gates[2 * size : 3 * size])
            candidate = np.tanh(gates[3 * size :])
            cell = forget_gate * previous_cell + input_gate * candidate
            hidden = output_gate * np.tanh(cell)
            cache.append((joined, previous_cell, input_gate, forget_gate, output_gate, candidate, cell))
        prediction = float(self.output_weights @ hidden + self.output_bias)
        return prediction, cache

    def _backward(self, cache: list[tuple], error: float) -> None:
        size = self.config.hidden_size
        final_hidden = cache[-1][4] * np.tanh(cache[-1][6])
        output_gradient = 2.0 * error
        gradient_output_weights = output_gradient * final_hidden
        gradient_output_bias = output_gradient
        hidden_gradient = output_gradient * self.output_weights
        cell_gradient = np.zeros(size, dtype=float)
        gradient_weights = np.zeros_like(self.weights)
        gradient_bias = np.zeros_like(self.bias)
        for joined, previous_cell, input_gate, forget_gate, output_gate, candidate, cell in reversed(cache):
            tanh_cell = np.tanh(cell)
            output_delta = hidden_gradient * tanh_cell * output_gate * (1.0 - output_gate)
            cell_total = cell_gradient + hidden_gradient * output_gate * (1.0 - tanh_cell**2)
            forget_delta = cell_total * previous_cell * forget_gate * (1.0 - forget_gate)
            input_delta = cell_total * candidate * input_gate * (1.0 - input_gate)
            candidate_delta = cell_total * input_gate * (1.0 - candidate**2)
            gate_delta = np.concatenate((input_delta, forget_delta, output_delta, candidate_delta))
            gradient_weights += np.outer(gate_delta, joined)
            gradient_bias += gate_delta
            joined_gradient = self.weights.T @ gate_delta
            hidden_gradient = joined_gradient[1:]
            cell_gradient = cell_total * forget_gate
        gradients = [gradient_weights, gradient_bias, gradient_output_weights]
        norm = math.sqrt(sum(float(np.sum(value**2)) for value in gradients) + gradient_output_bias**2)
        factor = min(1.0, 5.0 / max(norm, 1e-12))
        rate = self.config.learning_rate
        self.weights -= rate * factor * gradient_weights
        self.bias -= rate * factor * gradient_bias
        self.output_weights -= rate * factor * gradient_output_weights
        self.output_bias -= rate * factor * gradient_output_bias

    def predict(self, history: pd.DataFrame, horizon: int = 1) -> list[float]:
        if self.target is None:
            raise RuntimeError("Fit or load the forecaster before predicting")
        if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
            raise ValueError("horizon must be a positive integer")
        values = _validated_series(history, self.target).tolist()
        if len(values) < self.config.window:
            raise ValueError(f"At least {self.config.window} history observations are required")
        predictions: list[float] = []
        for _ in range(horizon):
            sequence = (np.asarray(values[-self.config.window :]) - self.mean) / self.scale
            scaled_prediction, _ = self._forward(sequence)
            prediction = max(0.0, float(scaled_prediction * self.scale + self.mean))
            values.append(prediction)
            predictions.append(prediction)
        return predictions

    def save(self, path: str | Path, metadata: dict | None = None) -> None:
        if self.target is None:
            raise RuntimeError("Fit the forecaster before saving")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "algorithm": "numpy_lstm",
            "target": self.target,
            "config": asdict(self.config),
            "normalization": {"mean": self.mean, "scale": self.scale},
            "loss_history": self.loss_history,
            "metadata": metadata or {},
            "weights": self.weights.tolist(),
            "bias": self.bias.tolist(),
            "output_weights": self.output_weights.tolist(),
            "output_bias": self.output_bias,
        }
        destination.write_text(json.dumps(payload, indent=2) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "LSTMForecaster":
        payload = json.loads(Path(path).read_text())
        if payload.get("schema_version") != "1.0" or payload.get("algorithm") != "numpy_lstm":
            raise ValueError("Unsupported LSTM artifact")
        model = cls(LSTMConfig(**payload["config"]))
        model.target = payload["target"]
        model.mean = float(payload["normalization"]["mean"])
        model.scale = float(payload["normalization"]["scale"])
        model.loss_history = [float(value) for value in payload.get("loss_history", [])]
        model.weights = np.asarray(payload["weights"], dtype=float)
        model.bias = np.asarray(payload["bias"], dtype=float)
        model.output_weights = np.asarray(payload["output_weights"], dtype=float)
        model.output_bias = float(payload["output_bias"])
        expected = (4 * model.config.hidden_size, model.config.hidden_size + 1)
        if model.weights.shape != expected or model.bias.shape != (expected[0],) or model.output_weights.shape != (model.config.hidden_size,):
            raise ValueError("LSTM artifact dimensions do not match its configuration")
        if not all(np.isfinite(value).all() for value in (model.weights, model.bias, model.output_weights)):
            raise ValueError("LSTM artifact contains nonfinite parameters")
        return model
