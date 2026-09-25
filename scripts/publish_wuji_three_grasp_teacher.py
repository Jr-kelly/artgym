"""Package all post-freeze trials, including fast long-rollout failures."""
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
from scripts.monitor_wuji_checkpoints import policy_snapshot
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    out = base / 'release-three-grasp-teacher-20260922'
    out.mkdir(exist_ok=False)
    evidence = out / 'evidence'
    evidence.mkdir()
    prefix = 'wuji-knife-three-grasp-teacher-20260922'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    checkpoint = base / 'frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth'
    model_sha = '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
    assert sha(checkpoint) == model_sha
    reports, sources, curves = {}, {}, {}
    score_keys = ['active', 'slider', 'goal', 'drift', 'rotation', 'fall', 'invalid']
    for duration in [20, 60]:
        for seconds in [2, 5]:
            name = 'bridge3-functionalinit-cp25-fresh632-seed56-%ds-timed%dseconds' % (duration, seconds)
            folder = base / 'verification' / name
            status = json.loads((folder/'status.json').read_text())
            assert status['status'] == 'completed' and status['returncode'] == 0
            report = json.loads((folder/'report.json').read_text())
            assert report['checkpoint_sha256'] == model_sha and report['num_envs'] == 632
            with np.load(folder/'trace.npz') as loaded:
                trace = {k: loaded[k] for k in score_keys}
            rescored = score_timed_trace(trace, seconds*30, 9, duration*30)
            assert all(rescored[k] == report[k] for k in ['records', 'alive_full', 'stable_full_all_endpoints'])
            reports['%d/%d' % (duration, seconds)] = report
            np.savez_compressed(evidence/(name+'-metric-trace.npz'), **trace)
            sources[str((folder/'trace.npz').relative_to(root))] = sha(folder/'trace.npz')
            for file in ['status.json', 'report.json', 'config.yaml', 'source.py', 'source_metrics.py']:
                p = folder/file
                sources[str(p.relative_to(root))] = sha(p)
                shutil.copy2(p, evidence/(name+'-'+file))
            if duration == 60:
                curves[seconds] = [trace['active'][:, a:a+200].mean(axis=1) for a in [0, 200, 400]]
    assert len({r['initial_states_sha256'] for r in reports.values()}) == 1
    splits = [(0, 200), (200, 400), (400, 600), (600, 632)]
    counts = {key: [sum(bool(row['stable_full_all_endpoints']) for row in report['records'][a:b]) for a,b in splits]
              for key, report in reports.items()}
    assert counts == {'20/2': [198, 199, 196, 0], '20/5': [195, 200, 199, 0],
                      '60/2': [195, 124, 51, 0], '60/5': [189, 196, 192, 0]}
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8))
    labels = ['Source grasp', 'Train row 16', 'Train row 15', 'Held-out grasp']
    for column, seconds in enumerate([2, 5]):
        ax = axes[0, column]
        for i, duration in enumerate([20, 60]):
            values = counts['%d/%d' % (duration, seconds)]
            denominators = np.array([200, 200, 200, 32])
            bars = ax.bar(np.arange(4)+(i-.5)*.36, np.array(values)/denominators*100, .34, label='%d s rollout' % duration)
            ax.bar_label(bars, labels=['%d/%d' % (n,d) for n,d in zip(values, denominators)], fontsize=8, padding=3)
        ax.set(xticks=np.arange(4), xticklabels=labels, ylim=(0, 116), ylabel='Joint success (%)', title='%d s fixed command duration' % seconds)
        ax.tick_params(axis='x', labelsize=8)
        ax.legend(loc='upper right', fontsize=8)
        for i, line in enumerate(curves[seconds]):
            axes[1, column].plot((np.arange(len(line))+1)/30, line*100, label=labels[i])
        axes[1, column].axvline(20, color='gray', linestyle='--', linewidth=1, label='Training episode limit')
        axes[1, column].set(xlabel='Time (s)', ylabel='Active trials (%)', ylim=(0, 105), title='Survival during 60 s rollout')
        axes[1, column].legend(fontsize=8, loc='lower left')
    for ax in axes.flat:
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('One frozen Wuji teacher: three trained grasps, new reset perturbations', fontsize=13)
    fig.text(.02, .014, 'Model frozen before generating 200 perturbations per trained grasp; no outcome filtering. Held-out 32-state cohort is reused development data.\nJoint: all command tails within 2 mm for 0.3 s; body drift <10 mm / angle <0.25 rad, alive and finite. Privileged teacher simulation only.', fontsize=8)
    fig.tight_layout(rect=[0, .065, 1, .96])
    fig.savefig(out/(prefix+'-all-trials-and-duration-limits.png'), dpi=165)
    plt.close(fig)

    videos = {}
    for duration in [20, 60]:
        name = 'bridge3-functionalinit-cp25-three-grasps-video-%ds-timed2seconds' % duration
        folder = base/'verification'/name
        status = json.loads((folder/'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        report = json.loads((folder/'report.json').read_text())
        assert report['initial_state_rows'] == [0, 200, 400]
        assert report['checkpoint_sha256'] == model_sha
        with np.load(folder/'trace.npz') as loaded:
            trace = {k: loaded[k] for k in score_keys}
        rescored = score_timed_trace(trace, 60, 9, duration*30)
        assert all(rescored[k] == report[k] for k in ['records', 'alive_full', 'stable_full_all_endpoints'])
        movie = out/(prefix+'-%ds-fast-commands-no-text.mp4' % duration)
        shutil.copy2(folder/'policy.mp4', movie)
        reader = imageio.get_reader(movie)
        count = 0
        for frame in reader:
            assert frame.shape == (384, 1536, 3)
            if duration == 20 and count == 300:
                imageio.imwrite(out/(prefix+'-frame-at-10seconds.png'), frame)
            count += 1
        reader.close()
        assert count == duration*30
        videos[str(duration)] = dict(report=report, frames=count, sha256=sha(movie))
        np.savez_compressed(evidence/(name+'-metric-trace.npz'), **trace)
        for file in ['status.json', 'report.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            shutil.copy2(folder/file, evidence/(name+'-'+file))
    snapshot = policy_snapshot(checkpoint, evidence/'policy', 25)
    # This is a byte-identical model/normalizer extraction, no quantization.
    import torch
    original = torch.load(checkpoint, map_location='cpu', weights_only=False)
    extracted = torch.load(snapshot['policy_checkpoint'], map_location='cpu', weights_only=False)
    assert original[0]['model'].keys() == extracted[0]['model'].keys()
    assert all(torch.equal(value, extracted[0]['model'][key]) for key,value in original[0]['model'].items())
    policy_file = out/(prefix+'-policy-only.pth')
    shutil.copy2(snapshot['policy_checkpoint'], policy_file)
    for package in [base/'bridge3-fresh200-each-seed20261056', checkpoint.parent]:
        for p in package.iterdir():
            if p.suffix in ['.npy', '.json']:
                shutil.copy2(p, evidence/(package.name+'-'+p.name))
    for p in [base/'bridge3-video-proposal.json', base/'bridge3-dataset-manifest.json',
              base/'diagnostics/bridge3-cp25-long60-failure-breakdown.json', Path(__file__)]:
        shutil.copy2(p, evidence/p.name)
    manifest = json.loads((base/'bridge3-dataset-manifest.json').read_text())
    for name, digest in manifest['artifact_sha256'].items():
        p = root/name
        assert sha(p) == digest
        destination = evidence/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, destination)
    provenance = dict(scope=__doc__, counts=counts, reports=reports, videos=videos,
                      source_checkpoint_sha256=model_sha, policy_only_sha256=sha(policy_file),
                      policy_model_and_normalizers_identical=True, original_file_sha256=sources,
                      selection=json.loads((base/'bridge3-video-proposal.json').read_text()))
    (out/(prefix+'-all-trials-provenance.json')).write_text(json.dumps(provenance, indent=2)+'\n')
    summary = '''# 同一个 Wuji teacher 的三抓姿验证

这是强化学习teacher的真实PhysX执行，没有脚本关节轨迹、物体轨迹驱动或外力辅助。刀具为约147×19×11mm（含滑块），沿用实际检查过的Wuji官方执行器参数参考；仍未做硬件标定。

CP25在已有开发集被选中后冻结，随后才生成每种训练抓姿200个新扰动，共600个。位置每轴±0.5mm、关节±0.01rad、旋转向量每轴±0.5°；无结果筛选。另一个未训练抓姿的32个已有开发初态保留为失败控制，不冒充新盲测。新扰动不等于600种新抓姿。

|执行协议|原抓姿|训练row16|训练row15|未训练抓姿|
|---|---:|---:|---:|---:|
|20秒，每2秒切换|198/200|199/200|196/200|0/32|
|20秒，每5秒切换|195/200|200/200|199/200|0/32|
|60秒，每2秒切换|195/200|124/200|51/200|0/32|
|60秒，每5秒切换|189/200|196/200|192/200|0/32|

联合成功要求每条指令末尾0.3秒在±2mm内，全程刀身漂移小于10mm、旋转小于0.25rad，且有限、存活。20秒训练回合不能保证快速长时控制：第三抓姿60秒快速协议仅59/200存活。慢速成功不覆盖快速失败。四份全部632行记录及评分轨迹均收入ZIP。

两段无字视频从左至右是原抓姿、row16、row15，各取新初态的第一行（总队列0/200/400）。选取发生在汇总后；视频用三个环境重新仿真，不增加独立评估样本数，批量变化可能改变结果。20秒与60秒文件用于展示短时能力及持续操作限制，具体重跑成绩见provenance。

policy-only.pth从被评估的完整CP25仅提取模型、归一化统计和计数；逐张量完全相同，未重新训练或量化。源CP及发布CP各自SHA256均已记录。它使用当前物体真值等特权观测，是teacher，不能直接当真机student部署。
'''
    (out/(prefix+'-results.md')).write_text(summary)
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(evidence.rglob('*')):
            if p.is_file() and 'policy' not in p.relative_to(evidence).parts:
                archive.write(p, str(p.relative_to(evidence)))
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(out.iterdir()) if p.is_file())+'\n')
    print(json.dumps(dict(output=str(out), assets=len([p for p in out.iterdir() if p.is_file()]), videos={k:v['report']['stable_full_all_endpoints'] for k,v in videos.items()})))


if __name__ == '__main__':
    main()
