"""Strict hourly measurement preparation. Never impute or relabel source data."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

FIELDS = ["timestamp", "demand_mw", "solar_mw", "wind_mw", "frequency_hz", "source"]
NUMERIC = FIELDS[1:5]


def clean_measurements(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return sorted valid rows and a rejection/gap audit without filling gaps.

    Timestamps must explicitly include Z or a numeric UTC offset. All duplicate
    timestamps are rejected to avoid silently selecting conflicting observations.
    Bounds are ingestion sanity checks, not grid protection thresholds.
    """
    missing = set(FIELDS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    df = frame[FIELDS].copy().reset_index(drop=True)
    offset = df.timestamp.astype(str).str.contains(r"(?:Z|[+-]\d{2}:\d{2})$", regex=True)
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True, errors="coerce", format="mixed")
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    reasons = pd.DataFrame(index=df.index)
    reasons["invalid_timestamp"] = df.timestamp.isna() | ~offset
    reasons["non_hourly_timestamp"] = df.timestamp.notna() & (df.timestamp != df.timestamp.dt.floor("h"))
    reasons["invalid_numeric"] = ~np.isfinite(df[NUMERIC]).all(axis=1)
    reasons["negative_power"] = (df[NUMERIC[:3]] < 0).any(axis=1)
    reasons["frequency_out_of_bounds"] = ~df.frequency_hz.between(45, 55)
    reasons["missing_source"] = df.source.isna() | df.source.astype(str).str.strip().eq("")
    reasons["duplicate_timestamp"] = df.timestamp.notna() & df.timestamp.duplicated(keep=False)
    rejected = reasons.any(axis=1)
    cleaned = df.loc[~rejected].sort_values("timestamp").copy()
    gaps = []
    times = cleaned.timestamp.tolist()
    for earlier, later in zip(times, times[1:]):
        hours = (later - earlier).total_seconds() / 3600
        if hours > 1:
            gaps.append({"after": earlier.isoformat(), "before": later.isoformat(), "missing_hours": int(hours)-1})
    cleaned["timestamp"] = cleaned.timestamp.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    cleaned["quality_flag"] = "validated"
    report = {"input_rows": len(df), "accepted_rows": len(cleaned), "rejected_rows": int(rejected.sum()),
              "reasons": {col: int(reasons[col].sum()) for col in reasons},
              "gaps": gaps, "imputed_rows": 0, "cadence": "hourly", "timezone": "UTC"}
    return cleaned.reset_index(drop=True), report


def preprocess(source: Path, destination: Path, audit_path: Path) -> dict:
    """Validate CSV and write canonical measurements plus machine-readable audit."""
    cleaned, report = clean_measurements(pd.read_csv(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(destination, index=False)
    audit_path.write_text(json.dumps(report, indent=2) + "\n")
    return report
