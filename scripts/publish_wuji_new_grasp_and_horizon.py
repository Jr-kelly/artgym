"""Build failure-preserving evidence for a learned second grasp and final horizons."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    out = base / 'release-new-grasp-and-final-horizon-20260922'
    out.mkdir(exist_ok=False)
    prefix = 'wuji-knife-new-grasp-and-final-horizon-20260922'
    evidence = out / 'evidence'
    evidence.mkdir()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    cases = [('functional16-%s-cp50-fresh200-seed38-timed%dseconds' % (identity, seconds), seconds, 600)
             for identity in ['adapted', 'original'] for seconds in [2, 5]]
    cases += [('functional20-adapted-cp50-source-retention100-timed%dseconds' % seconds, seconds, 600) for seconds in [2, 5]]
    cases += [('wuji_horizon%d_near5_cp50_seed33_v1-cp%d-extended60-timed2seconds-seed30' % (duration, cp), 2, 1800)
              for duration in [20, 60] for cp in [25, 100]]
    cases += [('student-near5cp50-teacher500-cp200-timed%dseconds-perturb100' % seconds, seconds, 600) for seconds in [2, 5]]
    video_name = 'functional16-adapted-cp50-first3-video-timed2seconds'
    cases.append((video_name, 2, 600))
    reports, files = {}, {}
    for name, seconds, steps in cases:
        folder = base / 'verification' / name
        status = json.loads((folder / 'status.json').read_text())
        report = json.loads((folder / 'report.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        with np.load(folder / 'trace.npz') as full:
            trace = {k: full[k] for k in ['active', 'slider', 'goal', 'drift', 'rotation', 'fall', 'invalid']}
        metrics = score_timed_trace(trace, seconds * 30, 9, steps)
        assert all(report[k] == metrics[k] for k in ['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints', 'alive_full'])
        np.savez_compressed(evidence / (name + '-metric-trace.npz'), **trace)
        for field in ['report.json', 'status.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            source = folder / field
            shutil.copy2(source, evidence / (name + '-' + field))
            files[str(source.relative_to(root))] = sha(source)
        files[str((folder / 'trace.npz').relative_to(root))] = sha(folder / 'trace.npz')
        reports[name] = report
    assert len({reports[name]['initial_states_sha256'] for name, _, _ in cases[:4]}) == 1
    assert [reports['functional16-adapted-cp50-fresh200-seed38-timed%dseconds' % t]['stable_full_all_endpoints'] for t in [2, 5]] == [177, 183]
    assert [reports['functional16-original-cp50-fresh200-seed38-timed%dseconds' % t]['stable_full_all_endpoints'] for t in [2, 5]] == [0, 19]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for i, identity in enumerate(['original', 'adapted']):
        y = [reports['functional16-%s-cp50-fresh200-seed38-timed%dseconds' % (identity, t)]['stable_full_all_endpoints'] for t in [2, 5]]
        bars = axes[0].bar(np.arange(2)+(i-.5)*.34, y, .32, label=identity)
        axes[0].bar_label(bars, padding=3)
    axes[0].set(title='Training grasp 16: paired fresh 200\nSame physical initial states', ylabel='Joint successes / 200',
                xticks=[0, 1], xticklabels=['2 s commands', '5 s commands'], ylim=(0, 225))
    axes[0].legend(fontsize=8, loc='upper left')
    bars = axes[1].bar(['2 s', '5 s'], [reports['functional20-adapted-cp50-source-retention100-timed%dseconds' % t]['stable_full_all_endpoints'] for t in [2, 5]], color='#d78839')
    axes[1].bar_label(bars, padding=3)
    axes[1].set(title='Adapted policy on original source grasp\nSeparate existing 100 states', ylabel='Joint successes / 100', ylim=(0, 115))
    for duration, color in [(20, '#557fad'), (60, '#b87592')]:
        y = [reports['wuji_horizon%d_near5_cp50_seed33_v1-cp%d-extended60-timed2seconds-seed30' % (duration, cp)]['stable_full_all_endpoints'] for cp in [25, 100]]
        axes[2].plot([25, 100], y, 'o-', color=color, label='%d s training episodes' % duration)
        for x, value in zip([25, 100], y):
            axes[2].annotate(str(value), (x, value), xytext=(0, 7), textcoords='offset points', ha='center')
    axes[2].set(title='Matched continuation, final CP100\n60 s evaluation, 2 s commands', xlabel='Additional training epochs', ylabel='Joint successes / 100', ylim=(0, 115), xticks=[25, 100])
    axes[2].legend(fontsize=8, loc='lower left')
    for ax in axes:
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True); ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .018, 'Grasp 16 was seen during adaptation; this is new perturbation validation, not unseen-grasp generalization.\nJoint requires all 0.3 s command tails within 2 mm and base drift <10 mm / rotation <0.25 rad throughout, alive and finite.', fontsize=8)
    fig.tight_layout(rect=[0, .09, 1, 1])
    fig.savefig(out / (prefix + '-paired-grasp-transfer-retention-and-horizon.png'), dpi=165)
    plt.close(fig)
    folder = base / 'verification' / video_name
    reader = imageio.get_reader(folder / 'policy.mp4')
    metadata = reader.get_meta_data()
    count, selected = 0, {}
    for i, frame in enumerate(reader):
        count += 1
        if i in [45, 59, 149, 299, 599]: selected[i] = frame.copy()
    reader.close()
    assert count == 600 and metadata['fps'] == 30
    assert reports[video_name]['initial_state_rows'] == [0, 1, 2]
    media = dict(decoded_frames=count, fps=30, duration_seconds=20, text_overlays=False,
                 video_sha256=sha(folder / 'policy.mp4'), rows=[0, 1, 2],
                 scope='First three existing fresh200 states after aggregate evaluation; not an additional independent sample.')
    (folder / 'media-verification.json').write_text(json.dumps(media, indent=2)+'\n')
    shutil.copy2(folder / 'policy.mp4', out / (prefix + '-grasp16-first3-20seconds-no-text.mp4'))
    imageio.imwrite(out / (prefix + '-preview.png'), selected[45])
    imageio.imwrite(out / (prefix + '-sequence.png'), np.concatenate([selected[i] for i in [59, 149, 299, 599]], axis=0))
    for p in [base / 'functional16-fresh200-seed20261038/initial_states.npy',
              base / 'functional16-fresh200-seed20261038/manifest.json',
              base / 'functional16-validation-proposal.json', base / 'functional16-video-proposal.json',
              base / 'bridge2-evaluation-states/source.npy',
              base / 'frozen-candidates/teacher-functional20-hemisphere-seed34-cp50/manifest.json',
              base / 'frozen-candidates/teacher-horizon60-seed33-cp100/manifest.json',
              folder / 'media-verification.json', Path(__file__)]:
        files[str(p.relative_to(root))] = sha(p)
        shutil.copy2(p, evidence / str(p.relative_to(root)).replace('/', '__'))
    (out / (prefix + '-all-trials-provenance.json')).write_text(json.dumps(dict(reports=reports, media=media, original_file_sha256=files), indent=2)+'\n')
    with zipfile.ZipFile(out / (prefix + '-metric-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(evidence.iterdir()): archive.write(path, path.name)
    (out / (prefix + '-results.md')).write_text('''# 第二抓姿与长回合最终结果

均为Wuji/PhysX学习策略，官方关节参数、ArtBot几何、147×19×11mm刀具。物体由接触带动，非预设动作；尚无真机标定或成功证据。
联合成功要求各指令末尾0.3秒在±2mm内，全程刀柄漂移<10mm、旋转<0.25rad，存活且数值有效。

|同一批新200初态，训练见过的第16抓姿|2秒指令|5秒指令|
|---|---:|---:|
|原冻结CP50|0/200|19/200|
|20抓姿适应后的冻结CP50|177/200|183/200|

这批初态在两份模型冻结后生成，seed20261038，每轴位置±0.5mm、关节±0.01rad、旋转向量每轴±0.5度；无按成功过滤。
适应后的首轮200/200（两协议），严格首轮194/196，全部存活。原模型首次196/195、严格180/123、全部存活，主要差距在持续稳定保持。
它是第二种训练见过的抓姿，不是未见抓姿。整体20抓姿的80开发扰动仅4次联合，全部来自此行；1个测试抓姿32扰动仍0。

同一适应策略回到另一批100个原成功抓姿初态，联合仅26/100（2秒）、91/100（5秒），两协议首轮/严格/存活均99。
新抓姿提升与原能力损失并存，继续开展原抓姿+第16行的两抓姿课程；不能只发布新抓姿的高分。

无字20秒视频是新200初态的前三行在本机的小批物理重跑，3/3联合；选择在汇总之后，不当作新测试或代表性随机抽样，不加入200分母。
生成刀具资产以几何基元表示；该视频不是高细节真实刀具模型。序列为59/149/299/599帧，完整视频600帧，未裁掉失败片段。

长回合配对结果：相同100初态、60秒快速测试，20/60秒训练回合在CP25联合64/48，在最终CP100变为44/87。
配对使用同源CP50、新Adam、相同seed、5120环境、horizon32、常数LR1e-5、100轮，仅训练回合长度不同。
因此早期负结果不能替代最终结论。最终支持长回合在这次配对中的收益，不推广为普适结论；60秒训练CP100已冻结并另建新100初态复核队列。

student CP200的独立100次闭环也随附：2/5秒首轮91/97、严格90/87、联合7/9，全部存活；仍不足以可靠部署。
ZIP保留13项评估的全部评分字段轨迹并重算核对，包含所有失败。原始完整关节/接触轨迹的SHA256记录在provenance中。
''')
    (out / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(out.iterdir()) if p.is_file())+'\n')
    print(json.dumps(dict(output=str(out), evaluations=len(cases), assets=len([p for p in out.iterdir() if p.is_file()]))))


if __name__ == '__main__':
    main()
