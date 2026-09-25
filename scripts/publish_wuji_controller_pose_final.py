"""Publish both complete pose-cost and controller-input pairs, including failures."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.publish_wuji_student_replay_results import read_trial

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'runs/wuji-goal'


def main():
    families = {
        'pose': dict(title='Wuji: complete pose-cost comparison', seed=64,
            arms=[('pose1', 'Pose cost 1', '#337fac', 'student-actorrl-smallcp25-pose1-noramp-seed64-v1',
                   'wuji_student_actorrl_smallcp25_pose1_noramp_seed64_v1'),
                  ('pose3', 'Pose cost 3', '#b58246', 'student-actorrl-smallcp25-pose3-noramp-seed64-v1',
                   'wuji_student_actorrl_smallcp25_pose3_noramp_seed64_v1')],
            note='Same historical quarter-noise CP25, seed64, new Adam1e-5, 5120 x32 x100. Both use full pose cost from start (ramp0).'),
        'controller': dict(title='Wuji: complete controller-input comparison', seed=65,
            arms=[('masked', 'Masked tracking input', '#337fac', 'student-controller-masked-smallcp25-seed65-v2',
                   'wuji_student_controller_masked_smallcp25_seed65_v2'),
                  ('tracking', 'Measured tracking error', '#488e67', 'student-controller-tracking-smallcp25-seed65-v2',
                   'wuji_student_controller_tracking_smallcp25_seed65_v2')],
            note='Same inherited CP25 and zero20-to16 residual, seed65, Adam1e-5, 5120 x32 x100. Pose1/ramp0. Only adapter input differs.')}
    cases = []
    for family, settings in families.items():
        for arm, _, _, prefix, run in settings['arms']:
            state = json.loads((ROOT/'runs'/run/'pipeline-status.json').read_text())
            assert state['status'] == 'completed' and state['stages'][-1]['returncode'] == 0, run
            assert state['spec']['epochs'] == 100
            for cp in [0, 1, 25, 50, 100]:
                for seconds in [2, 5]:
                    name = prefix+'-cp%d-mixed332-timed%dseconds' % (cp, seconds)
                    folder, report, trace = read_trial(name)
                    records = report['records']
                    # Pure pose stability excludes the first-cycle condition
                    # included in the legacy stable_full report field.
                    pose_ok = np.isfinite(trace['drift']) & np.isfinite(trace['rotation'])
                    pose_ok &= (trace['drift'] < .01) & (trace['rotation'] < .25)
                    body = pose_ok.all(axis=0) & np.array([r['alive_full'] for r in records])
                    cases.append(dict(family=family, arm=arm, cp=cp, seconds=seconds, name=name,
                        joint=[sum(r['stable_full_all_endpoints'] for r in records[i:i+100]) for i in [0,100,200,300]],
                        alive=[sum(r['alive_full'] for r in records[i:i+100]) for i in [0,100,200,300]],
                        pure_body_stable=[int(body[i:i+100].sum()) for i in [0,100,200,300]],
                        folder=folder, trace=trace))
    assert len(cases) == 40
    out = BASE/'release-student-controller-pose-final-20260922'
    out.mkdir(exist_ok=False)
    evidence = out/'evidence'
    evidence.mkdir()
    prefix = 'wuji-student-controller-pose-final-20260922'
    hashes = {}

    def copy(source, name):
        shutil.copy2(source, evidence/name)
        hashes[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()

    for case in cases:
        for p in case['folder'].iterdir():
            if p.is_file() and p.suffix in ['.json', '.yaml', '.py']:
                copy(p, case['name']+'-'+p.name)
        np.savez_compressed(evidence/(case['name']+'-metric-trace.npz'), **case['trace'])
    for settings in families.values():
        for _, _, _, _, run in settings['arms']:
            copy(ROOT/'runs'/run/'pipeline-status.json', run+'-pipeline-status.json')
    for name in ['student-actorrl-pose-pair-seed64-proposal.json',
                 'student-controller-cp0-preserving-seed65-proposal.json',
                 'student-controller-cp0-preserving-seed65-v2-proposal.json',
                 'diagnostics/actor-noise-drift-20260922T1710.json']:
        copy(BASE/name, name.replace('/', '-'))
    for version in ['1652-v1', '1655-v2']:
        folder = BASE/('diagnostics/controller-actor-runtime-'+version)
        for p in folder.rglob('*.json'):
            copy(p, 'controller-runtime-'+version+'-'+str(p.relative_to(folder)).replace('/', '-'))
    for name in ['scripts/publish_wuji_controller_pose_final.py',
                 'scripts/publish_wuji_student_replay_results.py',
                 'scripts/wuji_timed_command_metrics.py',
                 'scripts/analyze_wuji_actor_noise_drift.py']:
        copy(ROOT/name, Path(name).name)
    for family, settings in families.items():
        fig, axes = plt.subplots(2, 3, figsize=(12, 7.4))
        for row, seconds in enumerate([2, 5]):
            for col, grasp in enumerate(['Original grasp', 'Training row16', 'Training row15']):
                ax = axes[row, col]
                for arm, label, color, _, _ in settings['arms']:
                    selected = [c for c in cases if c['family']==family and c['arm']==arm and c['seconds']==seconds]
                    ax.plot([c['cp'] for c in selected], [c['joint'][col] for c in selected],
                            'o-', label=label, color=color, markersize=4)
                ax.set(title=grasp+' / %d s commands'%seconds, xlabel='PPO epochs',
                       ylabel='20 s joint success /100', ylim=(-2, 103), xticks=[0,25,50,100])
                ax.grid(alpha=.2)
                ax.spines[['top', 'right']].set_visible(False)
        handles, labels = axes[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5,.96), ncol=2, frameon=False)
        fig.suptitle(settings['title'])
        fig.text(.02, .015, settings['note']+'\nFrozen student encoder and observation statistics. Strict tails <2mm for0.3s, body <10mm /0.25rad throughout.\nReused332 development states: three training grasps x100 and fourth held-out grasp x32. Failures retained; no hardware claim.', fontsize=8)
        fig.tight_layout(rect=[0,.1,1,.9])
        fig.savefig(out/(prefix+'-'+family+'.png'), dpi=170)
        plt.close(fig)
    records = [{k:v for k,v in c.items() if k not in ['folder','trace']} for c in cases]
    provenance = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        reports=40, all_records_rescored_exact=True, cases=records, source_sha256=hashes,
        body_semantics='pure_body_stable is all-step finite pose bounds AND alive_full; unlike legacy stable_full it has no first_cycle condition.')
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance, indent=2)+'\n')
    lines = ['# 完整稳定性与控制输入对照', '',
        '四组均完成100轮且正常退出；40份固定CP评估均从原trace逐条重算。每组5120×32×100，冻结student编码器和观测normalizer。所有失败保留。', '',
        '|组别|CP0 快/慢|CP100 快/慢|', '|---|---:|---:|']
    for family, settings in families.items():
        for arm, label, _, _, _ in settings['arms']:
            values=[]
            for cp in [0,100]:
                values.append('/'.join(str(sum(next(c for c in cases if c['family']==family and c['arm']==arm and c['cp']==cp and c['seconds']==sec)['joint'][:3])) for sec in [2,5]))
            lines.append('|'+label+'|'+'|'.join(values)+'|')
    lines += ['', '分母各300，另32个未训练第四抓姿逐项见provenance。初态均为既有开发集，不能称新盲测。联合成功要求每条指令末0.3秒持续<2mm，刀身全程<10mm/.25rad且存活；附纯刀身稳定分解，它不混入旧stable_full字段中的首次循环条件。', '',
        '稳定性配对同seed64、同历史小噪声CP25、新Adam1e-5，组内系数1/3不同；两组都取消旧50轮ramp，因此与旧实验的差异不能只归因权重。控制输入配对同seed65、相同初始策略和零初始化20→16残差，只改变adapter输入为零或(已发目标−实测角度)/0.1rad、裁剪[-5,5]。两者bias都训练；处理组weights学习，对照weights保持零。Actor不读取当前物体/接触/力矩真值。两类配对不是同一seed的四臂对照。', '',
        '控制V1两个独立PhysX轨迹哈希不等，正式训练未启动；V2在同物理状态/输入/入站RNN里分别19200次模式比较完全一致，仍保存跨进程不等的证据。两组真实3轮PPO预检各491520转移，冻结、有限性、实际学习率、精确同策略KL与adapter更新检查通过。', '',
        '小噪声宽0和pose1最终标准差相对CP1逐项变化不到0.5%，不支持噪声幅度回涨的解释；它不能排除探索分布的作用。训练回报与端点的冻结诊断另列，不混入本包的固定时钟成功率。全部属于Wuji迁移研究，未声明可靠部署、未见几何或真机成功。']
    (out/(prefix+'-README.md')).write_text('\n'.join(lines)+'\n')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()):
            z.write(p, p.name)
    files = sorted(p for p in out.iterdir() if p.is_file())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out), reports=40, assets=len(files)+1)))


if __name__ == '__main__':
    main()
