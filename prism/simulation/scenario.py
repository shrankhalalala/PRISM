"""Adapters that create reproducible simulation profiles from validated data."""

from __future__ import annotations

import math

import pandas as pd


def quarter_hour_profile(frame: pd.DataFrame, hours: int = 24) -> list[dict[str, float]]:
    """Linearly interpolate hourly measurements into a 15-minute profile.

    The final hourly observation is held for its remaining three quarter-hours.
    This is an explicit synthetic simulation adapter, not missing-data imputation.
    """

    required = {"demand_mw", "solar_mw", "wind_mw"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Profile input is missing columns: {', '.join(sorted(missing))}")
    if isinstance(hours, bool) or not isinstance(hours, int) or hours < 1:
        raise ValueError("hours must be a positive integer")
    selected = frame.tail(hours).reset_index(drop=True)
    if selected.empty:
        raise ValueError("Profile input must contain observations")
    for column in required:
        values = pd.to_numeric(selected[column], errors="coerce")
        if values.isna().any() or not values.map(math.isfinite).all() or (values < 0).any():
            raise ValueError(f"Profile column {column} must be finite and nonnegative")
        selected[column] = values.astype(float)

    profile: list[dict[str, float]] = []
    rows = selected[list(sorted(required))].to_dict(orient="records")
    for index, current in enumerate(rows):
        following = rows[min(index + 1, len(rows) - 1)]
        for quarter in range(4):
            fraction = quarter / 4
            profile.append(
                {
                    field: current[field] + (following[field] - current[field]) * fraction
                    for field in required
                }
            )
    return profile
