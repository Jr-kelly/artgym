"""Rescore all twenty custom-TCN paired evaluations and preserve the complete evidence."""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.analyze_wuji_state_encoder_evaluations import analyze

ROOT = Path(__file__).resolve().parents[1]
ARMS = ['provided', 'masked']
CLOCKS = [2, 5]
UPDATES = [0, 250, 1000]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run, source, out = args.run.resolve(), args.source_run.resolve(), args.output.resolve()
    assert not out.exists()
    status = json.loads((run/'status.json').read_text())
    assert status['status'] == 'completed' and status['all_initial_paired_traces_exact']
    assert all(s['status'] == 'completed' and s['returncode'] == 0 for s in status['stages'])
    fitting = json.loads((source/'fitting/status.json').read_text())
    assert fitting['status'] == 'completed' and fitting['updates_completed'] == 1000
    expected = {f'gate-{a}-cp{u}-runtime3-{s}s' for a in ARMS for u in [0, 1000] for s in CLOCKS}
    expected |= {f'formal-{a}-cp{u}-mixed332-{s}s' for a in ARMS for u in UPDATES for s in CLOCKS}
    assert {p.parent.name for p in run.glob('*/state-estimation-audit.json')} == expected
    rows = [analyze(run/name) for name in sorted(expected)]
    for name in expected:
        audit = json.loads((run/name/'state-estimation-audit.json').read_text())
        assert audit['state_encoder_backend'] == 'custom_tcn'
        assert audit['checks']['command_update_rows'] == audit['checks']['physics_transitions']
        if name.startswith('gate'):
            assert audit['checks']['privileged_invariance'] == 1800
    initial_comparisons = []
    for prefix, batch in [('gate', 'runtime3'), ('formal', 'mixed332')]:
        for seconds in CLOCKS:
            paths = [run/f'{prefix}-{a}-cp0-{batch}-{seconds}s' for a in ARMS]
            for name in ['trace.npz', 'estimation-trace.npz']:
                with np.load(paths[0]/name) as a, np.load(paths[1]/name) as b:
                    assert a.files == b.files
                    for key in a.files:
                        assert np.array_equal(a[key], b[key]), (prefix, seconds, name, key)
                    initial_comparisons.append(dict(prefix=prefix, seconds=seconds, file=name, exact=True, fields=a.files))
    curves = {a:{} for a in ARMS}
    by_name = {Path(r['folder']).name:r for r in rows}
    for a in ARMS:
        for s in CLOCKS:
            curves[a][str(s)] = []
            for u in UPDATES:
                r = by_name[f'formal-{a}-cp{u}-mixed332-{s}s']
                curves[a][str(s)].append(dict(update=u, joint=sum(g['joint'] for g in r['groups'][:3]),
                    body=sum(g['body'] for g in r['groups'][:3]), alive=sum(g['alive'] for g in r['groups'][:3]),
                    groups=[g['joint'] for g in r['groups']], fourth=r['groups'][3]['joint']))
    out.mkdir(parents=True)
    prefix = 'wuji-command-input-final-20260923'
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        rows=rows, curves=curves, all20_reports_rescored=True,
        cp0_paired_full_traces_exact=initial_comparisons,
        formal_physics_transitions=sum(r['actual_transitions'] for r in rows if r['num_envs'] == 332),
        runtime_physics_transitions=sum(r['actual_transitions'] for r in rows if r['num_envs'] == 3),
        fitting=fitting, validation=json.loads((source/'fitting/validation.json').read_text()),
        source_fitting_run=str(source), backend='custom_tcn', same_gpu=True,
        scope='Exact copied weights, new numerical baseline. Three training grasps x100 perturbations plus fourth32, previously observed development set including fitting rows. No independent validation or hardware claim.')
    (out/(prefix+'-results.json')).write_text(json.dumps(result, indent=2)+'\n')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, s in zip(axes, CLOCKS):
        for a, color, marker in [('provided', '#337d9e', 'o'), ('masked', '#b67c41', 's')]:
            y = [r['joint'] for r in curves[a][str(s)]]
            ax.plot(UPDATES, y, marker=marker, color=color, label=a)
            for x, v in zip(UPDATES, y):
                ax.annotate(str(v), (x, v), xytext=(0, 8 if a == 'provided' else -14),
                    textcoords='offset points', ha='center', fontsize=8)
        ax.set(xticks=UPDATES, ylim=(0, 315), xlabel='Supervised updates',
            ylabel='Strict successes /300', title=f'{s} s commands')
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend()
    fig.suptitle('Own commanded targets: all frozen checkpoints')
    fig.text(.02, .02, 'Same network, initial tensors, data and 512,000 labels/arm; only slider position is corrected.\n'
        'Custom TCN with copied weights; same GPU. Reused development states; fourth grasp reported separately.', fontsize=8)
    fig.tight_layout(rect=[0, .11, 1, .94])
    fig.savefig(out/(prefix+'-comparison.png'), dpi=160)
    plt.close(fig)
    table = ['|模型|CP|快速 /300|慢速 /300|第四抓姿 快/慢 /32|', '|---|---:|---:|---:|---:|']
    for a in ARMS:
        for i, u in enumerate(UPDATES):
            fast, slow = curves[a]['2'][i], curves[a]['5'][i]
            table.append(f"|{a}|{u}|{fast['joint']}|{slow['joint']}|{fast['fourth']}/{slow['fourth']}|")
    (out/(prefix+'-README.md')).write_text('''# 已发关节目标输入配对完整结果

'''+'\n'.join(table)+'''

两组同148→128→64→1网络、初始残差张量、固定四来源数据与批次、1000次Adam2e-4更新。每组512000监督样本，拟合无新物理。原TCN、teacher、刀身六维和滑块速度保持，只修正滑块位置。后20维为本次动作之前程序已发关节目标，provided提供、masked在标准化后清零。当前物体/接触真值只用于训练标签与评分，推理不读取。

正式使用V3的同六个checkpoint，原生确定性Conv1d出现严重性能问题后，将相同权重逐项复制到已有custom TCN；没有重新拟合。算术顺序变化，单独建立CP0数值基线，不用旧168/51代替。所有20报告包括八项运行检查和十二项正式评估，均逐条从原物理trace重算；快慢两种节奏的CP0两组完整物理、动作、估计和已发目标轨迹在同一GPU独立进程间逐元素一致，不宣称跨GPU或原生实现位级一致。

数据为已观察开发集，三训练抓姿各100扰动加第四抓姿32；包含拟合初态。严格标准为20秒每条命令末0.3秒误差小于2mm、刀身全程位移小于10mm/转角小于0.25rad且存活。离线误差、短运行检查、中期峰值均不构成可靠独立控制或真机成功。全部结果与失败保留。

V1数值分歧、V2动作前配置检查失败、V3性能主动停止均有独立公开证据。原数据zip和V3拟合权重包已经另行发布；本包保留所有六个被正式评估的权重、指标重算轨迹、估计轨迹和源码。结果json记录完整原trace的SHA256。
''')
    pin = Path(json.loads((run/'launcher.json').read_text())['pin'])
    # Local publication may not have the remote pin path. The checked source
    # archive contains the exact executed files and is always included below.
    source_history = ROOT/'runs/wuji-goal/source-history'
    pinned = source_history/'pinned-command-backend-source-20260923T0011-v4.tar.gz'
    assert digest(pinned) == 'c633b50835cd8e94070cd8dafdfa2b12a7e9e53f4f1192dde6e5ec5fd084b54e'
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for r in rows:
            p = Path(r['folder'])
            for f in sorted(p.iterdir()):
                if f.is_file() and (f.suffix in ['.json', '.yaml', '.py'] or f.name == 'estimation-trace.npz'):
                    archive.write(f, p.name+'/'+f.name)
            with np.load(p/'trace.npz') as z:
                values = {k:z[k] for k in ['active', 'fall', 'invalid', 'slider', 'goal', 'drift', 'rotation']}
            stream = io.BytesIO()
            np.savez_compressed(stream, **values)
            archive.writestr(p.name+'/metric-trace.npz', stream.getvalue())
        for a in ARMS:
            for u in UPDATES:
                p = source/'fitting'/f'{a}-update{u:04d}.pth'
                assert digest(p) == status['spec']['artifact_sha256'][p.name]
                archive.write(p, 'artifacts/'+p.name)
                archive.write(p.with_suffix('.json'), 'artifacts/'+p.with_suffix('.json').name)
        for p in sorted(run.glob('*.json')):
            archive.write(p, 'pipeline/'+p.name)
        for p in [source/'fitting/status.json', source/'fitting/validation.json']:
            archive.write(p, 'fitting/'+p.name)
        for p in [Path(__file__), ROOT/'scripts/analyze_wuji_state_encoder_evaluations.py',
                  ROOT/'scripts/wuji_timed_command_metrics.py', pinned]:
            archive.write(p, 'source/'+p.name)
    files = sorted(out.iterdir())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(digest(p)+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out), curves=curves, reports=len(rows),
        files=[(p.name, p.stat().st_size) for p in out.iterdir()])))


if __name__ == '__main__':
    main()
