"""Package fixed-cohort near-reward results, including every failed trial."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    out = base / 'release-near-reward-cp10-20260922'
    out.mkdir(exist_ok=True)
    prefix = 'wuji-knife-near-reward-cp10-20260922'
    cohorts = ['near-reward-' + group + '-cp10-fresh200-seed20261025-timed5seconds'
               for group in ['original', 'near01', 'near5']]
    videos = ['near-reward-' + group + '-cp10-fresh200-preset3-timed5second' + 's-video'
              for group in ['original', 'near5']]
    reports, provenance = {}, {}
    paths = []
    for name in cohorts + videos:
        folder = base / 'verification' / name
        status = json.loads((folder / 'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0, name
        report = json.loads((folder / 'report.json').read_text())
        assert report['recorded_steps'] == 600
        assert report['protocol']['stage_seconds'] == 5
        assert report['protocol']['arrival_used_for_switching'] is False
        assert len(report['records']) == report['num_envs']
        for field in ['first_cycle_strict', 'stable_full', 'stable_full_all_endpoints']:
            assert sum(row[field] for row in report['records']) == report[field]
        reports[name] = report
        provenance[name] = dict(status=status, report_sha256=sha(folder / 'report.json'))
        paths.extend(folder / item for item in ['report.json', 'status.json', 'config.yaml',
                     'source.py', 'source_metrics.py', 'trace.npz'])
    assert len({reports[n]['initial_states_sha256'] for n in reports}) == 1
    assert [reports[n]['stable_full_all_endpoints'] for n in cohorts] == [85, 79, 170]
    assert all(reports[n]['num_envs'] == 200 for n in cohorts)
    for group, name in zip(['original', 'near5'], videos):
        folder = base / 'verification' / name
        assert reports[name]['initial_state_rows'] == [0, 2, 76]
        media = json.loads((folder / 'media-verification.json').read_text())
        assert media['decoded_frames'] == 600 and media['fps'] == 30
        assert reports[name]['stable_full_all_endpoints'] == 2
        provenance[name]['media'] = media
        shutil.copy2(folder / 'policy.mp4', out / (prefix + '-' + group + '-preset3-no-text-failures-retained.mp4'))
        shutil.copy2(folder / 'preview.png', out / (prefix + '-' + group + '-preview.png'))
        paths.append(folder / 'media-verification.json')

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    fields = [('first_cycle_strict', 'First cycle stable', '#238b8e'),
              ('stable_full_all_endpoints', 'Every endpoint + full stability', '#d47f28')]
    for i, (field, label, color) in enumerate(fields):
        values = [reports[n][field] for n in cohorts]
        bars = axes[0].bar(np.arange(3) + (i - .5) * .34, values, .32, label=label, color=color)
        axes[0].bar_label(bars, fontsize=9, padding=3)
    axes[0].set_xticks([0, 1, 2], ['Original CP10', 'Matched near 0.1', 'Matched near 5'])
    axes[0].set_ylim(0, 222)
    axes[0].set_ylabel('Trials / 200')
    axes[0].set_title('Fresh seed 20261025; 5-second commands')
    axes[0].legend(loc='lower left', fontsize=8)
    matched = [reports[n]['records'] for n in cohorts[1:]]
    paired = dict(both=0, near5_only=0, near01_only=0, neither=0)
    for low, high in zip(*matched):
        assert low['env'] == high['env']
        a, b = low['stable_full_all_endpoints'], high['stable_full_all_endpoints']
        paired['both' if a and b else 'near5_only' if b else 'near01_only' if a else 'neither'] += 1
    bars = axes[1].bar(range(4), list(paired.values()), color=['#238b8e', '#d47f28', '#8c80a5', '#a9adb2'])
    axes[1].bar_label(bars, padding=3)
    axes[1].set_xticks(range(4), ['Both', 'Near 5 only', 'Near 0.1 only', 'Neither'])
    axes[1].set_ylim(0, max(paired.values()) * 1.18 + 1)
    axes[1].set_ylabel('Paired trials / 200')
    axes[1].set_title('Matched reward pair: joint criterion')
    for ax in axes:
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .025, 'Same nominal grasp with fresh reset perturbations; one training seed. '
             'No new-grasp or geometry claim.\nJoint criterion: all command tails within 2 mm for 0.3 s, '
             'base drift <10 mm / rotation <0.25 rad throughout 20 s, alive and finite.', fontsize=8.5)
    fig.tight_layout(rect=[0, .1, 1, 1])
    fig.savefig(out / (prefix + '-fresh200-matched-comparison.png'), dpi=160)
    plt.close(fig)

    text = '''# Wuji 近目标奖励 CP10：独立扰动评估

|策略|首次完整开合且稳定|全20秒联合成功|
|---|---:|---:|
|原始定时CP10|195/200|85/200|
|随机2/5秒，近目标系数0.1，CP10|189/200|79/200|
|随机2/5秒，近目标系数5，CP10|200/200|170/200|

下两行是匹配实验：相同原始CP10初始化、新Adam、seed20261023、5120环境、horizon32、
初始学习率2e-5及adaptive KL、相同完整初始化扰动、官方Wuji关节增益和armature。
唯一指定训练差别是近目标高斯奖励系数0.1或5，首次到位奖励50不变。
与原始CP10比较时还存在训练时长、指令时长分布等差异，不能当作纯奖励单变量对照。

评估在冻结CP10之后生成seed20261025的200个新扰动，三组使用相同初态。
刀具为147×19×11mm，滑块目标0/40mm，PhysX及ArtBot手部几何，滑块阻尼0.3。
每5秒由外部时钟切换指令，到位状态不触发切换。联合成功要求20秒内所有指令末尾0.3秒
均保持在目标±2mm，且刀柄全程位移<10mm、旋转<0.25rad，存活且数值有效。
stable_full字段还要求首次完整开合，不能将其理解为单纯静态持物。
全部600条测试记录和视频的6条记录都包含在provenance中，无失败删除。

两段无文字视频都使用评估前预定的0/2/76行，本机4090重新运行真实teacher。
每段20秒、30fps、1536×384。原始与near5视频都为首次稳定3/3、联合成功2/3；
两段视频各自的保持失败均保留。三个展示样本不是200次统计的代表性抽样，视频不计入200次分母。
teacher推理输出20个关节动作，不读取脚本轨迹；刀具依靠接触运动。

本批只验证同一个名义抓姿周围的扰动，尚不证明多抓姿、多几何或真机成功。
当前结论限于5秒协议与一个训练seed；2秒协议、第二训练seed和CP50另行报告。
teacher仍使用物体特权状态，不能直接当作部署student。
'''
    (out / (prefix + '-results.md')).write_text(text)
    for name in ['near-reward-pair-proposal.json', 'near-reward-fresh200-proposal.json',
                 'near-reward-video-proposal.json', 'audit-queue-near-reward-preset3-video.json']:
        paths.append(base / name)
    paths.extend([root / 'wuji_near_reward_suite.json', Path(__file__),
                  base / 'near-reward-fresh200-seed20261025/initial_states.npy'])
    for path in paths:
        assert path.is_file(), str(path)
    metadata = dict(source_sha256=sha(Path(__file__)), reports=reports, provenance=provenance,
                    matched_paired_joint=paired,
                    files={str(p.relative_to(root)): sha(p) for p in paths})
    (out / (prefix + '-all-trials-provenance.json')).write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')
    with zipfile.ZipFile(out / (prefix + '-evaluation-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, str(path.relative_to(root)))
    sums = [sha(p) + '  ' + p.name for p in sorted(out.iterdir()) if not p.name.endswith('SHA256SUMS.txt')]
    (out / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sums) + '\n')
    print(json.dumps(dict(output=str(out), paired=paired, assets=len(sums) + 1)))


if __name__ == '__main__':
    main()
