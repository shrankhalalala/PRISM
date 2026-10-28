"""Direct day-ahead ridge autoregression with known calendar covariates."""
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prism.forecasting.models import _validated_series, contiguous_endpoints, require_recent_window, AutoregressiveForecaster


@dataclass
class DirectDayAheadForecaster:
    ridge: float = 10.0
    coefficients: np.ndarray | None = None
    mean: float = 0.0
    scale: float = 1.0
    target: str = 'demand_mw'

    def _features(self, values, stamp):
        local = pd.Timestamp(stamp).tz_convert('Asia/Kolkata')
        angles = [2*np.pi*local.hour/24, 2*np.pi*local.dayofweek/7, 2*np.pi*local.dayofyear/365.25]
        return np.array([1., *((np.asarray(values)-self.mean)/self.scale), *[v for angle in angles for v in (np.sin(angle),np.cos(angle))]])

    def fit(self, frame, target='demand_mw'):
        if not np.isfinite(self.ridge) or self.ridge <= 0:
            raise ValueError('Ridge must be finite and positive')
        values = _validated_series(frame, target)
        self.target = target
        self.mean, self.scale = float(values.mean()), float(values.std()) or 1.
        ends = contiguous_endpoints(frame, 47)
        if not len(ends):
            raise ValueError('No contiguous 48-hour training blocks')
        origins = ends - 23
        x = np.asarray([self._features(values[i-24:i], frame.timestamp.iloc[i]) for i in origins])
        # Predict each horizon's departure from yesterday directly, without recursion.
        y = np.asarray([(values[i:i+24]-values[i-24:i])/self.scale for i in origins])
        penalty = np.eye(x.shape[1])*self.ridge
        penalty[0,0] = 0.
        self.coefficients = np.linalg.solve(x.T@x+penalty, x.T@y)
        return self

    def predict(self, history, horizon=24):
        if self.coefficients is None:
            raise RuntimeError('Fit or load model before predicting')
        if isinstance(horizon, bool) or not isinstance(horizon,int) or not 1 <= horizon <= 24:
            raise ValueError('Direct forecast horizon must be 1–24 hours')
        require_recent_window(history,24)
        values = _validated_series(history,self.target)[-24:]
        stamp = pd.Timestamp(history.timestamp.iloc[-1])+pd.Timedelta(hours=1)
        prediction = values + self.scale*(self._features(values,stamp)@self.coefficients)
        return np.maximum(0.,prediction[:horizon]).tolist()

    def save(self,path,metadata):
        Path(path).write_text(json.dumps(dict(algorithm='direct_day_ahead_ridge',lags=24,horizon=24,target=self.target,ridge=self.ridge,mean=self.mean,scale=self.scale,coefficients=self.coefficients.tolist(),**metadata),indent=2)+'\n')


def load_autoregressive(path):
    payload = json.loads(Path(path).read_text())
    coefficients = np.asarray(payload['coefficients'],dtype=float)
    if payload.get('algorithm') == 'direct_day_ahead_ridge':
        model = DirectDayAheadForecaster(ridge=payload['ridge'],mean=payload['mean'],scale=payload['scale'],target=payload['target'])
        if coefficients.shape != (31,24) or not np.isfinite([model.mean,model.scale,model.ridge]).all() or model.scale <= 0 or model.ridge <= 0:
            raise ValueError('Invalid direct autoregressive artifact')
    else:
        model = AutoregressiveForecaster(lags=payload['lags'])
        model.target = payload['target']
        if coefficients.shape != (model.lags+1,):
            raise ValueError('Invalid autoregressive dimensions')
    if not np.isfinite(coefficients).all():
        raise ValueError('Nonfinite autoregressive parameters')
    model.coefficients = coefficients
    return model
