"""Package independently verified CP50 and the full failure-preserving 60s video."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    out = base / 'release-near-reward-cp50-20260922'
    out.mkdir(exist_ok=True)
    prefix = 'wuji-knife-near-reward-cp50-20260922'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    reports, files = {}, []
    fresh = ['near-reward-near5-cp50-fresh200-seed20261029-timed%dseconds' % t for t in [2, 5]]
    development = ['wuji_variable_nearreward5_seed23_v1-cp%d-timed%dseconds-perturb100' % (cp, t)
                   for cp in [10, 25, 50, 100] for t in [2, 5]]
    video = 'near5-cp50-fresh100-preset3-extended60-timed2seconds-video'
    for name in fresh + development + [video]:
        folder = base / 'verification' / name
        status = json.loads((folder / 'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        report = json.loads((folder / 'report.json').read_text())
        assert len(report['records']) == report['num_envs']
        assert sum(r['stable_full_all_endpoints'] for r in report['records']) == report['stable_full_all_endpoints']
        reports[name] = report
        files.extend(folder / f for f in ['report.json', 'status.json', 'trace.npz'])
    assert [reports[n]['stable_full_all_endpoints'] for n in fresh] == [199, 200]
    assert all(reports[n]['num_envs'] == 200 for n in fresh)
    assert len({reports[n]['checkpoint_sha256'] for n in fresh + [video]}) == 1
    assert reports[video]['initial_state_rows'] == [0, 2, 76]
    assert reports[video]['stable_full_all_endpoints'] == 2
    assert reports[video]['prefix_metrics']['40']['stable_full_all_endpoints'] == 3
    folder = base / 'verification' / video
    media = json.loads((folder / 'media-verification.json').read_text())
    assert media['decoded_frames'] == 1800 and media['fps'] == 30
    for source, target in [('policy.mp4', '-preset3-60seconds-no-text-failure-retained.mp4'),
                           ('preview.png', '-preview.png'), ('sequence.png', '-sequence.png')]:
        shutil.copy2(folder / source, out / (prefix + target))
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    values = [reports[n]['stable_full_all_endpoints'] for n in fresh]
    bars = axes[0].bar([0, 1], values, width=.55, color=['#248d8f', '#d7802b'])
    axes[0].bar_label(bars, padding=3)
    axes[0].set_xticks([0, 1], ['2-second commands', '5-second commands'])
    axes[0].set_ylabel('Joint successes / 200')
    axes[0].set_ylim(0, 225)
    axes[0].set_title('Frozen CP50: fresh seed 20261029\nSame 200 initial states in both protocols')
    for seconds, color in [(2, '#248d8f'), (5, '#d7802b')]:
        y = [reports['wuji_variable_nearreward5_seed23_v1-cp%d-timed%dseconds-perturb100' % (cp, seconds)]['stable_full_all_endpoints']
             for cp in [10, 25, 50, 100]]
        axes[1].plot([10, 25, 50, 100], y, 'o-', color=color, label='%d-second commands' % seconds)
        for x, value in zip([10, 25, 50, 100], y):
            axes[1].annotate(str(value), (x, value), xytext=(0, 6 if seconds == 2 else -13), textcoords='offset points', ha='center', fontsize=8)
    axes[1].set_ylim(0, 113)
    axes[1].set_xlabel('Additional training epochs')
    axes[1].set_ylabel('Joint successes / 100')
    axes[1].set_title('Development cohort: later training can regress')
    axes[1].legend(loc='lower left', fontsize=8)
    for ax in axes:
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .025, '20-second evaluations; one nominal grasp with reset perturbations. '
             'Joint: all command tails within 2 mm for 0.3 s,\nbase drift <10 mm / rotation <0.25 rad throughout, alive and finite. '
             'No unseen-grasp, geometry or hardware claim.', fontsize=8.5)
    fig.tight_layout(rect=[0, .1, 1, 1])
    fig.savefig(out / (prefix + '-fresh200-and-late-regression.png'), dpi=160)
    plt.close(fig)
    files.extend([folder / 'media-verification.json', folder / 'source.py', folder / 'source_metrics.py', folder / 'config.yaml',
                  base / 'near-reward-cp50-fresh200-proposal.json', base / 'near5-cp50-extended-proposal.json',
                  base / 'near5-cp50-extended-fresh100-seed20261030/seed20261030.npy',
                  base / 'near5-cp50-extended-fresh100-seed20261030/manifest.json',
                  base / 'diagnostics/extended-timed-parity.json', root / 'wuji_near_reward_suite.json', Path(__file__)])
    for name in fresh:
        files.extend(base / 'verification' / name / f for f in ['config.yaml', 'source.py', 'source_metrics.py'])
    (out / (prefix + '-all-trials-provenance.json')).write_text(json.dumps(dict(reports=reports,
        media=media, files={str(p.relative_to(root)): sha(p) for p in files}), indent=2, allow_nan=False) + '\n')
    with zipfile.ZipFile(out / (prefix + '-evaluation-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, str(path.relative_to(root)))
    text = '''# Wuji CP50：单抓姿的独立验证

固定teacher SHA256：`2230146804f9e0de54d4e61ab3efd2d90ec6ef1ee403130cd9a46c235bf860b7`。
它使用官方Wuji关节增益和armature、ArtBot几何、147×19×11mm刀具与PhysX；滑块阻尼0.3仍未做真机标定。
从原定时teacher CP10继续训练50轮，每轮5120×32次转移，近目标高斯奖励系数5，训练指令随机2/5秒。
网络推理直接输出20维关节动作，物体依靠接触运动，没有读取预先求解轨迹。

|独立测试，seed20261029|首次稳定开合|20秒全程联合成功|
|---|---:|---:|
|2秒切换指令|200/200|199/200|
|5秒切换指令|200/200|200/200|

两行使用相同的200个新初态，不能称为400个独立抓姿。单个名义抓姿扰动为每轴位置±0.5mm、
关节±0.01rad、旋转向量每轴±0.5度。模型在产生这批初态前已冻结。
联合指标要求每条指令最后0.3秒均在目标±2mm，全程刀柄位移<10mm/旋转<0.25rad，存活且数值有效。
2秒测试唯一失败为第29行：仍存活，但末段未能保持关闭，最大旋转0.2612rad；失败完整保留。

60秒无字视频来自另一批预定seed20261030中的0/2/76行，在本机4090实际运行固定策略。
每2秒切换一次，共30条指令、15个完整开合循环。三格都在所有指令末尾到位，前40秒3/3握稳，
全60秒2/3联合成功；一格后期刀柄位姿超限，画面和轨迹均保留。
视频是三个预定样本，不能替代独立100次长时评估，且不加入上表分母。
新增长时评估入口在20秒设置下与原入口实际逐帧比较：3个初态、600次转移、全部轨迹字段完全一致。

后期CP100在开发100初态上，2秒协议降至7/100（88次掉落），5秒协议仍为93/100。
CP50相应为99/100与100/100，因此保留CP50。训练平均回报继续上升，不能代替独立操作质量评估。
证据支持快速多次开合后的累积失稳，尚未唯一隔离出奖励、优化、探索或指令频率的因果作用。

60秒100次及未训练的3秒指令、多抓姿迁移与新teacher的student蒸馏另行开展。
当前是单抓姿的学习策略成功，不代表多几何泛化或真机部署成功。
'''
    (out / (prefix + '-results.md')).write_text(text)
    sums = [sha(p) + '  ' + p.name for p in sorted(out.iterdir()) if not p.name.endswith('SHA256SUMS.txt')]
    (out / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sums) + '\n')
    print(json.dumps(dict(output=str(out), assets=len(sums) + 1)))


if __name__ == '__main__':
    main()
