"""Analyze acquisition failure without relabeling holding as manipulation."""
import hashlib
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    output = base / 'release-acquisition-diagnostic-20260922'
    output.mkdir(exist_ok=True)
    prefix = 'wuji-knife-acquisition-diagnostic-20260922'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    files = [Path(__file__), base / 'single24-arrival-proposal.json', root / 'wuji_single24_arrival_suite.json']
    results = dict(single24={}, long60={}, scope='Frozen policy traces; reward component reconstructed for diagnosis, not total training return. All failures retained.')
    traces = {}
    for seconds in [2, 5]:
        folder = base / 'verification' / ('wuji_single24_scratch_timed5_seed27_v1-cp100-perturb100-timed%dseconds' % seconds)
        status = json.loads((folder / 'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        report = json.loads((folder / 'report.json').read_text())
        trace = dict(np.load(folder / 'trace.npz'))
        assert report['num_envs'] == 100 and report['recorded_steps'] == 600
        # The URDF's closed joint coordinate is nonzero. Use the commanded
        # closed endpoint rather than interpreting raw joint position as travel.
        closed = trace['goal'].min(axis=0)
        displacement = (trace['slider'] - closed[None]) * 1000
        valid = trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
        opening = trace['goal'] > closed[None] + .02
        near_reward = 5 * np.exp(-((trace['slider'] - trace['goal']) / .002) ** 2)
        assert valid.all(), 'This diagnosis expects all 100 traces alive and finite'
        maximum = displacement.max(axis=0)
        phase_means = {phase: float(near_reward[mask & valid].mean())
                       for phase, mask in [('open', opening), ('close', ~opening)]}
        rows = [dict(env=i, maximum_opening_mm=float(maximum[i]),
                     near_open_mean=float(near_reward[:, i][opening[:, i]].mean()),
                     near_close_mean=float(near_reward[:, i][~opening[:, i]].mean()),
                     original_score=row) for i, row in enumerate(report['records'])]
        results['single24'][str(seconds)] = dict(
            original_report=report, phase_mean_near_reward=phase_means, records=rows,
            max_opening_mm_quantiles=np.quantile(maximum, [0, .25, .5, .75, 1]).tolist(),
            maximum_opening_below5mm=int((maximum < 5).sum()),
            pure_base_pose_stable=sum(row['alive_full'] and row['max_drift_m'] < .01 and row['max_rotation_rad'] < .25
                                      for row in report['records']),
            interpretation='Close-only behavior is consistent with an acquisition local optimum. The arrival-switching experiment tests this; no sole causal claim.')
        traces[seconds] = (trace, displacement, maximum)
        files.extend(folder / name for name in ['report.json', 'status.json', 'trace.npz', 'config.yaml', 'source.py', 'source_metrics.py'])
    for seconds in [2, 3, 5]:
        folder = base / 'verification' / ('near5-cp50-fresh100-extended60-timed%dseconds' % seconds)
        status = json.loads((folder / 'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        results['long60'][str(seconds)] = json.loads((folder / 'report.json').read_text())
        files.extend(folder / name for name in ['report.json', 'status.json', 'trace.npz', 'config.yaml', 'source.py', 'source_metrics.py'])
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7))
    values = [results['long60'][str(s)]['stable_full_all_endpoints'] for s in [2, 3, 5]]
    bars = axes[0].bar([0, 1, 2], values, color=['#287a8d', '#4578b0', '#cf8539'])
    axes[0].bar_label(bars, padding=3)
    axes[0].set_xticks([0, 1, 2], ['2 s', '3 s (untrained)', '5 s'])
    axes[0].set_ylim(0, 112)
    axes[0].set_ylabel('60-second joint successes / 100')
    axes[0].set_title('Original grasp: frozen seed23 CP50')
    for seconds, color in [(2, '#287a8d'), (5, '#cf8539')]:
        maximum = traces[seconds][2]
        axes[1].plot(np.arange(1, 101), np.sort(maximum), label='%d s' % seconds, color=color)
    axes[1].axhline(40, color='black', linestyle='--', linewidth=1, label='40 mm target')
    axes[1].set_xlabel('Trial rank, including the outlier')
    axes[1].set_ylabel('Maximum opening from closed (mm)')
    axes[1].set_title('New grasp24: scratch CP100\n99/100 move less than 5 mm')
    axes[1].legend(fontsize=8)
    x = np.arange(2)
    for i, seconds in enumerate([2, 5]):
        r = results['single24'][str(seconds)]['phase_mean_near_reward']
        bars = axes[2].bar(x + (i - .5) * .34, [r['open'], r['close']], .34,
                           color=['#287a8d', '#cf8539'][i], label='%d s commands' % seconds)
        axes[2].bar_label(bars, labels=['%.4f' % r['open'], '%.3f' % r['close']], fontsize=8, padding=3)
    axes[2].set_xticks(x, ['Open phase', 'Close phase'])
    axes[2].set_ylim(0, 5.8)
    axes[2].set_ylabel('Mean reconstructed near-goal reward')
    axes[2].set_title('New grasp24: scratch CP100\n0/100 full first cycles in both protocols')
    axes[2].legend(fontsize=8, loc='upper left')
    for axis in axes:
        axis.grid(axis='y', alpha=.2)
        axis.set_axisbelow(True)
        axis.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .025, 'Left: the same 100 perturbations of the original grasp; no new-grasp claim. Right two panels: another training grasp, 100 perturbations, 20 seconds.\n'
             'Joint success includes all endpoint holds and full-time base stability. Reconstructed reward is one component, not the total training return.', fontsize=8.5)
    fig.tight_layout(rect=[0, .1, 1, 1])
    fig.savefig(output / (prefix + '-long-timing-and-acquisition-failure.png'), dpi=160)
    plt.close(fig)
    results['source_sha256'] = {str(path.relative_to(root)): sha(path) for path in files}
    (output / (prefix + '-all-trials.json')).write_text(json.dumps(results, indent=2, allow_nan=False) + '\n')
    with zipfile.ZipFile(output / (prefix + '-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, str(path.relative_to(root)))
    text = '''# 长时操作与新抓姿的学习障碍

原抓姿的固定 seed23 near5 CP50，在同100初态、60秒测试中：每2/3/5秒切换指令，联合成功分别74/82/98。
3秒未用于该teacher训练。三种时序全部100次存活，失败仍保留。不同循环次数属于各自协议，不能当作相同运动量比较。

新训练抓姿24的从头固定5秒teacher CP100，在相同100扰动初态的2秒与5秒评估中，都是0首轮、0联合、100存活、98纯刀柄位姿稳定。
99次最大打开距离不足5mm，中位数约0.487mm；目标40mm。一个约50mm的异常样本同样保留，不筛除。
原URDF关闭位置不为零，图中位移以实际关闭指令为原点。
按已保存实际轨迹重算近目标奖励5×exp(-(误差/2mm)^2)，打开均值约0.000175，关闭约4.943/4.923。
这只是一个奖励分量，不能替代完整训练回报，也没有证明它是唯一失败原因。

论文训练在到位后才切换指令，因此未打开时不会自动进入容易得分的关闭阶段。
新增single24到位切换对照：同seed20261027、同从头初始化、5120环境、horizon32、300轮，保持物理、奖励和2mm精度要求。
只将训练指令从固定5秒改为到位切换；独立评估继续使用严格的固定2/5秒指令。
实验先验证实际配置只差时钟、10000次物理转移与成功切换链路，再通过3轮PPO检查启动正式训练；此制品不宣称该实验已成功。
这是Wuji迁移诊断，绝非把全部设置称为原论文完全复现。多抓姿、多几何、可靠student和真机仍未完成。
'''
    (output / (prefix + '-results.md')).write_text(text)
    sums = [sha(p) + '  ' + p.name for p in sorted(output.iterdir()) if not p.name.endswith('SHA256SUMS.txt')]
    (output / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sums) + '\n')
    print(json.dumps(dict(output=str(output), assets=len(sums) + 1)))


if __name__ == '__main__':
    main()
