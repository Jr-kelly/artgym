"""Package paired teacher replication, transfer controls and student failures.

This script builds local artifacts only. Publication is a separate explicit gh
release upload. Metric traces retain every trial; raw hand/contact traces stay
in the experiment directories and their hashes are recorded.
"""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    out = base / 'release-replication-transfer-student-20260922'
    out.mkdir(exist_ok=False)
    prefix = 'wuji-knife-replication-transfer-student-20260922'
    evidence = out / 'evidence'
    evidence.mkdir()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    reports, raw_files, rows = {}, {}, []
    score_keys = ['active', 'fall', 'invalid', 'slider', 'goal', 'drift', 'rotation']
    count_keys = ['first_cycle', 'first_cycle_strict', 'all_commands_attained',
                  'all_endpoints_held', 'stable_full', 'stable_full_all_endpoints', 'alive_full']

    def add(name, folder, label, seconds, expected):
        status = json.loads((folder / 'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0, name
        report = json.loads((folder / 'report.json').read_text())
        assert len(report['records']) == report['num_envs']
        source = folder / 'trace.npz'
        with np.load(source) as full:
            metric_trace = {k: full[k] for k in score_keys}
        scored = score_timed_trace(metric_trace, int(seconds * 30), 9, expected)
        assert all(scored[k] == report[k] for k in count_keys), name
        np.savez_compressed(evidence / (name + '-metric-trace.npz'), **metric_trace)
        for field in ['report.json', 'status.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            p = folder / field
            if p.exists():
                shutil.copy2(p, evidence / (name + '-' + field))
                raw_files[str(p.relative_to(root))] = sha(p)
        raw_files[str(source.relative_to(root))] = sha(source)
        reports[name] = report
        rows.append(dict(name=name, cohort=label, command_seconds=seconds,
                         duration_seconds=expected / 30, trials=report['num_envs'],
                         **{k: report[k] for k in count_keys}))
        return report

    for seed in [23, 26]:
        for seconds in [2, 5]:
            name = 'near5-cp50-seed%d-fresh200-seed20261035-timed%dseconds' % (seed, seconds)
            add(name, base / 'verification' / name, 'same 200 perturbations, one nominal grasp', seconds, 600)
    assert len({reports[n]['initial_states_sha256'] for n in reports}) == 1
    for seed in [23, 26]:
        for seconds in [2, 3, 5]:
            name = ('near5-cp50-fresh100-extended60-timed%dseconds' % seconds if seed == 23 else
                    'near5-cp50-seed26-reused100-extended60-timed%dseconds' % seconds)
            add(name, base / 'verification' / name, 'same 100 long-rollout states, reused across models', seconds, 1800)
    for seconds in [2, 5]:
        name = 'near5-cp50-equivalent-original-frame-seed30-timed%dseconds' % seconds
        add(name, base / 'verification' / name, 'physically equivalent source grasp in generated asset frame', seconds, 600)
    add('single24-scripted-perturb100', base / 'diagnostics/single24-scripted-perturb100',
        'scripted feasibility only, one training grasp / 100 perturbations', 5, 600)
    for cp in [25, 100]:
        for seconds in [2, 5]:
            name = 'student-near5cp50-teacher500-cp%d-timed%dseconds-perturb100' % (cp, seconds)
            add(name, base / 'verification' / name, 'student closed loop, reused 100 development states', seconds, 600)
    for duration in [20, 60]:
        name = 'wuji_horizon%d_near5_cp50_seed33_v1-cp25-extended60-timed2seconds-seed30' % duration
        add(name, base / 'verification' / name, 'matched continuation pair, same 100 long-rollout states', 2, 1800)

    latent_dir = base / 'diagnostics/near5cp50-student-latent-on-teacher32'
    latent = json.loads((latent_dir / 'encoder_report.json').read_text())
    assert latent['status'] == 'completed' and latent['model_before'] == latent['model_after']
    assert [x['sha256'] for x in latent['students']] == [
        reports['student-near5cp50-teacher500-cp%d-timed2seconds-perturb100' % cp]['student_sha256']
        for cp in [25, 100]]
    for p in latent_dir.iterdir():
        if p.is_file() and p.suffix in ['.json', '.py', '.yaml', '.npz']:
            raw_files[str(p.relative_to(root))] = sha(p)
            shutil.copy2(p, evidence / ('latent-on-teacher32-' + p.name))
    with np.load(latent_dir / 'encoder_error_trace.npz') as data:
        assert data['active'].all()
        latent_mse = (data['latent_error'] ** 2).mean(axis=(0, 2, 3))
        thumb_error = np.abs(data['action_error'][:, :, :, 16:]).mean(axis=(0, 2, 3)) * 25

    def finish(fig, name, footer):
        for ax in fig.axes:
            ax.grid(axis='y', alpha=.2)
            ax.set_axisbelow(True)
            ax.spines[['top', 'right']].set_visible(False)
        fig.text(.02, .015, footer, fontsize=8)
        fig.tight_layout(rect=[0, .07, 1, 1])
        fig.savefig(out / (prefix + '-' + name + '.png'), dpi=165)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for i, seed in enumerate([23, 26]):
        x = np.arange(2) + (i - .5) * .32
        y = [reports['near5-cp50-seed%d-fresh200-seed20261035-timed%dseconds' % (seed, t)]['stable_full_all_endpoints'] for t in [2, 5]]
        bars = axes[0].bar(x, y, .3, label='training seed %d' % seed)
        axes[0].bar_label(bars, padding=3)
        y = [reports[('near5-cp50-fresh100-extended60-timed%dseconds' % t if seed == 23 else
                     'near5-cp50-seed26-reused100-extended60-timed%dseconds' % t)]['stable_full_all_endpoints'] for t in [2, 3, 5]]
        axes[1].plot([2, 3, 5], y, 'o-', label='training seed %d' % seed)
        for x, value in zip([2, 3, 5], y):
            above = (i == 1) if x in [2, 3] else (i == 0)
            axes[1].annotate(str(value), (x, value), xytext=(0, 7 if above else -14), textcoords='offset points', ha='center')
    axes[0].set(xticks=[0, 1], xticklabels=['2 s commands', '5 s commands'], ylim=(0, 225),
                title='Frozen CP50 paired replication\nSame fresh 200 states, 20 s rollout', ylabel='Joint successes / 200')
    axes[1].set(xticks=[2, 3, 5], ylim=(0, 110), xlabel='Command duration (seconds)',
                title='Same 100 states, 60 s rollout\n3 s commands were not used in training', ylabel='Joint successes / 100')
    axes[0].legend(fontsize=8, loc='lower left')
    axes[1].legend(fontsize=8, loc='lower left')
    finish(fig, 'paired-seeds-and-60seconds', 'One nominal grasp; both training seeds share the same CP10 ancestor. No unseen-grasp or hardware claim.\nJoint: every command tail within 2 mm for 0.3 s; base drift <10 mm / rotation <0.25 rad, alive and finite throughout.')

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    bars = axes[0].bar(['2 s', '5 s'], [reports['near5-cp50-equivalent-original-frame-seed30-timed%dseconds' % t]['stable_full_all_endpoints'] for t in [2, 5]], color='#268c91')
    axes[0].bar_label(bars, padding=3)
    axes[0].set(title='Equivalent asset-frame control\nSame physical grasp, frozen CP50', ylabel='Joint successes / 100', ylim=(0, 115))
    r = reports['single24-scripted-perturb100']
    bars = axes[1].bar(['First cycle', 'Strict first', 'Joint 20 s', 'Alive'], [r[k] for k in ['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints', 'alive_full']], color='#be8450')
    axes[1].bar_label(bars, padding=3)
    axes[1].set(title='Scripted contact path: fragile\nOne new training grasp, 100 perturbations', ylabel='Trials / 100', ylim=(0, 115))
    bars = axes[2].bar(['Original\nCP50', '20 s training\n+25 epochs', '60 s training\n+25 epochs'], [
        reports['near5-cp50-fresh100-extended60-timed2seconds']['stable_full_all_endpoints'],
        *[reports['wuji_horizon%d_near5_cp50_seed33_v1-cp25-extended60-timed2seconds-seed30' % t]['stable_full_all_endpoints'] for t in [20, 60]]], color=['#268c91', '#718dbe', '#a980af'])
    axes[2].bar_label(bars, padding=3)
    axes[2].set(title='Longer episodes have not helped yet\n60 s rollout, 2 s commands', ylabel='Joint successes / 100', ylim=(0, 115))
    finish(fig, 'physical-controls-and-horizon', 'The equivalent-frame control is not a new grasp; the scripted path is not RL. All failed trials remain in evidence.\nThe two continuation runs share constant LR 1e-5 and differ in episode duration. Their CP100 evaluation is separate.')

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
    bars = axes[0].bar(['CP25', 'CP100'], latent_mse, color='#648bb5'); axes[0].bar_label(bars, fmt='%.3f', padding=3)
    axes[0].set(title='Latent MSE on teacher states', ylim=(0, float(max(latent_mse)) * 1.25))
    bars = axes[1].bar(['CP25', 'CP100'], thumb_error, color='#648bb5'); axes[1].bar_label(bars, fmt='%.2f', padding=3)
    axes[1].set(title='Thumb target increment error\nSame incoming teacher RNN state', ylabel='Mean absolute error (mrad / step)', ylim=(0, float(max(thumb_error)) * 1.25))
    for i, metric in enumerate(['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints']):
        bars = axes[2].bar(np.arange(2)+(i-1)*.25, [reports['student-near5cp50-teacher500-cp100-timed%dseconds-perturb100' % t][metric] for t in [2, 5]], .23, label=['First cycle', 'Strict first', 'Joint 20 s'][i])
        axes[2].bar_label(bars, padding=2, fontsize=8)
    axes[2].set(xticks=[0, 1], xticklabels=['2 s commands', '5 s commands'], ylim=(0, 112), title='CP100 student closed loop', ylabel='Trials / 100')
    axes[2].legend(fontsize=8)
    finish(fig, 'student-encoder-and-closed-loop', 'Left/middle: teacher drives physics on 32 reused states; lower prediction error is not closed-loop success.\nRight: student alone drives physics on the same 100 development states in both protocols. No joint success yet at CP100.')

    for source in [base / 'cp50-replication-fresh200-seed20261035/initial_states.npy',
                   base / 'cp50-replication-fresh200-seed20261035/manifest.json',
                   base / 'equivalent-frame-evaluation-states/initial_states.npy',
                   base / 'equivalent-frame-evaluation-states/manifest.json',
                   base / 'single24-evaluation-states/initial_states.npy',
                   base / 'near5-cp50-extended-fresh100-seed20261030/seed20261030.npy',
                   base / 'verification/precision-near01-cp125-perturb-small/perturbed_initial_states.npy',
                   base / 'diagnostics/bridge2-hemisphere-runtime/report.json', Path(__file__)]:
        assert source.is_file(), str(source)
        raw_files[str(source.relative_to(root))] = sha(source)
        target = evidence / str(source.relative_to(root)).replace('/', '__')
        shutil.copy2(source, target)
    with (out / (prefix + '-counts.csv')).open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    provenance = dict(scope=__doc__, reports=reports, student_latent=latent,
                      original_file_sha256=raw_files, metric_traces_recomputed=True)
    (out / (prefix + '-all-trials-provenance.json')).write_text(json.dumps(provenance, indent=2, allow_nan=False)+'\n')
    with zipfile.ZipFile(out / (prefix + '-metric-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(evidence.iterdir()): archive.write(path, path.name)
    text = '''# Wuji：第二训练种子、物理对照与 student 失败记录

全部为 PhysX 仿真，官方 Wuji 执行器参数、ArtBot 几何、147×19×11 mm 刀具；阻尼 0.3 未经真机标定。
联合成功要求所有指令末尾连续 0.3 秒在 ±2 mm 内，全程刀柄漂移 <10 mm、旋转 <0.25 rad，存活且数值有效。

|同一批新 200 初态，20 秒|2 秒指令|5 秒指令|
|---|---:|---:|
|seed23 CP50|197/200|199/200|
|seed26 CP50|198/200|198/200|

两份模型冻结后才生成 seed20261035 初态。两种训练种子共享祖先 CP10，不是独立从零训练；200 个初态都是同一名义抓姿的扰动。
相同另一批 100 初态，60 秒的 2/3/5 秒指令：seed23 联合 74/82/98，seed26 为 83/94/97。
3 秒未用于训练，但这些初态已在其他协议使用；不把六个测试分母相加当作新抓姿数量。

等价资产对照保持世界接触几何、质量惯量及初始抓姿，只改变资产局部坐标约定并纠正输入编码；2/5 秒均 100/100 联合。
这是确认处理链路可以保留原成功策略，不是新抓姿泛化，也不是不同仿真批次的逐帧等价证明。

single24 固定 IK 拇指路径在同 100 个扰动初态上为 68 首轮、50 严格首轮、14 全程联合、34 存活；66 次掉落全部保留。
支撑指维持初始预压力，只向手部发送合法关节动作，刀具无轨迹或外力辅助。它是脚本可行性诊断，不计入 RL 成绩。

固定较低学习率的 20/60 秒训练回合配对，在追加 25 轮后的 60 秒快速测试为 64/48 联合，原 CP50 为 74。
两配对组只改变训练回合长度；相对原策略还涉及继续优化，不能把所有变化都归因于回合长度。最终 CP100 另行评估。

student CP25→CP100 在同 32 个 teacher 驱动物理状态上的 latent MSE 和动作误差下降；teacher 始终驱动物理，这不是 student 成功率。
独立 student CP100 闭环 100 次：2/5 秒指令首轮均 60，严格首轮 20/2，全程联合 0/0，存活 78/60。
所有失败均保留；部分首轮开合不等于持续控制或真机部署。

ZIP 保存所有试验的完整评分字段轨迹，并逐项重算结果；原始完整关节/接触轨迹仍在实验目录，SHA256 在 provenance 中。
图、CSV、JSON 使用明确分母；没有筛掉失败样本。
'''
    (out / (prefix + '-results.md')).write_text(text)
    sums = [sha(p)+'  '+p.name for p in sorted(out.iterdir()) if p.is_file()]
    (out / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sums)+'\n')
    print(json.dumps(dict(output=str(out), assets=len(sums)+1, evaluations=len(rows))))


if __name__ == '__main__':
    main()
