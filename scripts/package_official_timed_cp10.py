"""Package frozen teacher evidence, failed trials included, for the authorized Release."""
import hashlib
import json
from pathlib import Path
import shutil

import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    goal = root/'runs/wuji-goal'
    out = goal/'release-official-timed-cp10-20260922-0600'
    out.mkdir(exist_ok=False)
    prefix = 'wuji-knife-official-timed-cp10-20260922'
    names = [f'official-timed2-cp10-fresh-seed{seed}-timed{period}seconds'
             for seed in [16729, 17839] for period in [2, 5]]
    names += [f'official-timed2-cp{cp}-timed{period}seconds-perturb100'
              for cp in [10, 25, 50, 100] for period in [2, 5]]
    names += [f'official-arrival-cp{cp}-timed{period}seconds-perturb100'
              for cp in [10, 25] for period in [2, 5]]
    video_name = 'official-timed-cp10-2seconds-preset3-video'
    names.append(video_name)
    reports, provenance = {}, {}
    for name in names:
        directory = goal/'verification'/name
        status = json.loads((directory/'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0, name
        reports[name] = json.loads((directory/'report.json').read_text())
        provenance[name] = dict(report=reports[name], status=status,
                               report_sha256=sha(directory/'report.json'))
        correction = directory/'provenance-correction.json'
        if correction.exists():
            provenance[name]['source_identity_correction'] = json.loads(correction.read_text())
    checkpoint_hash = '38903d492ee7d6c372633ce5584c6ea7703034362f3bab8928e31eda599e977e'
    for name in names[:4] + [video_name]:
        assert reports[name]['checkpoint_sha256'] == checkpoint_hash
    video = goal/'verification'/video_name/'policy.mp4'
    reader = imageio.get_reader(str(video))
    media = reader.get_meta_data()
    media['decoded_frame_count'] = reader.count_frames()
    assert media['decoded_frame_count'] == 600 and media['fps'] == 30 and media['size'] == (1536, 384)
    media.pop('nframes', None)
    imageio.imwrite(out/(prefix+'-preview.png'), reader.get_data(45))
    reader.close()
    shutil.copy2(video, out/(prefix+'-three-trials-no-text-failure-retained.mp4'))
    metric_names = ['first_cycle_strict', 'all_endpoints_held', 'stable_full', 'stable_full_all_endpoints']
    aggregate = {}
    for period in [2, 5]:
        rows = [reports[f'official-timed2-cp10-fresh-seed{seed}-timed{period}seconds'] for seed in [16729,17839]]
        aggregate[period] = {key:sum(row[key] for row in rows) for key in metric_names+['num_envs']}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    labels = ['First stable\nopen + close', 'Every command\nendpoint held', 'Full 20 s\nbase stability', 'Endpoint +\nbase jointly']
    colors = ['#2c7fb8', '#f28e2b']
    for i, period in enumerate([2, 5]):
        vals = [aggregate[period][key]/2 for key in metric_names]
        bars = axes[0].bar(np.arange(4)+(i-.5)*.36, vals, .36, label=f'{period} s commands', color=colors[i])
        axes[0].bar_label(bars, labels=[f'{v:g}%' for v in vals], fontsize=8)
    axes[0].set(xticks=np.arange(4), xticklabels=labels, ylim=(0,112), ylabel='Trials (%)',
                title='Frozen CP10: 200 fresh perturbations per protocol')
    axes[0].legend(fontsize=8)
    cps = [10,25,50,100]
    for period,color in zip([2,5],colors):
        values = [reports[f'official-timed2-cp{cp}-timed{period}seconds-perturb100']['stable_full_all_endpoints'] for cp in cps]
        axes[1].plot(cps,values,'o-',color=color,label=f'Timed training, {period} s audit')
        controls = [reports[f'official-arrival-cp{cp}-timed{period}seconds-perturb100']['stable_full_all_endpoints'] for cp in [10,25]]
        axes[1].plot([10,25],controls,'s--',color=color,label=f'Arrival control, {period} s audit')
    axes[1].set(ylim=(0,100), xlabel='Additional teacher epoch', ylabel='Joint success / 100',
                title='Development results: later checkpoints can regress')
    axes[1].legend(fontsize=8)
    fig.suptitle('Official Wuji actuator parameters in PhysX; one nominal grasp, no hardware validation', fontsize=11)
    fig.savefig(out/(prefix+'-fresh-tests-and-later-regression.png'),dpi=170)
    plt.close(fig)
    failure_path = goal/'diagnostics/official-timed-late-holding-failures.json'
    failures = json.loads(failure_path.read_text())
    fig,axes = plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for cp in [10,25,50]:
        rows = failures['results'][f'official-timed2-cp{cp}-timed2seconds-perturb100']['rows']
        closing = [row for row in rows if row['command'] == 'close']
        axes[0].plot(range(1,6),[row['held'] for row in closing],'o-',label=f'CP{cp}')
        axes[1].plot(range(1,6),[row['end_error_median_mm'] for row in closing],'o-',label=f'CP{cp}')
    axes[0].set(ylim=(0,105),xlabel='Closing command',ylabel='Endpoint held / 100',title='Closing endpoints degrade despite reaching the target')
    axes[1].axhline(2,color='black',linestyle=':',label='2 mm tolerance')
    axes[1].set(xlabel='Closing command',ylabel='Signed final-window error (mm)',title='Positive closing error means reopening')
    for ax in axes: ax.legend()
    fig.savefig(out/(prefix+'-holding-failure-analysis.png'),dpi=170)
    plt.close(fig)
    result = dict(source_sha256=sha(Path(__file__)), checkpoint_sha256=checkpoint_hash,
                  media=media, reports=provenance, fresh_aggregate=aggregate,
                  failure_analysis=failures,
                  scope='Same nominal grasp, same 200 states reused across two protocols; one seed per training arm. PhysX simulation only.')
    (out/(prefix+'-provenance-and-all-trials.json')).write_text(json.dumps(result,indent=2)+'\n')
    text = '''# Wuji 官方执行器参数：定时开合 teacher CP10

这是学习策略在 PhysX 中驱动关节完成的操作。采用官方逐关节 Kp/Kv 和 armature，保留 ArtBot 几何和接触模型，不能视为真机或完整官方 MuJoCo 模型的验证。

固定 CP10（SHA256：`38903d492ee7d6c372633ce5584c6ea7703034362f3bab8928e31eda599e977e`）后，用预先声明的种子 16729/17839 生成各 100 个新扰动初态。2 秒和 5 秒协议复用这 200 个初态，不是 400 个独立初态，也不是新抓姿。

| 外部指令周期 | 首次稳定开合 | 所有指令末尾保持 | 全 20 秒刀身稳定 | 末尾保持且全程稳定 |
|---|---:|---:|---:|---:|
| 2 秒 | 198/200 | 138/200 | 188/200 | 132/200 |
| 5 秒 | 198/200 | 92/200 | 191/200 | 92/200 |

到位要求误差小于 2 mm 连续 9 个控制采样（0.3 秒）；末尾保持要求每个指令窗口最后 9 个采样都满足该阈值。刀身稳定要求整个 20 秒内平移小于 10 mm、转角小于 0.25 rad，且无掉落、无无效状态并完成首次开合。联合指标要求所有这些条件。

无字视频固定使用此前声明的初态行 0/2/76，20 秒、30 fps、1536×384，未换样。三个案例均完成所有目标、刀身全程稳定；前两个满足所有末尾保持，右侧第三个在后期三个关闭窗口保持失败。失败保留。本机 4090 的 3 环境录制与 H100 的 100 环境评估不是逐帧一致的复现。

开发集后期退化：定时 teacher CP10/25/50/100 的 2 秒联合成功为 63/58/0/3（每 100），5 秒为 51/37/5/27。CP50 关闭目标仍能到达，但随后重新打开；不能按训练奖励或训练轮数选择策略。

匹配到位切换对照 CP10 的 2 秒/5 秒联合成功为 54/49，CP25 为 17/39；定时组分别为 63/51 和 58/37。每组只有一个训练种子，5 秒协议也没有一致优势，不能将全部改善归因于切换时钟。

图片允许标注，视频不含文字。完整逐案例结果、源码身份校正、报告哈希和轨迹失败分析在 JSON 中。多抓姿、持续保持和 student 仍在改进，真机标定尚未完成。
'''
    (out/(prefix+'-results.md')).write_text(text)
    files=sorted(out.iterdir())
    (out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(f'{sha(p)}  {p.name}\n' for p in files))
    print(out)
    print(json.dumps(aggregate))


if __name__=='__main__':
    main()
