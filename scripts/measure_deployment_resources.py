"""Read actual container memory peaks/caps and versions without exposing environment secrets."""
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import subprocess


def run(arguments):return subprocess.check_output(arguments,text=True).strip()


def main():
    components={}
    for service in ['web','worker','beat','collector','redis','postgres','neo4j']:
        name='prism-phase3-reference-'+service+'-1'
        config=json.loads(run(['docker','inspect','--format','{{json .HostConfig.Memory}}',name]))
        state=json.loads(run(['docker','inspect','--format','{{json .State}}',name]))
        peak=int(run(['docker','exec',name,'cat','/sys/fs/cgroup/memory.peak']))
        components[service]=dict(running=state['Running'],restart_count=int(run(['docker','inspect','--format','{{.RestartCount}}',name])),
            peak_cgroup_memory_bytes=peak,memory_limit_bytes=config,below_4_gib=peak<4*1024**3)
    result=dict(measured_at=datetime.now(timezone.utc).isoformat(),host=dict(system=platform.system(),architecture=platform.machine(),
        physical_memory_bytes=int(run(['sysctl','-n','hw.memsize']))),components=components,
        image_id=run(['docker','inspect','--format','{{.Image}}','prism-phase3-reference-web-1']),
        app_user=run(['docker','inspect','--format','{{.Config.User}}','prism-phase3-reference-web-1']),
        scope='cgroup lifetime peaks after local verification, including cache; memory limits are configuration, not observed demand. Short workload, not a saturation or long-duration test.')
    assert result['app_user']=='prism' and all(c['running'] and c['below_4_gib'] for c in components.values())
    Path('reports/phase3_resources.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
