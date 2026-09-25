"""Package paired two-grasp retention and exact command-delay sensitivity."""
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
    output = base / 'release-bridge-and-latency-20260922'
    output.mkdir(exist_ok=False)
    evidence = output / 'evidence'
    evidence.mkdir()
    prefix = 'wuji-knife-bridge-and-latency-20260922'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    cases = [('%s-cp50-paired-fresh400-plus-heldout32-timed%dseconds' % (policy, t), t, 600)
             for policy in ['bridge2', 'functional20'] for t in [2, 5]]
    cases += [('horizon60-cp100-command-delay%d-perturb100-timed%dseconds-transport-v3' % (delay, t), t, 600)
              for delay in [0, 1, 2] for t in [2, 5]]
    cases += [('horizon60-cp100-fresh100-seed39-extended60-timed%dseconds' % t, t, 1800) for t in [2, 3, 5]]
    video_name = 'bridge2-cp50-two-grasps-first3each-video-timed2seconds'
    cases.append((video_name, 2, 600))
    reports, identities = {}, {}
    for name, seconds, steps in cases:
        folder = base / 'verification' / name
        status = json.loads((folder / 'status.json').read_text())
        report = json.loads((folder / 'report.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        with np.load(folder / 'trace.npz') as source:
            trace = {k: source[k] for k in ['active', 'slider', 'goal', 'drift', 'rotation', 'fall', 'invalid']}
        scored = score_timed_trace(trace, seconds * 30, 9, steps)
        assert all(scored[k] == report[k] for k in ['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints', 'alive_full', 'records'])
        np.savez_compressed(evidence / (name + '-metric-trace.npz'), **trace)
        for filename in ['status.json', 'report.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            source = folder / filename
            shutil.copy2(source, evidence / (name + '-' + filename))
            identities[str(source.relative_to(root))] = sha(source)
        identities[str((folder / 'trace.npz').relative_to(root))] = sha(folder / 'trace.npz')
        if 'transport-v3' in name:
            latency = json.loads((folder / 'command-force-report.json').read_text())
            assert latency['target_delay_verified_exactly'] and not latency['force_instrumentation_enabled']
            assert latency['model_before'] == latency['model_after']
            assert latency['checkpoint_sha256'] == report['checkpoint_sha256']
            assert latency['initial_states_sha256'] == report['initial_states_sha256']
            with np.load(folder / 'command_force_trace.npz') as data:
                delay = latency['delay_steps']
                actual, emitted = data['physical_target'], data['emitted_target']
                assert np.array_equal(actual[delay:], emitted[:-delay] if delay else emitted)
                np.savez_compressed(evidence / (name + '-command-trace.npz'),
                                    physical_target=actual, emitted_target=emitted, active=data['active'])
            for filename in ['command-force-report.json', 'latency_probe_source.py']:
                shutil.copy2(folder / filename, evidence / (name + '-' + filename))
            identities[str((folder / 'command_force_trace.npz').relative_to(root))] = sha(folder / 'command_force_trace.npz')
        reports[name] = report
    paired = [reports[name] for name, _, _ in cases[:4]]
    assert len({r['initial_states_sha256'] for r in paired}) == 1
    split_counts = {}
    for name, _, _ in cases[:4]:
        report = reports[name]
        split_counts[name] = {}
        for split, start, stop in [('source', 0, 200), ('novel_train', 200, 400), ('heldout', 400, 432)]:
            records = report['records'][start:stop]
            split_counts[name][split] = dict(n=len(records), **{
                key: sum(int(row[key]) for row in records)
                for key in ['first_cycle_strict', 'stable_full_all_endpoints', 'alive_full']})
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.7))
    for ax, split, title in zip(axes[:2], ['source', 'novel_train'], ['Original training grasp', 'Added training grasp 16']):
        for i, policy in enumerate(['functional20', 'bridge2']):
            counts = [split_counts['%s-cp50-paired-fresh400-plus-heldout32-timed%dseconds' % (policy, t)][split]['stable_full_all_endpoints'] for t in [2, 5]]
            bars = ax.bar(np.arange(2) + (i - .5) * .34, counts, .32, label=policy)
            ax.bar_label(bars, padding=3, fontsize=9)
        ax.set(title=title + '\nSame fresh 200 physical states', xticks=[0, 1], xticklabels=['2 s commands', '5 s commands'], ylim=(0, 230), ylabel='Joint successes / 200')
        ax.legend(fontsize=8, loc='upper left')
    for t, marker in [(2, 'o'), (5, 's')]:
        values = [reports['horizon60-cp100-command-delay%d-perturb100-timed%dseconds-transport-v3' % (d, t)]['stable_full_all_endpoints'] for d in [0, 1, 2]]
        axes[2].plot([0, 33.33, 66.67], values, marker=marker, label='%d s commands' % t)
        for x, y in zip([0, 33.33, 66.67], values):
            axes[2].annotate(str(y), (x, y), xytext=(0, 5 if t == 5 else -13), textcoords='offset points', ha='center', fontsize=9)
    axes[2].set(title='Single-grasp horizon60 teacher CP100\nSame 100 states, 20 s evaluation', xlabel='Added command delay (ms)', ylabel='Joint successes / 100', ylim=(65, 108), xticks=[0, 33.33, 66.67])
    axes[2].legend(fontsize=8, loc='lower left')
    for ax in axes:
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True); ax.spines[['top', 'right']].set_visible(False)
    fig.text(.015, .02, 'All 32 held-out-grasp perturbations fail in both paired policies. Two training grasps are not broad generalization.\nJoint: all command tails within 2 mm for 0.3 s; base drift <10 mm, rotation <0.25 rad, alive and finite. Simulation only.', fontsize=8)
    fig.tight_layout(rect=[0, .09, 1, 1])
    fig.savefig(output / (prefix + '-paired-retention-and-delay.png'), dpi=165)
    plt.close(fig)

    folder = base / 'verification' / video_name
    reader = imageio.get_reader(folder / 'policy.mp4')
    assert reader.get_meta_data()['fps'] == 30
    selected, count = {}, 0
    for index, frame in enumerate(reader):
        count += 1
        if index in [45, 59, 119, 299, 599]: selected[index] = frame
    reader.close()
    assert count == 600 and reports[video_name]['initial_state_rows'] == [0, 1, 2, 200, 201, 202]
    media = dict(decoded_frames=count, fps=30, seconds=20, rows=[0, 1, 2, 200, 201, 202],
                 video_sha256=sha(folder / 'policy.mp4'), text_overlays=False,
                 scope='Top row original grasp, bottom row training grasp16. First3 existing perturbations per grasp selected after aggregate evaluation. Same learned policy; no additional independent sample.')
    shutil.copy2(folder / 'policy.mp4', output / (prefix + '-two-grasps-same-policy-20seconds-no-text.mp4'))
    imageio.imwrite(output / (prefix + '-preview.png'), selected[45])
    imageio.imwrite(output / (prefix + '-sequence.png'), np.concatenate([selected[t] for t in [59, 119, 299, 599]], axis=0))
    (folder / 'media-verification.json').write_text(json.dumps(media, indent=2) + '\n')
    additions = [base / 'bridge2-fresh200-each-seeds41-42/manifest.json', base / 'bridge2-fresh200-each-seeds41-42/mixed432.npy',
                 base / 'bridge2-video-and-long-proposal.json', base / 'command-latency-proposal.json',
                 base / 'action-distillation-pair-proposal.json', Path(__file__)]
    for name in ['action-distillation-runtime', 'action-distillation-runtime-cudnn-v2', 'command-latency-first-attempt', 'command-latency-sensor-v2-attempt']:
        additions.extend(p for p in (base / 'diagnostics' / name).rglob('*') if p.is_file() and p.suffix in ['.json', '.py', '.log'])
    for source in additions:
        identities[str(source.relative_to(root))] = sha(source)
        shutil.copy2(source, evidence / str(source.relative_to(root)).replace('/', '__'))
    (output / (prefix + '-all-trials-provenance.json')).write_text(json.dumps(dict(reports=reports, paired_splits=split_counts, media=media, original_file_sha256=identities), indent=2) + '\n')
    with zipfile.ZipFile(output / (prefix + '-metric-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(evidence.iterdir()): archive.write(source, source.name)
    (output / (prefix + '-results.md')).write_text('''# 两抓姿共同成功与动作传输延迟

同一个冻结的 Wuji teacher CP50 控制两种训练抓姿，官方关节增益/armature/力矩限制、ArtBot 接触几何、147×19×11mm 几何基元刀具、PhysX 接触仿真。没有脚本控制刀具。滑块阻尼0.3尚未实物标定。

|冻结策略，同批400新扰动，20秒评估|原抓姿2秒|新增抓姿2秒|原抓姿5秒|新增抓姿5秒|
|---|---:|---:|---:|---:|
|20抓姿适应CP50|46/200|186/200|190/200|184/200|
|原抓姿+第16行两抓姿课程CP50|199/200|186/200|198/200|198/200|

两模型冻结后生成seed41/42各200初态，无结果筛选。独立扰动不是新抓姿；各协议复用相同初态。额外留出的一个测试抓姿32个既有扰动，在两模型和两协议上均0首轮/0联合/0存活。课程策略解决了当前两训练抓姿的能力保留，尚未证明未见抓姿、未见几何或真机成功。两种训练的数据和学习率不同，这张表是策略比较，不是单变量消融。

联合要求每条指令最后0.3秒在±2mm内，全程刀身漂移<10mm、旋转<0.25rad，存活且数值有限。换向只按外部时钟，不因到位提前切换。

无字视频上排是原抓姿前三个扰动，下排是新增抓姿前三个扰动。六个均通过20秒联合。它是汇总后选定行的小批真实物理重跑，非新增盲测，不加入400分母。完整600帧，不裁剪失败片段；这六行恰好全部成功，所有432行失败证据保留于ZIP。

另一份单抓姿长回合teacher CP100，在同100初态的20秒延迟敏感性：新增动作延迟0/1/2帧，2秒指令联合100/94/84，5秒为100/98/98。30Hz下每帧约33.3ms。延迟施加到策略发出的绝对手指目标，保留策略已发目标历史；逐步核对实际目标确实等于延迟后的目标。未叠加观测延迟或SDK滤波，不能据此声称真机鲁棒。

上述长回合teacher在冻结后新100初态的60秒复核也随附：2/3/5秒协议联合83/96/100，存活97/99/100。3秒时长未用于训练。不同指令时长对应不同循环数，不唯一隔离频率因素。

力传感器两次尝试无效并保留原日志；当前延迟结果不含有效力矩测量。实际actor的effort/Kp/Kv/armature已核对，但配置一致不等于硬件电流/力矩标定。动作蒸馏首版native LSTM检查因1.45e-4的动作差异失败，修正版仅为零dropout的cuDNN RNN开启反传缓冲，教师动作误差0、学生梯度非零、模型/归一化与实时RNN不变，256次物理转移检查通过。新动作损失系数10的500更新对照已启动，不能提前称其闭环成功。

ZIP重算核对14项评估的全部逐样本评分，保留失败和原始文件哈希。Goal仍在继续：多抓姿长期保持、更多几何、student闭环、延迟适应及实际控制标定。
''')
    (output / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sha(p) + '  ' + p.name for p in sorted(output.iterdir()) if p.is_file()) + '\n')
    print(json.dumps(dict(output=str(output), evaluations=len(cases), assets=len([p for p in output.iterdir() if p.is_file()]))))


if __name__ == '__main__':
    main()
