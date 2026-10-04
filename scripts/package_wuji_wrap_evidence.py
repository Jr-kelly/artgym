"""Curated evidence with full physical sequences for selected force experiments."""
import argparse,json
from pathlib import Path
from scripts.build_wuji_wrap_recovery import B,R,write_packet


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    paths=[B/'continuous/index-wrap-v8-direct-corner-mass-corrected-v4',
           B/'validation/wrap-frozen-v12-load035-v1',B/'validation/wrap-frozen-v12-load050-v1',
           B/'validation/wrap-frozen-v12-joint-pulse-v1']
    paths += [B/'validation'/('wrap-direct-corner-geometry'+sid+'-v14') for sid in ['012','013','014','015']]
    # A modest number of causal intervention traces, not every historical run.
    for pattern in ['remote-multiregion*v17','remote-reverse*v19','remote-corner-*v20',
                    '*v21','*v22','*v23','*v24r2','*v27','*v28','*v29r1','*v30','*final-only*v39']:
        paths += [p.relative_to(R) for p in (R/B/'validation').glob(pattern)]
    paths += [B/'measurement'/name for name in [
        'index-wrap-pressure080-series-v8','source2-pressure080-series-v8',
        'index-wrap-pressure080-series-fresh-v9',
        'wrap-direct-corner-continuous-series020-v18r1',
        'wrap-direct-corner-continuous-series035-v18r1',
        'serial-moving-base-v6','serial-guide-reaction-calibration-v10r2',
        'created-force-sensor-readability-v25r1','pressure-model-damping-v21']]
    for name in ['remote-corner-cartesian080-series020-v23',
                 'index-wrap-pressure080-series-v8-repeat-v26',
                 'source2-pressure080-series-v8-repeat-v26',
                 'index-wrap-pressure080-series-v8-repeat-v26r3',
                 'source2-pressure080-series-v8-repeat-v26r3']:
        path=B/'measurement'/name
        if (R/path/'report.json').exists():paths.append(path)
    paths += [B/'comparison/source2-original-pressure080-v3',
              B/'comparison/index-wrap-v8-pressure080-v3',
              Path('research/wrap-force-20261004/events.jsonl'),
              Path('research/wrap-force-20261004/events-remote.jsonl'),
              B/'figures',B/'offline/frozen-v12-legal-export-v1',B/'offline/frozen-v12-replay-v1r1',B/'offline/frozen-v12-legal-action-export-v42',B/'offline/frozen-v12-recorded-issued-replay-v42',B/'remote']
    # Persist both successes and selected failures' actual command/source hashes.
    allowed={str(p) for p in paths}
    for folder in (R/B/'jobs').iterdir():
        identity=folder/'identity.json'
        if not identity.exists():continue
        command=json.loads(identity.read_text())['command']
        if '--output' in command and command[command.index('--output')+1] in allowed:
            paths.append(folder.relative_to(R))
    paths += [p.relative_to(R) for p in (R/B/'jobs').glob('source1-matched-direct-corner*')]
    paths += [B/'validation/boundary-assets-v35',B/'validation/thin-boundary-continuous-v35',B/'validation/thin-boundary-continuous-v36',B/'validation/axial-plus5-boundary-continuous-v36',B/'validation/axial-plus5-boundary-continuous-v38']
    paths += [p.relative_to(R) for p in (R/B/'jobs').glob('*boundary*')]
    paths += [B/'planning/source1-direct-corner-v33r1',B/'planning/source1-direct-corner-v33r2']
    paths += [B/'jobs/corner-thumb-head-only-v20',B/'jobs/corner-thumb-head-nominal-recovery-v21']
    for name in ['corner-thumb-head-only-v20','corner-thumb-head-nominal-recovery-v21','corner-functional-load-pilot-v13r1']:
        folder=R/B/'train'/name
        for f in folder.iterdir():
            if f.is_file() and f.suffix in {'.json','.jsonl','.yaml'}:paths.append(f.relative_to(R))
    packet=write_packet(a.output,'wrap-curated-evidence',paths)
    (a.output/'packet.json').write_text(json.dumps(packet,indent=2)+'\n');print(json.dumps(packet))


if __name__=='__main__':main()
