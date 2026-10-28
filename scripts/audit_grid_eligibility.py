"""Write the machine-readable electrical-data acquisition checklist."""
import json
from pathlib import Path
from prism.grid.reference import build_reference
from prism.grid.eligibility import electrical_readiness

if __name__ == '__main__':
    report = electrical_readiness(build_reference())
    Path('reports/phase3_grid_eligibility.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='circuit_requirements'}, indent=2))
