"""Immutable forecast bundles, validation-gated atomic promotion and rollback."""
from contextlib import contextmanager
from datetime import datetime,timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import os
import fcntl
from prism.config import ROOT

REGISTRY=ROOT/'artifacts/model-registry'


@contextmanager
def lock(root=REGISTRY):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    with (root/'registry.lock').open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def verify_bundle(version,root=REGISTRY):
    if not isinstance(version,str) or not re.fullmatch('[0-9a-f]{64}',version):raise ValueError('Invalid model version')
    folder=Path(root)/version;manifest=json.loads((folder/'manifest.json').read_text())
    if sha256(json.dumps(manifest['files'],sort_keys=True).encode()).hexdigest()!=version:raise ValueError('Bundle identity mismatch')
    if set(manifest['files'])!={'lstm.json','autoregressive.json','forecast_report.json'}:raise ValueError('Unsupported bundle files')
    for name,digest in manifest['files'].items():
        if sha256((folder/name).read_bytes()).hexdigest()!=digest:raise ValueError('Bundle file integrity mismatch')
    return folder,json.loads((folder/'forecast_report.json').read_text())


def active_bundle(root=REGISTRY):
    pointer=Path(root)/'current.json'
    if not pointer.exists():return None
    manifest=json.loads(pointer.read_text());folder,report=verify_bundle(manifest['version'],root)
    return dict(version=manifest['version'],folder=folder,report=report,previous=manifest.get('previous'))


def write_pointer(payload,root):
    root=Path(root);temporary=root/'current.tmp';temporary.write_text(json.dumps(payload,indent=2)+'\n');os.replace(temporary,root/'current.json')


def promote(version,current_rmse,minimum_improvement=.01,root=REGISTRY):
    folder,report=verify_bundle(version,root)
    selected=report['selected_on_validation'];score=float(report['metrics'][selected]['validation']['rmse'])
    if not math.isfinite(current_rmse) or current_rmse<=0 or not math.isfinite(score):raise ValueError('Invalid validation scores')
    if report['validation_origins']<10:raise ValueError('Too few validation origins')
    accepted=score<=current_rmse*(1-minimum_improvement)
    result=dict(version=version,promoted=accepted,candidate_validation_rmse=score,incumbent_validation_rmse=current_rmse,minimum_relative_improvement=minimum_improvement,
                basis='same validation origins only; test metrics do not select promotion')
    with lock(root):
        active=active_bundle(root)
        if accepted:
            write_pointer(dict(version=version,previous=active['version'] if active else None,promoted_at=datetime.now(timezone.utc).isoformat(),validation_gate=result),root)
        with (Path(root)/'events.jsonl').open('a') as stream:stream.write(json.dumps(dict(event='promotion_review',**result))+'\n')
    return result


def rollback(root=REGISTRY):
    with lock(root):
        active=active_bundle(root)
        if active is None or not active['previous']:raise ValueError('No prior promoted bundle available')
        previous=active['previous'];verify_bundle(previous,root)
        write_pointer(dict(version=previous,previous=active['version'],promoted_at=datetime.now(timezone.utc).isoformat(),reason='explicit_rollback'),root)
        with (Path(root)/'events.jsonl').open('a') as stream:stream.write(json.dumps(dict(event='rollback',version=previous,previous=active['version']))+'\n')
        return dict(version=previous,rolled_back=True)


def bootstrap(root=REGISTRY):
    """Register the unchanged reviewed baseline so the first promotion can roll back."""
    import tempfile
    import shutil
    with lock(root):
        active=active_bundle(root)
        if active:return active['version']
        with tempfile.TemporaryDirectory(dir=root,prefix='baseline-') as temporary:
            folder=Path(temporary)
            shutil.copyfile(ROOT/'models/forecasting/phase3_demand_lstm.json',folder/'lstm.json')
            shutil.copyfile(ROOT/'models/forecasting/phase3_demand_ar.json',folder/'autoregressive.json')
            report=json.loads((ROOT/'reports/phase3_real_forecasting.json').read_text());report['base_hourly_sha256']=report['hourly_sha256']
            (folder/'forecast_report.json').write_text(json.dumps(report,indent=2)+'\n')
            hashes={path.name:sha256(path.read_bytes()).hexdigest() for path in folder.iterdir()};version=sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
            (folder/'manifest.json').write_text(json.dumps({'files':hashes},indent=2)+'\n');target=Path(root)/version
            if not target.exists():folder.rename(target)
        verify_bundle(version,root)
        write_pointer(dict(version=version,previous=None,reason='unchanged_reviewed_baseline'),root)
        return version
