"""Archive all fixed-budget replay controls, including their final regressions."""
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
BASE = ROOT/'runs/wuji-goal'


def main():
    prefix = 'wuji-student-replay-final-20260922'
    out = BASE/'release-student-replay-final-20260922'
    assert not out.exists()
    cases, statuses = [], []
    for arm, version in [('current', 'v2'), ('currenttwice', 'v1'), ('replay', 'v2')]:
        name = 'wuji_student_bridge3cp25_pure250_then_%s500_seed60_%s' % (arm, version)
        p = ROOT/'runs'/name/'pipeline-status.json'
        status = json.loads(p.read_text())
        assert status['status'] == 'completed' and status['stages'][-1]['returncode'] == 0
        statuses.append((name, p))
        for cp in [25, 100, 250, 500]:
            for seconds in [2, 5]:
                name = 'student-bridge3-pure250-%s500-seed60-%s-cp%d-mixed332-timed%dseconds' % (arm, version, cp, seconds)
                folder, report, trace = read_trial(name)
                joint = [sum(x['stable_full_all_endpoints'] for x in report['records'][i:i+100]) for i in [0,100,200,300]]
                alive = [sum(x['alive_full'] for x in report['records'][i:i+100]) for i in [0,100,200,300]]
                cases.append(dict(name=name, arm=arm, cp=cp, seconds=seconds, joint=joint, alive=alive,
                                  folder=folder, trace=trace))
    evidence = out/'evidence'
    evidence.mkdir(parents=True)
    sources = {}

    def copy(source, name):
        shutil.copy2(source, evidence/name)
        sources[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()

    for name, path in statuses:
        copy(path, name+'-pipeline-status.json')
    for case in cases:
        for name in ['report.json', 'status.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            copy(case['folder']/name, case['name']+'-'+name)
        np.savez_compressed(evidence/(case['name']+'-metric-trace.npz'), **case['trace'])
    for name in ['student-replay-pair-seed60-proposal.json', 'student-replay-currenttwice-seed60-proposal.json']:
        copy(BASE/name, name)
    copy(Path(__file__), 'publisher_source.py')
    copy(ROOT/'scripts/publish_wuji_student_replay_results.py', 'reader_source.py')
    copy(ROOT/'scripts/wuji_timed_command_metrics.py', 'metrics_source.py')
    colors = dict(current='#777777', currenttwice='#d27e24', replay='#2474a4')
    labels = dict(current='Current batch', currenttwice='Second current pass', replay='Historical batch')
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for row, seconds in enumerate([2,5]):
        for col, grasp in enumerate(['Original grasp', 'Training row16', 'Training row15']):
            ax = axes[row,col]
            for arm in colors:
                group = [x for x in cases if x['arm']==arm and x['seconds']==seconds]
                ax.plot([x['cp'] for x in group], [x['joint'][col] for x in group], 'o-',
                        color=colors[arm], label=labels[arm], markersize=4)
            ax.set(title=grasp+' / %d s commands'%seconds, xlabel='Updates after frozen ordinary-student CP250',
                   ylabel='20 s joint success / 100', xlim=(10,515), ylim=(-2,103), xticks=[25,100,250,500])
            ax.grid(alpha=.2)
            ax.spines[['top','right']].set_visible(False)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Completed 500-update student controls: early replay gains do not persist')
    fig.text(.02,.015,'All three declared budgets completed. Same initial checkpoint, seed60, Adam2e-4, 1024 environments x16 steps/update.\nHistorical and second-current arms match extra encoder-pass counts; single seed and differing GPU scheduling remain limitations.\nEvery command tail <2 mm for0.3 s, body drift <10 mm / angle <0.25 rad, alive. Reused development states; held-out grasp0/32 throughout.',fontsize=8)
    fig.tight_layout(rect=[0,.08,1,.95])
    fig.savefig(out/(prefix+'-checkpoint-comparison.png'), dpi=170)
    plt.close(fig)
    provenance = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      completed_budgets=True, updates_each=500, physical_transitions_each=8192000,
                      all_24_reports_rescored_exact=True, source_sha256=sources,
                      cases=[{k:v for k,v in x.items() if k not in ['folder','trace']} for x in cases])
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance, indent=2)+'\n')
    (out/(prefix+'-README.md')).write_text('''# 三组 student 500 更新最终对照

三组均已正常完成500更新，各8,192,000物理转移；24份固定CP25/100/250/500、快速2秒/慢速5秒指令的报告已从trace逐条重算一致。每次执行20秒，三个训练抓姿各100个已有扰动，另32个未训练第四抓姿。它们都是开发集，不是新增盲测。

最终CP500快速/慢速联合：当前batch86/59，第二次当前batch94/127，历史batch78/116（分母各300）。历史CP25曾达153/222，但早期峰值未保留到最后；最终也没有稳定胜过相同额外训练量的当前batch对照。三组均不满足可靠开合要求，未训练第四抓姿均0/32。不能用训练latent MSE降低来宣称操作成功。

相同普通student CP250起点、teacher CP25、seed60、新Adam2e-4、1024环境×16步。历史组半数当前/半数历史MSE，FIFO655360；第二次当前组写入、采样相同FIFO并保留额外encoder训练量，但额外监督仍来自当前batch。两组额外dropout使用私有随机流。第二次当前是在看到早期结果后追加，运行设备/调度不同，保留单seed限制。当前batch组计算量较少。

之前的无字学生视频保留在同Release的wuji-student-replay-controls-20260922-learned-cp25-three-grasps-no-text.mp4；本包补齐最终预算，不把旧视频当作最终CP500表现。证据ZIP包含所有记录、失败、评分轨迹、实际退出码和协议。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(evidence.iterdir()):
            archive.write(path, path.name)
    files = [p for p in out.iterdir() if p.is_file()]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(files))+'\n')
    print(json.dumps(dict(assets=len(files)+1, reports=len(cases), output=str(out))))


if __name__ == '__main__':
    main()
