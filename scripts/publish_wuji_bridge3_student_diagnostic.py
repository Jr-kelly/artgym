"""Package early three-grasp student outcomes, counterfactual errors and failures."""
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

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base = ROOT/'runs/wuji-goal'
    output = base/'release-bridge3-student-diagnostic-20260922'
    evidence = output/'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    prefix = 'wuji-three-grasp-student-diagnostic-20260922'
    metric_keys = ['active', 'fall', 'invalid', 'slider', 'goal', 'drift', 'rotation']
    provenance = dict(scope=__doc__, outcomes=[], diagnostics=[], videos=[], source_files={})

    def collect(name):
        folder = base/'verification'/name
        status = json.loads((folder/'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        report = json.loads((folder/'report.json').read_text())
        with np.load(folder/'trace.npz') as data:
            trace = {k:data[k] for k in metric_keys}
        score = score_timed_trace(trace, report['protocol']['stage_steps'], 9, 600)
        assert score['records'] == report['records']
        for file in ['report.json', 'status.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            source = folder/file
            shutil.copy2(source, evidence/(name+'-'+file))
            provenance['source_files'][str(source.relative_to(ROOT))] = digest(source)
        np.savez_compressed(evidence/(name+'-metric-trace.npz'), **trace)
        provenance['source_files'][str((folder/'trace.npz').relative_to(ROOT))] = digest(folder/'trace.npz')
        return report

    results = {}
    for kind in ['pure', 'controller']:
        for cp in [100, 250]:
            for seconds in [2, 5]:
                name = 'student-bridge3cp25-%s1000-seed57-cp%d-mixed332-timed%dseconds' % (kind, cp, seconds)
                report = collect(name)
                counts = [sum(x['stable_full_all_endpoints'] for x in report['records'][i:i+100]) for i in [0,100,200,300]]
                alive = [sum(x['alive_full'] for x in report['records'][i:i+100]) for i in [0,100,200,300]]
                results[kind, cp, seconds] = counts
                provenance['outcomes'].append(dict(kind=kind, cp=cp, seconds=seconds, joint=counts, alive=alive,
                                                  denominators=[100,100,100,32], source=name))

    error_rows = []
    for driver in ['teacher', 'plain', 'controller']:
        name = 'bridge3-encoder-v2-%s-cp100-development72' % driver
        report = collect(name)
        folder = base/'verification'/name
        d = json.loads((folder/'encoder_report.json').read_text())
        assert d['driver'] == driver and d['num_envs'] == 72
        for file in ['encoder_report.json', 'encoder_error_trace.npz', 'probe_source.py']:
            shutil.copy2(folder/file, evidence/(name+'-'+file))
            provenance['source_files'][str((folder/file).relative_to(ROOT))] = digest(folder/file)
        aggregate = []
        for grasp in ['source', 'row16', 'row15']:
            for student in ['plain', 'controller']:
                selected = [x for x in d['summaries'] if x['grasp'] == grasp and x['student'] == student]
                count = sum(x['active_transitions'] for x in selected)
                row = dict(driver=driver, grasp=grasp, student=student, active_transitions=count,
                    **{k:sum(x[k]*x['active_transitions'] for x in selected if x[k] is not None)/max(count,1)
                       for k in ['latent_mse','thumb_step_error_mrad','support_action_mae']})
                aggregate.append(row)
                error_rows.append(row)
        provenance['diagnostics'].append(dict(driver=driver, joint=report['stable_full_all_endpoints'],
                                             alive=report['alive_full'], aggregate=aggregate))

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    labels = ['Original grasp', 'Training row16', 'Training row15']
    colors = ['#2877b9', '#de793d']
    for i, grasp in enumerate(['source', 'row16', 'row15']):
        ax = axes[0,i]
        for j, kind in enumerate(['pure','controller']):
            values = [results[kind,cp,sec][i] for cp,sec in [(100,2),(100,5),(250,2),(250,5)]]
            bars = ax.bar(np.arange(4)+(j-.5)*.34, values, .34, color=colors[j], label=['Plain','Controller inputs'][j])
            ax.bar_label(bars, fontsize=8)
        ax.set(xticks=np.arange(4), xticklabels=['CP100\n2 s','CP100\n5 s','CP250\n2 s','CP250\n5 s'],
               ylim=(0,108), ylabel='Joint success / 100', title=labels[i])
        ax.legend(fontsize=8)
        ax = axes[1,i]
        for j, student in enumerate(['plain','controller']):
            values = [next(x['thumb_step_error_mrad'] for x in error_rows
                           if x['grasp']==grasp and x['student']==student and x['driver']==driver)
                      for driver in ['teacher','plain','controller']]
            bars = ax.bar(np.arange(3)+(j-.5)*.34, values, .34, color=colors[j])
            ax.bar_label(bars, fmt='%.2f', fontsize=8)
        ax.set(xticks=np.arange(3), xticklabels=['Teacher\ndriver','Plain\ndriver','Controller\ndriver'],
               ylim=(0,5), ylabel='CP100 thumb step MAE (mrad)', title='Same incoming actor state, '+labels[i])
    for ax in axes.flat:
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='y', alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle('Wuji student: improving early checkpoints, persistent closed-loop gap', fontsize=14)
    fig.text(.018,.01,'Top: reused development states, 20 s; every command tail within 2 mm for 0.3 s, body drift <10 mm / angle <0.25 rad, alive. Held-out grasp: 0/32 throughout.\nBottom: CP100 diagnostics on 24 existing states per grasp; only the named driver advances physics. Errors averaged over active transitions; dropped trials shorten the denominator.\nDifferent input dimensions also alter initialization. Teacher-driven diagnostic success is not student success. No hardware validation.',fontsize=8)
    fig.tight_layout(rect=[0,.085,1,.96])
    fig.savefig(output/(prefix+'-outcomes-and-error-distribution.png'),dpi=160)
    plt.close(fig)

    readers = []
    for kind in ['pure','controller']:
        name = 'student-bridge3-%s-cp250-three-grasps-video-timed2seconds-localgraphics' % kind
        report = collect(name)
        assert report['initial_state_rows'] == [0,100,200]
        folder = base/'verification'/name
        reader = imageio.get_reader(folder/'policy.mp4')
        readers.append(reader)
        provenance['videos'].append(dict(kind=kind, joint=report['stable_full_all_endpoints'],
                                        alive=report['alive_full'], report=report, original_sha256=digest(folder/'policy.mp4')))
    movie = output/(prefix+'-cp250-plain-top-controller-bottom-no-text.mp4')
    try:
        with imageio.get_writer(movie,fps=30) as writer:
            for frame_index in range(600):
                frames = [reader.get_data(frame_index) for reader in readers]
                assert all(frame.shape == (384,1536,3) for frame in frames)
                frame = np.concatenate(frames,axis=0)
                writer.append_data(frame)
                if frame_index == 300:
                    imageio.imwrite(output/(prefix+'-frame-at-10seconds.png'),frame)
            for reader in readers:
                try:
                    reader.get_data(600)
                    raise AssertionError('Unexpected extra video frame')
                except IndexError:
                    pass
    finally:
        for reader in readers:
            reader.close()
    decoded = sum(1 for frame in imageio.get_reader(movie))
    assert decoded == 600
    provenance['combined_video'] = dict(frames=600, fps=30, shape=[768,1536,3], sha256=digest(movie), added_text=False)
    for name in ['student-bridge3-cp250-video-proposal.json', 'student-replay-pair-seed60-proposal.json',
                 'diagnostics/bridge3-encoder-cp100-diagnostic-v2/noninterference.json']:
        shutil.copy2(base/name,evidence/Path(name).name)
    for kind in ['pure','controller']:
        name = 'student-bridge3-%s-cp250-three-grasps-video-timed2seconds' % kind
        folder = base/'verification'/name
        assert json.loads((folder/'status.json').read_text())['returncode'] == -11
        for file in ['status.json','worker.log']:
            shutil.copy2(folder/file,evidence/(name+'-'+file))
    shutil.copy2(Path(__file__),evidence/Path(__file__).name)
    np.save(evidence/'development-mixed332.npy',np.load(base/'bridge3-evaluation-states/mixed332.npy'))
    (output/(prefix+'-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    (output/(prefix+'-README.md')).write_text('''# Wuji 三抓姿 student 的早期进展与闭环差距

两组使用同一冻结三抓姿teacher CP25，1024环境、50帧历史、纯latent MSE、Adam2e-4、全student动作。普通输入2055维；controller版增加20维当前已发关节目标和1维外部指令，不读取当前物体真值。输入维度改变也改变随机初始化，因此不能单独归因于某一个新增输入。

普通CP250快速/慢速联合63/300、101/300；controller CP250为47/300、67/300。各300是三种训练抓姿各100个已有开发扰动，所有未训练第四抓姿均0/32。不能把CP100慢速controller100/300的优势外推到CP250。图和ZIP保留所有CP100/250记录与失败。

视频无文字，上排普通CP250，下排controller CP250；从左至右原抓姿、row16、row15。每组固定取开发队列0/100/200，选取在汇总后，不按成功挑选。视频是在本机4090、3个环境重新仿真，不增加独立评估分母，也不保证与332环境逐帧一致。八卡远端两次相机创建阶段退出-11，日志保留。

底部动作误差图来自CP100的72个已有初态，三种driver各跑一次真实物理。仅指定driver控制环境，所有反事实动作使用同一个入站actor记忆且不进入物理。误差只在仍活跃的转移上平均，掉落轨迹会变短；不把更短的误差分母当作更强能力。六次门禁验证证明额外诊断不改变物理/动作/完整actor记忆；跨进程五维critic接触输入差异另记。

同teacher轨迹上controller动作误差较小，但到自身闭环上前两抓姿优势并不一致。新实验从同一普通student CP250及相同初态出发，比较当前样本训练与50%历史自身轨迹MSE；它是有待验证的保留能力假设。该包没有宣称可靠student、未见抓姿泛化或真机成功。部署仍需要真实动力学与控制链路标定。
''')
    with zipfile.ZipFile(output/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(evidence.rglob('*')):
            if p.is_file():
                archive.write(p,str(p.relative_to(evidence)))
    files = [p for p in output.iterdir() if p.is_file() and not p.name.endswith('SHA256SUMS.txt')]
    (output/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(digest(p)+'  '+p.name for p in sorted(files))+'\n')
    print(json.dumps(dict(output=str(output),assets=len(files)+1,video_frames=decoded,
                          video_results=[{k:x[k] for k in ['kind','joint','alive']} for x in provenance['videos']])))


if __name__ == '__main__':
    main()
