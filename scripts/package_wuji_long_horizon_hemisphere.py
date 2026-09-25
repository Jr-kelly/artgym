"""Publish long-horizon limits, repeated reward comparison and frame failures."""
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
    out = base / 'release-long-horizon-hemisphere-20260922'
    out.mkdir(exist_ok=True)
    prefix = 'wuji-knife-long-horizon-hemisphere-20260922'
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    long_names = ['near5-cp50-fresh100-extended60-timed%dseconds' % t for t in [2, 5]]
    frame_names = ['near5-cp50-functional20-%s-local-timed%dseconds' % (mode, seconds)
                   for seconds in [2, 5] for mode in ['acquisition', 'acquisition_hemisphere']]
    seed_names = ['wuji_variable_nearreward%s_seed26_v1-cp10-fresh200-timed%dseconds' % (coef, seconds)
                  for seconds in [2, 5] for coef in ['01', '5']]
    reports, provenance, files = {}, {}, []
    for name in long_names + frame_names + seed_names:
        path = base / 'verification' / name
        status = json.loads((path / 'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        report = json.loads((path / 'report.json').read_text())
        assert sum(row['stable_full_all_endpoints'] for row in report['records']) == report['stable_full_all_endpoints']
        reports[name] = report
        provenance[name] = dict(status=status, report_sha256=sha(path / 'report.json'))
        files.extend(path / f for f in ['report.json', 'status.json', 'config.yaml'])
        for name2 in ['source.py', 'source_metrics.py', 'frame-provenance.json', 'trace.npz']:
            if (path / name2).exists():
                files.append(path / name2)
    sensitivity = base / 'diagnostics/functional20-hemisphere-policy-sensitivity/report.json'
    inp = json.loads(sensitivity.read_text())
    assert inp['status'] == 'verified' and inp['model_and_normalizer_unchanged']
    assert [reports[n]['stable_full_all_endpoints'] for n in long_names] == [74, 98]
    assert [reports[n]['stable_full_all_endpoints'] for n in seed_names] == [79, 122, 50, 130]
    assert all(reports[n]['stable_full_all_endpoints'] == 0 for n in frame_names)
    splits = {}
    for name in frame_names:
        splits[name] = {split: dict(trials=end-start, **{key: sum(row[key] for row in reports[name]['records'][start:end])
                              for key in ['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints', 'alive_full']})
                        for split, start, end in [('train', 0, 80), ('test', 80, 112)]}

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    for name, seconds, color in zip(long_names, [2, 5], ['#278f96', '#d58230']):
        vals = [reports[name]['prefix_metrics'][str(t)]['stable_full_all_endpoints'] for t in [20, 40, 60]]
        axes[0].plot([20, 40, 60], vals, 'o-', label='%ds commands' % seconds, color=color)
        for t, value in zip([20, 40, 60], vals):
            axes[0].annotate(str(value), (t, value), xytext=(0, 7 if seconds == 5 else -14), textcoords='offset points', ha='center')
    axes[0].set_ylim(0, 112)
    axes[0].set_ylabel('Joint successes / 100')
    axes[0].set_xlabel('Uninterrupted physical rollout (seconds)')
    axes[0].set_title('CP50: same fresh 100, seed 20261030\nAll 100 survive the full 60 s in both conditions')
    axes[0].legend(loc='lower left')
    for i, (coefficient, color) in enumerate([('01', '#888f9b'), ('5', '#278f96')]):
        vals = [reports['wuji_variable_nearreward%s_seed26_v1-cp10-fresh200-timed%dseconds' % (coefficient, s)]['stable_full_all_endpoints'] for s in [2, 5]]
        bars = axes[1].bar(np.arange(2) + (i-.5)*.34, vals, .32, color=color, label='Near reward ' + ('0.1' if coefficient == '01' else '5'))
        axes[1].bar_label(bars, padding=3)
    axes[1].set_xticks([0, 1], ['2s commands', '5s commands'])
    axes[1].set_ylim(0, 220)
    axes[1].set_ylabel('Joint successes / 200')
    axes[1].set_title('Independent training seed 20261026, CP10\nPreviously fixed seed 20261025 evaluation cohort')
    axes[1].legend(loc='upper right', fontsize=8)
    for ax in axes:
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .02, 'Both panels use one nominal grasp with perturbations. Joint: every command tail within 2 mm for 0.3 s, '
             'base drift <10 mm / rotation <0.25 rad throughout.\nRight panel is a second training seed on a reused fixed cohort, '
             'not a second newly drawn evaluation cohort. No hardware claim.', fontsize=8.5)
    fig.tight_layout(rect=[0, .11, 1, 1])
    fig.savefig(out / (prefix + '-long-rollouts-and-repeated-reward.png'), dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    for j, (key, label, color) in enumerate([('clipped_policy_input_fraction', 'Policy input', '#888f9b'),
                                          ('clipped_privileged_input_fraction', 'Privileged input', '#278f96')]):
        vals = [100*inp['conditions'][name][key] for name in ['raw', 'acquisition', 'acquisition_hemisphere']]
        bars = axes[0].bar(np.arange(3)+(j-.5)*.34, vals, .32, label=label, color=color)
        axes[0].bar_label(bars, fmt='%.1f', padding=2, fontsize=9)
    axes[0].set_xticks([0, 1, 2], ['Raw', 'Frame', 'Frame + sign'])
    axes[0].set_ylim(0, 50)
    axes[0].set_ylabel('Clipped observation entries (%)')
    axes[0].set_title('Same 256 training-source observations\nFrozen CP50 and normalization statistics')
    axes[0].legend(loc='upper right', fontsize=8)
    vals = [splits[name]['train']['first_cycle_strict'] for name in frame_names]
    bars = axes[1].bar(range(4), vals, color=['#888f9b', '#278f96']*2)
    axes[1].bar_label(bars, padding=3)
    axes[1].set_xticks(range(4), ['2s frame', '2s frame+sign', '5s frame', '5s frame+sign'], rotation=12)
    axes[1].set_ylim(0, 6)
    axes[1].set_ylabel('Strict first-cycle successes / 80')
    axes[1].set_title('20 training grasps × 4 perturbations\nFull 20 s joint success remains 0/80 in every arm')
    axes[1].text(.03, .9, 'Held-out grasp: 0/32 first or joint in every arm\nSign adaptation: 0/32 held-out survivors at 20 s', transform=axes[1].transAxes, fontsize=8.5)
    for ax in axes:
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .02, 'Quaternion q and -q encode the same rotation; this network is sensitive to their component values. '
             'Physics and learned weights stay fixed.\nAll strict first-cycle successes occur on training grasp 16. '
             'One held-out grasp and no joint successes do not establish generalization.', fontsize=8.5)
    fig.tight_layout(rect=[0, .11, 1, 1])
    fig.savefig(out / (prefix + '-input-conventions-and-grasp-failures.png'), dpi=160)
    plt.close(fig)
    files += [sensitivity, base / 'diagnostics/near5-cp50-long60-failure-components.json',
              base / 'functional20-hemisphere-proposal.json', base / 'functional20-frame-eval-states/manifest.json',
              base / 'functional20-frame-eval-states/initial_states.npy',
              base / 'near5-cp50-extended-fresh100-seed20261030/seed20261030.npy',
              base / 'near-reward-fresh200-seed20261025/initial_states.npy',
              root / 'wuji_near_reward_seed26_suite.json', root / 'scripts/wuji_quaternion_hemisphere.py',
              root / 'scripts/probe_wuji_hemisphere_policy_sensitivity.py', root / 'scripts/audit_wuji_hemisphere_transfer.py', Path(__file__)]
    provenance_all = dict(reports=reports, grouped_frame_records=splits, sensitivity=inp,
                          provenance=provenance, files={str(path.relative_to(root)): sha(path) for path in files})
    (out / (prefix + '-all-trials-provenance.json')).write_text(json.dumps(provenance_all, indent=2, allow_nan=False) + '\n')
    with zipfile.ZipFile(out / (prefix + '-evaluation-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, str(path.relative_to(root)))
    text = '''# 长时保持、第二训练种子与坐标约定

CP50在新的100个同抓姿扰动（seed20261030）上做实际连续60秒测试：

|指令周期|20秒联合|40秒联合|60秒联合|60秒存活|
|---|---:|---:|---:|---:|
|2秒|99/100|84/100|74/100|100/100|
|5秒|100/100|100/100|98/100|100/100|

联合指标保持不变：每条指令最后0.3秒都在目标±2mm，刀柄全程位移<10mm/转角<0.25rad，存活且有限。
2秒协议26次联合失败中，11次仅姿态不合格、6次仅到位保持不合格、9次两者均不合格；没有掉落。
三个时长是同一次60秒轨迹的前缀，不是三批独立试验。3秒协议另行测试，本批不包含其结果。

第二训练seed 20261026的匹配CP10对照：近目标系数0.1/5，2秒联合79/200与122/200，5秒50/200与130/200。
两臂同初始模型、新优化器、训练seed、5120env与100epoch预算；这里只比较各自CP10。
复用先前固定seed 20261025的200初态；它是第二训练种子验证，不是新抽样200初态或新抓姿。

固定CP50的256条训练来源输入，仅把资产坐标转换后的四元数统一到原训练姿态所在半球，
特权输入截断比例21.7%降至1.9%；拇指裁剪动作平均绝对变化0.593。
旋转矩阵完全不变，任意同时取负的四元数变为相同表示，其他输入分量、网络及normalizer不变。
这直接确认输入约定敏感性，但不是操作成功证据。

实际物理对照使用原20训练抓姿×4扰动和1测试抓姿×32扰动，共112初态。
2秒的训练首次严格成功从0/80变4/80，5秒从0/80变3/80，全部来自训练抓姿16；
各臂全20秒联合都是0/80。测试抓姿各臂完整开合、首次严格和全程联合都是0/32。
统一符号后的测试抓姿在两周期都0/32存活；原仅坐标转换分别5/32、21/32存活，恶化完整保留。
因此不能宣称已获得多抓姿泛化。所有物理试验都在本机4090运行，保持相同物理与模型。

后续20抓姿适配采用统一坐标及符号，仍保留原20行训练和1行测试，不按测试结果筛选数据。
另做20/60秒训练回合长度匹配实验；它们不替代本批固定策略结果。
现实刀具为147×19×11mm，ArtBot几何与PhysX、官方关节增益/armature；刀具阻力和真机尚未标定。
'''
    (out / (prefix + '-results.md')).write_text(text)
    sums = [sha(path) + '  ' + path.name for path in sorted(out.iterdir()) if not path.name.endswith('SHA256SUMS.txt')]
    (out / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sums) + '\n')
    print(json.dumps(dict(output=str(out), assets=len(sums) + 1)))


if __name__ == '__main__':
    main()
