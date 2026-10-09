"""Saved legal input replay through the real network client and explicit offline endpoint."""
import isaacgym
import argparse
import json
from pathlib import Path
import numpy as np
from scripts.wuji_rear_controller import RearController,load_bundle,ROOT
from scripts.wuji_rear_network_backend import NetworkBackend
from scripts.wuji_rear_session import smooth


def main():
    p=argparse.ArgumentParser();p.add_argument('--field-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);field=json.loads(a.field_config.read_text());bundle=ROOT/field['bundle'];spec=load_bundle(bundle)
    b=NetworkBackend(field,bundle,a.output,motion=True,allow_replay=True)
    try:
        if b.header['evidence_scope']!='offline_contract_no_device':raise RuntimeError('This legal replay is ONLY for explicit offline protocol endpoints')
        c=RearController(spec);c.seed_issued(spec['open_q_rad'])
        trace=ROOT/'runs/rear-sim2real-20261009/final/nominal-video-v6/commands.jsonl';rows=[json.loads(l) for l in trace.read_text().splitlines()]
        differences=[];encoder_errors=[];issues=[];push=spec['release_seconds']+spec['settle_seconds']
        for i,row in enumerate(rows):
            q,telemetry=b.read();encoder_errors.append(float(np.max(abs(q-row['measured_q_rad']))));c.observe(q);t=row['time_s']
            if t<spec['prepare_seconds']:raw=c.propose_hold(np.array(spec['open_q_rad'])+smooth(t/spec['prepare_seconds'])*(np.array(spec['hold_target_rad'])-np.array(spec['open_q_rad'])))
            elif t<push:
                if t>=spec['release_seconds']+spec['prewarm_after_release_seconds'] and not c.taken:
                    c.takeover(q);b.read()  # Offline replay keeps this frame; refresh only packet timestamp after warmup.
                raw=c.propose_hold(spec['hold_target_rad'])
            else:raw=c.propose_push(q,t-push)
            sent,receipt=b.write(c.constrain(raw,b.lower,b.upper));c.commit(sent)
            error=float(np.max(abs(sent-row['issued_target_rad'])));differences.append(error)
            issues.append(dict(frame=i,error_rad=error,issued_target_rad=sent.tolist(),receipt_sequence=receipt['receipt']['sequence'],request_sha256=receipt['receipt']['request_sha256']))
        result=dict(frames=len(rows),maximum_sent_error_rad=max(differences),maximum_encoder_roundtrip_error_rad=max(encoder_errors),passed=max(differences)<2e-6 and max(encoder_errors)<1e-12,
            scope='Saved legal 380-frame encoder input through real SDK RPC, named permutations/sign/zero and accepted interface targets; not hardware/GDK processing or new contact physics',real_robot_ran=False,history_semantics=b.header['history_semantics'])
        (a.output/'RESULT.json').write_text(json.dumps(result,indent=2));(a.output/'commands.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in issues));print(json.dumps(result));assert result['passed']
    finally:b.close()

if __name__=='__main__':main()
