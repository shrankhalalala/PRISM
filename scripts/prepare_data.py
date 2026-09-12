"""Run from repository root: python -m scripts.prepare_data."""
import argparse
import json
from pathlib import Path
from prism.data.pipeline import preprocess

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path("data/raw/synthetic_measurements.csv"))
    parser.add_argument("--output",type=Path,default=Path("data/processed/measurements.csv"))
    parser.add_argument("--audit",type=Path,default=Path("data/processed/quality_report.json"))
    args=parser.parse_args()
    print(json.dumps(preprocess(args.input,args.output,args.audit),indent=2))
