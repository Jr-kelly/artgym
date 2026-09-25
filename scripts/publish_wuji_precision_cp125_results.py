"""Prepare measured reward comparison and fresh-seed results for the release."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root/'runs/wuji-goal/verification'
    out = root/'runs/wuji-goal/release-precision-cp125-20260922-0342'
    out.mkdir(exist_ok=True)
    prefix = 'wuji-knife-precision-cp125-reward-comparison-20260922'
    reports = {}
    for arm in ['near01', 'near1']:
        for cp in [50, 100, 150]:
            name = 'precision-%s-cp%d-perturb-small' % (arm, cp)
            reports[name] = json.loads((base/name/'report.json').read_text())
    fresh_names = ['precision-near01-cp125-perturb-small',
                   'precision-near01-cp125-blind-seed6259-perturb100',
                   'precision-near01-cp125-blind-seed7307-perturb100']
    for name in fresh_names:
        reports[name] = json.loads((base/name/'report.json').read_text())
    keys = ['successful_trials', 'strict_first_cycle_trials', 'stable_full_rollout_trials']
    assert all(d['envs'] == 100 for d in reports.values())
    initial_hashes = {}
    for name, d in reports.items():
        p = base/name/'perturbed_initial_states.npy'
        if p.exists():
            initial_hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    # The same prescribed development perturbations are used at every CP.
    assert len({sha for name, sha in initial_hashes.items() if reports[name]['seed'] == 1616}) == 1
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    for ax, key, title in zip(axes[:2], keys[1:], ['Stable first cycle', 'Stable full 20 seconds']):
        for arm, label, color in [('near01', 'Near-goal weight 0.1', '#24789f'),
                                  ('near1', 'Near-goal weight 1.0', '#ca6c4d')]:
            values = [reports['precision-%s-cp%d-perturb-small' % (arm, cp)][key] for cp in [50, 100, 150]]
            ax.plot([50, 100, 150], values, 'o-', color=color, label=label)
            for x, y in zip([50, 100, 150], values):
                ax.annotate(str(y), (x, y), xytext=(0, 6), textcoords='offset points', ha='center', fontsize=9)
        ax.set_xticks([50, 100, 150]); ax.set_xlabel('Additional training epochs')
        ax.set_title(title+'\nSame development seed 1616')
    axes[0].legend(loc='lower right', fontsize=8)
    ax = axes[2]
    for j, (key, label, color) in enumerate(zip(keys, ['Complete', 'First stable', 'Full stable'], ['#24789f', '#559a6c', '#c88b3d'])):
        values = [reports[name][key] for name in fresh_names]
        bars = ax.bar(np.arange(3)+(j-1)*.25, values, .23, label=label, color=color)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x()+bar.get_width()/2, value+1, str(value), ha='center', fontsize=8)
    ax.set_xticks([0, 1, 2], ['1616\nDevelopment', '6259\nFresh', '7307\nFresh'])
    ax.set_title('Selected low-weight CP125\nTwo new perturbation seeds')
    ax.legend(loc='lower right', fontsize=8)
    for ax in axes:
        ax.set_ylim(0, 113); ax.set_yticks([0, 25, 50, 75, 100]); ax.set_ylabel('Trials / 100')
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True); ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .02, 'Same nominal grasp and knife; position +/-0.5 mm/axis, joints +/-0.01 rad, rotation vector +/-0.5 deg/axis.\n'
             'Goals: 2 mm + 0.3 s dwell. Stable: base translation <10 mm, rotation <0.25 rad. No unseen-geometry or hardware claim.', fontsize=9)
    fig.tight_layout(rect=[0, .105, 1, 1]); fig.savefig(out/(prefix+'-results.png'), dpi=160); plt.close(fig)
    rows = []
    for name, d in reports.items():
        rows.append(dict(name=name, seed=d['seed'], trials=d['envs'], **{k:d[k] for k in keys},
                         checkpoint_sha256=d['checkpoint_sha256'],
                         report_sha256=hashlib.sha256((base/name/'report.json').read_bytes()).hexdigest(),
                         initial_states_sha256=initial_hashes.get(name)))
    (out/(prefix+'-provenance.json')).write_text(json.dumps(dict(
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), rows=rows), indent=2)+'\n')
    table = '\n'.join('|%s|%d|%d|%d|' % (row['name'], *(row[k] for k in keys)) for row in rows)
    text = '''# Wuji 精细开合：奖励对照与 CP125 复验

目标容差固定为 2 mm，连续停留 0.3 秒。所有测试均使用相同名义抓姿和现实尺寸刀具，
初始位置每轴 ±0.5 mm、关节 ±0.01 rad、旋转向量每轴 ±0.5°。以下每行分母均为 100。

| 模型/测试 | 首次完整开合 | 首次姿态稳定 | 全 20 秒稳定 |
|---|---:|---:|---:|
'''+table+'''

near01 与 near1 从同一 CP10、新优化器、相同训练种子和扰动课程开始；两组均为
5120 环境、32 步 rollout、学习率 5e-5、150 轮，预定唯一差别为接近目标奖励权重
0.1 或 1.0。该比较支持在这一训练配置下降低该项权重改善姿态质量；尚未重复多个训练种子。
对照 CP150 虽已达到 93/100 完整开合，但首次稳定仅 19/100，全程稳定 1/100。
因此宽松任务完成率不能代表握持质量。

CP125 在开发种子 1616 上全程稳定 50/100，高于 CP100 的 37/100 和 CP150 的 46/100，
故在两个新测试种子运行前固定选用 CP125。6259 和 7307 合计 200/200 首次开合并稳定，
106/200 全程稳定。开发测试不计入新的 200 次复验。三个初始状态文件哈希不同。

稳定标准固定为刀柄相对初始位置位移 <10 mm、旋转 <0.25 rad。全程标准还要求完成
至少一次完整循环，运行满 20 秒，且没有掉落、无效状态或目标超时。CP125 的开发测试中
29 次后续目标超时，20 次累计旋转超限，2 次位移超限；这些失败类别可重叠，全部保留。

这是一个抓姿附近的微扰鲁棒性，不能称为新抓姿、新几何或真机泛化。模型包已冻结。
后续实验从相同 CP125 开始比较绝对姿态成本，并单独开展包含实际初始扰动的 student 蒸馏。
旧模型、失败轨迹与原实验分组均保留。
'''
    (out/(prefix+'-results.md')).write_text(text)
    sums = [hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(out.iterdir()) if not p.name.endswith('SHA256SUMS.txt')]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sums)+'\n')
    print(out)


if __name__ == '__main__':
    main()
