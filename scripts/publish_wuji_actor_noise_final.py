"""Package complete actor noise/reward budgets and complete student budgets.

Requires all fixed checkpoints; never substitute a peak for a final result.
Existing output is immutable. Run after the four actor arms finish evaluation.
"""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.publish_wuji_student_replay_results import read_trial

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'runs/wuji-goal'


def main():
    arms = {
        'original0': ('Original std / broad0', '#777777', 'student-actorrl-replaycp25-seed62-v2'),
        'original5': ('Original std / broad5', '#b4824b', 'student-actorrl-replaycp25-broad5-seed62-v2'),
        'quarter0': ('Quarter std / broad0', '#267fa5', 'student-actorrl-replaycp25-sigmaquarter-broad0-seed62-v1'),
        'quarter5': ('Quarter std / broad5', '#539a70', 'student-actorrl-replaycp25-sigmaquarter-broad5-seed62-v1'),
    }
    cases = []
    completed_runs = [
        'wuji_student_actorrl_replaycp25_seed62_v2',
        'wuji_student_actorrl_replaycp25_broad5_seed62_v2',
        'wuji_student_actorrl_replaycp25_sigmaquarter_broad0_seed62_v1',
        'wuji_student_actorrl_replaycp25_sigmaquarter_broad5_seed62_v1',
        'wuji_student_bridge3cp25_pure1000_seed57_v1',
        'wuji_student_bridge3cp25_controller1000_seed57_v1',
    ]
    for run in completed_runs:
        status = json.loads((ROOT/'runs'/run/'pipeline-status.json').read_text())
        assert status['status'] == 'completed', run
        assert status['stages'][-1]['status'] == 'completed' and status['stages'][-1]['returncode'] == 0, run
    for arm, (_, _, prefix) in arms.items():
        for cp in [0, 1, 25, 50, 100]:
            for seconds in [2, 5]:
                base = prefix[:-3] if arm == 'original0' and cp == 0 else prefix
                cases.append(dict(kind='actor', arm=arm, cp=cp, seconds=seconds,
                                  name='%s-cp%d-mixed332-timed%dseconds' % (base, cp, seconds)))
    for arm in ['pure', 'controller']:
        for cp in [100, 250, 500, 1000]:
            for seconds in [2, 5]:
                cases.append(dict(kind='distill', arm=arm, cp=cp, seconds=seconds,
                    name='student-bridge3cp25-%s1000-seed57-cp%d-mixed332-timed%dseconds' % (arm, cp, seconds)))
    # Read and independently rescore every report before creating publication.
    for case in cases:
        folder, report, trace = read_trial(case['name'])
        case.update(folder=folder, report=report, trace=trace,
                    joint=[sum(x['stable_full_all_endpoints'] for x in report['records'][i:i+100]) for i in [0,100,200,300]],
                    alive=[sum(x['alive_full'] for x in report['records'][i:i+100]) for i in [0,100,200,300]])
    out = BASE / 'release-student-actor-noise-final-20260922'
    assert not out.exists()
    evidence = out / 'evidence'
    evidence.mkdir(parents=True)
    prefix = 'wuji-student-actor-noise-final-20260922'
    sources = {}

    def copy(source, name):
        shutil.copy2(source, evidence / name)
        sources[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()

    for run in completed_runs:
        copy(ROOT/'runs'/run/'pipeline-status.json', run+'-pipeline-status.json')

    for case in cases:
        for filename in ['report.json', 'status.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            copy(case['folder'] / filename, case['name'] + '-' + filename)
        np.savez_compressed(evidence / (case['name'] + '-metric-trace.npz'), **case['trace'])
    for kind in ['actor', 'distill']:
        fig, axes = plt.subplots(2, 3, figsize=(13, 8))
        selected_arms = arms if kind == 'actor' else {
            'pure': ('Original student inputs', '#267fa5', ''),
            'controller': ('With current controller state', '#b4824b', '')}
        for row, seconds in enumerate([2, 5]):
            for col, grasp in enumerate(['Original grasp', 'Training row16', 'Training row15']):
                ax = axes[row, col]
                for arm, (label, color, _) in selected_arms.items():
                    selected = [c for c in cases if c['kind'] == kind and c['arm'] == arm and c['seconds'] == seconds]
                    ax.plot([c['cp'] for c in selected], [c['joint'][col] for c in selected], 'o-',
                            color=color, label=label, markersize=4)
                ax.set(title=grasp + ' / %d s commands' % seconds,
                       xlabel='PPO epochs' if kind == 'actor' else 'Student updates',
                       ylabel='20 s joint success / 100', ylim=(-2, 103),
                       xticks=[0, 25, 50, 100] if kind == 'actor' else [100, 250, 500, 1000])
                ax.grid(alpha=.2)
                ax.spines[['top', 'right']].set_visible(False)
        axes[0,0].legend(fontsize=8)
        fig.suptitle('Wuji: complete actor noise / reward comparison' if kind == 'actor'
                     else 'Wuji: complete ordinary / controller-input distillation comparison')
        footnote = ('Actor: same initialization except initial logstd, seed62, Adam1e-5, 5120 x32 x100; frozen replayCP25 encoder and observation normalizer.'
                    if kind == 'actor' else 'Distillation: 1024 x16 x1000, seed57, Adam2e-4, latent MSE on student-driven trajectories. Input dimension also changes initialization.')
        fig.text(.02,.014,footnote + '\nReused332 development states; three trained grasps x100 perturbations and fourth held-out grasp x32. Independent PhysX processes can differ.\nEvery command tail <2 mm for0.3 s; full body drift <10 mm / angle <0.25 rad, alive. All failures retained; no hardware or unseen-geometry claim.', fontsize=8)
        fig.tight_layout(rect=[0,.095,1,.95])
        fig.savefig(out / (prefix + '-' + kind + '-curves.png'), dpi=170)
        plt.close(fig)
    for source in [Path(__file__), ROOT/'scripts/publish_wuji_student_replay_results.py',
                   ROOT/'scripts/wuji_timed_command_metrics.py']:
        copy(source, source.name)
    for filename in ['student-actorrl-sigmaquarter-seed62-proposal.json',
                     'student-actorrl-broad5-seed62-v2-proposal.json']:
        copy(BASE/filename, filename)
    records = [{k:v for k,v in c.items() if k not in ['folder','report','trace']} for c in cases]
    provenance = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      reports=len(records), all_records_rescored_exact=True, cases=records,
                      source_sha256=sources, denominator='Three trained grasps x100 and fourth held-out grasp x32; reused development.')
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    table = ['|实验|最终快速/300|最终慢速/300|', '|---|---:|---:|']
    for kind, selected in [('actor', arms), ('distill', {'pure':('普通蒸馏',), 'controller':('含控制器状态蒸馏',)})]:
        for arm, label in selected.items():
            counts = [sum(next(c for c in cases if c['kind']==kind and c['arm']==arm and c['cp']==(100 if kind=='actor' else 1000) and c['seconds']==seconds)['joint'][:3]) for seconds in [2,5]]
            table.append('|%s|%d|%d|' % (label[0], *counts))
    (out/(prefix+'-README.md')).write_text('''# Wuji完整预算：策略噪声/奖励与学生输入对照

全部56项固定检查点评估从trace重新评分，未用早期峰值替代最终结果。Actor四组为同冻结replayCP25编码器、原teacher均值权重和观测归一化、seed62、新Adam1e-5、5120环境×32步×100轮；只比较初始化std原值/四分之一、额外10mm宽奖励系数0/5。保留原2mm奖励及严格成功标准，sigma继续学习。实验是在先前结果基础上依次提出，GPU调度和独立PhysX进程存在差异，各CP0也可能有小幅差值，不能声称全部差异具有单seed因果确定性。

普通/控制器输入蒸馏另为1024×16×1000、Adam2e-4、seed57、全student闭环latentMSE，冻结teacher actor。增加21维当前关节目标/命令同时改变网络初始化，属于另一个实验族；两类曲线不作等预算横向比较。

''' + '\n'.join(table) + '''

统一使用已经反复检查的332开发初态：三个训练抓姿各100扰动与未训练第四抓姿32个。联合成功要求20秒内每次指令末0.3秒误差<2mm、刀身全程漂移<10mm/旋转<0.25rad且不掉落。全部第四抓姿结果在provenance中保留，不增加盲测分母。

初始噪声缩小不等于新学习；本包明确分开CP0和训练CP。低学习率和关闭跨组混用的后续实验有单独预算，不纳入此四组最终比较。SAPG聚合KL含跨探索组差异，不能直接据其推断优化器更新幅度；零学习率诊断和更正另存。当前仅仿真，物理参数未实物标定，不宣称可靠真机部署。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(evidence.iterdir()):
            archive.write(source, source.name)
    files = [p for p in out.iterdir() if p.is_file()]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(files))+'\n')
    print(json.dumps(dict(output=str(out), reports=len(cases), assets=len(files)+1)))


if __name__ == '__main__':
    main()
