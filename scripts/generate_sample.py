"""Create reproducible Phase 1 synthetic fixtures; no live data is fetched."""
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from prism.config import DATA_DIR
from prism.grid.model import synthetic_grid, validate_grid


HOURS = 24 * 90


def generate():
    """Write a 90-day hourly development series using fixed dates and seed 42."""
    rng=random.Random(42)
    raw=DATA_DIR / "raw"
    raw.mkdir(parents=True,exist_ok=True)
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    with (raw / "synthetic_measurements.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["timestamp","demand_mw","solar_mw","wind_mw","frequency_hz","source"],lineterminator="\n")
        writer.writeheader()
        for i in range(HOURS):
            hour=i%24
            day=i/24
            weekly=24*math.sin(2*math.pi*day/7)
            seasonal=35*math.sin(2*math.pi*day/90)
            writer.writerow(dict(timestamp=(start+timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                demand_mw=round(620+100*math.sin((hour-8)*math.pi/12)+weekly+seasonal+rng.uniform(-15,15),2),
                solar_mw=round(max(0,180*math.sin((hour-6)*math.pi/12))*(.9+.08*math.sin(day/8))*rng.uniform(.85,1),2),
                wind_mw=round(65+20*math.sin(i/9)+10*math.sin(day/5)+rng.uniform(-5,5),2),
                frequency_hz=round(50+rng.uniform(-.025,.025),4),source="synthetic_seed_42"))
    grid=synthetic_grid()
    validate_grid(grid)
    (raw / "grid.json").write_text(json.dumps(grid,indent=2)+"\n")
    print(f"Created synthetic grid and {HOURS} hourly measurements (seed 42).")

if __name__ == "__main__":
    generate()
