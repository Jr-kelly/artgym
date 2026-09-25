"""Rescore and package every gate and frozen checkpoint of the command-input pair."""
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
ARMS = ('provided', 'masked')
CLOCKS = (2, 5)
UPDATES = (0, 250, 1000)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fit-audit', type=Path, required=True)
    args = parser.parse_args()
    run, out = args.run.resolve(), args.output.resolve()
    assert not out.exists()
    status = json.loads((run/'status.json').read_text())
    assert status['status'] == 'completed' and status['zero_residual_cross_gpu_traces_exact']
    assert all(s['status'] == 'completed' and s['returncode'] == 0 for s in status['stages'])
    fit = json.loads((run/'fitting/status.json').read_text())
    fit_audit = json.loads(args.fit_audit.read_text())
    assert fit['status'] == 'completed' and fit['updates_completed'] == 1000
    assert fit['samples_each'] == 512000 and fit['same_initial_tensors']
    assert fit_audit['status'] == 'passed' and fit_audit['formal_fit_audited']
    expected = {f'gate-{a}-cp{u}-runtime3-{s}s' for a in ARMS for u in (0, 2) for s in CLOCKS}
    expected |= {f'formal-{a}-cp{u}-mixed332-{s}s' for a in ARMS for u in UPDATES for s in CLOCKS}
    expected |= {f'formal-{a}-cp1000-runtime3-{s}s' for a in ARMS for s in CLOCKS}
    assert {p.parent.name for p in run.glob('*/state-estimation-audit.json')} == expected
    rows = [analyze(run/name) for name in sorted(expected)]
    exact = []
    protocols = []
    for row in rows:
        folder = Path(row['folder'])
        audit = json.loads((folder/'state-estimation-audit.json').read_text())
        assert audit['checks']['command_update_rows'] == row['actual_transitions']
        protocols.append(audit['numerical_protocol'])
    assert all(p == protocols[0] for p in protocols)
    assert protocols[0] == dict(cublas_workspace=':4096:8', deterministic_algorithms=True,
        cudnn_benchmark=False, cudnn_deterministic=True, cudnn_tf32=False, matmul_tf32=False)
    # Compare all original fields, including actions and issued command targets.
    # Gate and formal batches can differ numerically; the paired arms within
    # each batch must agree exactly at the zero-residual initialization.
    for prefix, batch in [('gate', 'runtime3'), ('formal', 'mixed332')]:
        for seconds in CLOCKS:
            paths = [run/f'{prefix}-{a}-cp0-{batch}-{seconds}s' for a in ARMS]
            for name in ('trace.npz', 'estimation-trace.npz'):
                with np.load(paths[0]/name) as a, np.load(paths[1]/name) as b:
                    assert a.files == b.files
                    for key in a.files:
                        assert np.array_equal(a[key], b[key]), (prefix, seconds, name, key)
                    exact.append(dict(prefix=prefix, seconds=seconds, file=name, fields=a.files, exact=True))
    by_name = {Path(row['folder']).name: row for row in rows}
    curves = {}
    for arm in ARMS:
        curves[arm] = {}
        for seconds in CLOCKS:
            selected = [by_name[f'formal-{arm}-cp{u}-mixed332-{seconds}s'] for u in UPDATES]
            curves[arm][str(seconds)] = [dict(update=r['update'],
                joint=sum(g['joint'] for g in r['groups'][:3]),
                body=sum(g['body'] for g in r['groups'][:3]),
                groups=[g['joint'] for g in r['groups']],
                fourth_grasp=r['groups'][3]['joint']) for r in selected]
    out.mkdir(parents=True)
    prefix = 'wuji-command-slider-final-20260922'
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        all_reports_rescored=True, reports=len(rows), rows=rows, curves=curves, fitting=fit,
        validation=json.loads((run/'fitting/validation.json').read_text()),
        fit_audit=fit_audit, exact_cp0_comparisons=exact, numerical_protocol=protocols[0],
        physics_transitions=sum(r['actual_transitions'] for r in rows),
        scope='Same-network, fixed-data, slider-position-only comparison. Existing development states include fitting rows. No independent validation or hardware claim.')
    (out/(prefix+'-results.json')).write_text(json.dumps(result, indent=2)+'\n')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, seconds in zip(axes, CLOCKS):
        for arm, color, marker in [('provided', '#337d9e', 'o'), ('masked', '#b67c41', 's')]:
            values = [r['joint'] for r in curves[arm][str(seconds)]]
            ax.plot(UPDATES, values, color=color, marker=marker, label=arm)
            for x, y in zip(UPDATES, values):
                ax.annotate(str(y), (x, y), xytext=(0, 7 if arm == 'provided' else -13),
                    textcoords='offset points', ha='center', fontsize=8)
        ax.set(xticks=UPDATES, ylim=(0, 310), xlabel='Supervised updates',
            ylabel='Strict successes /300', title=f'{seconds} s commands')
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend()
    fig.suptitle('Own commanded targets: complete paired frozen evaluations')
    fig.text(.02, .02, 'Same initial tensors and 512,000 labels per arm; only slider position is corrected.\n'
        'Three training grasps x100 perturbations; fourth grasp reported separately. Reused development states.', fontsize=8)
    fig.tight_layout(rect=[0, .11, 1, .94])
    fig.savefig(out/(prefix+'-comparison.png'), dpi=160)
    plt.close(fig)
    table = ['|模型与更新|快速 /300|慢速 /300|第四抓姿 快/慢 /32|', '|---|---:|---:|---:|']
    for arm in ARMS:
        for i, update in enumerate(UPDATES):
            fast, slow = curves[arm]['2'][i], curves[arm]['5'][i]
            table.append(f"|{arm} CP{update}|{fast['joint']}|{slow['joint']}|{fast['fourth_grasp']}/{slow['fourth_grasp']}|")
    readme = '''# 已发关节目标输入配对：全部冻结评估

''' + '\n'.join(table) + '''

两组使用同一148→128→64→1残差网络、完全相同初始张量、同一训练批次和1000次Adam2e-4更新。原TCN、刀身六维、滑块速度和teacher冻结，只修正滑块位置。前128维为已有因果关节/动作、初始字段、TCN预测和URDF几何特征；后20维为本次动作发出之前控制程序已发的关节目标。provided提供这20维，masked在标准化后清零。推理不读取当前物体或接触真值。

训练使用已有teacher/student快慢四套轨迹，每源60训练初态与30留出初态，共36000训练标签、18000验证标签。每次batch512、每源128，每组512000监督样本；拟合阶段没有新物理采样。两次更新的预检与正式1000次拟合各自从相同原始权重开始。

24份报告包含8次预检、12次正式332初态评估和4次最终运行检查，全部从物理trace重算。相同批量的CP0在两GPU上，快慢时钟完整动作、物理、状态预测和已发目标逐元素一致。全组采用确定性cuDNN/CUBLAS及关闭TF32的推理设置；旧版168/51结果属于不同数值设置，不能替代这里的CP0基线。

332初态为三训练抓姿各100扰动加未训练第四抓姿32；这是包含拟合初态的开发集。严格标准为20秒每条指令末0.3秒保持2mm内、刀身全程10mm/0.25rad内且存活有限。离线RMSE和开发成功率都不代表独立泛化或真机验证。

此前V1的跨GPU数值分歧、V2被Runner重置cuDNN设置而在动作前失败，分别有独立公开证据；本包不改写失败历史。metric-trace可重算成功指标，完整trace原文件SHA256载于results；estimation-trace保留完整估计与控制器目标。
'''
    (out/(prefix+'-README.md')).write_text(readme)
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            p = Path(row['folder'])
            for f in sorted(p.iterdir()):
                if f.is_file() and (f.suffix in ('.json', '.yaml') or f.name == 'estimation-trace.npz'):
                    archive.write(f, p.name+'/'+f.name)
            with np.load(p/'trace.npz') as z:
                values = {k:z[k] for k in ('active', 'fall', 'invalid', 'slider', 'goal', 'drift', 'rotation')}
            stream = io.BytesIO()
            np.savez_compressed(stream, **values)
            archive.writestr(p.name+'/metric-trace.npz', stream.getvalue())
        for folder, updates in [('preflight', (0, 2)), ('fitting', UPDATES)]:
            for arm in ARMS:
                for update in updates:
                    p = run/folder/f'{arm}-update{update:04d}.pth'
                    assert digest(p) == json.loads(p.with_suffix('.json').read_text())['sha256']
                    archive.write(p, str(p.relative_to(run)))
                    archive.write(p.with_suffix('.json'), str(p.with_suffix('.json').relative_to(run)))
        for pattern in ('*.json', '*.log', 'preflight/*.json', 'fitting/*.json', 'data/*'):
            for p in sorted(run.glob(pattern)):
                if p.is_file() and p.suffix != '.pth':
                    # Checkpoint metadata was included beside each saved artifact.
                    name = str(p.relative_to(run))
                    if name not in archive.namelist():
                        archive.write(p, name)
        for name in ('publish_wuji_command_slider_final.py', 'wuji_command_slider.py',
            'prepare_wuji_command_slider_data.py', 'fit_wuji_command_slider_pair.py',
            'run_wuji_command_slider_pair.py', 'audit_wuji_command_slider_fit.py',
            'audit_wuji_command_slider_data.py', 'eval_wuji_fitted_state_encoder.py',
            'analyze_wuji_state_encoder_evaluations.py', 'wuji_timed_command_metrics.py'):
            archive.write(ROOT/'scripts'/name, 'source/'+name)
        archive.write(args.fit_audit, 'source/'+args.fit_audit.name)
    files = sorted(out.iterdir())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(digest(p)+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out), reports=len(rows), curves=curves,
        files=[(p.name, p.stat().st_size) for p in out.iterdir()])))


if __name__ == '__main__':
    main()
