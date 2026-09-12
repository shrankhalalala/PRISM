"""Create reproducible Phase 1 synthetic fixtures; no live data is fetched."""
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from prism.config import DATA_DIR
from prism.grid.model import synthetic_grid, validate_grid


def generate():
    """Write 336 hourly observations using fixed dates and seed 42."""
    rng=random.Random(42)
    raw=DATA_DIR / "raw"
    raw.mkdir(parents=True,exist_ok=True)
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    with (raw / "synthetic_measurements.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["timestamp","demand_mw","solar_mw","wind_mw","frequency_hz","source"])
        writer.writeheader()
        for i in range(336):
            hour=i%24
            writer.writerow(dict(timestamp=(start+timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                demand_mw=round(620+100*math.sin((hour-8)*math.pi/12)+rng.uniform(-15,15),2),
                solar_mw=round(max(0,180*math.sin((hour-6)*math.pi/12))*rng.uniform(.85,1),2),
                wind_mw=round(65+20*math.sin(i/9)+rng.uniform(-5,5),2),
                frequency_hz=round(50+rng.uniform(-.025,.025),4),source="synthetic_seed_42"))
    grid=synthetic_grid()
    validate_grid(grid)
    (raw / "grid.json").write_text(json.dumps(grid,indent=2)+"\n")
    print("Created synthetic grid and 336 hourly measurements (seed 42).")

if __name__ == "__main__":
    generate()
