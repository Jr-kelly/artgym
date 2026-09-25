"""Publish checkpoint fluctuations and matched replay controls, retaining failures."""
import datetime
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
BASE = ROOT/'runs/wuji-goal'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_trial(name):
    folder = BASE/'verification'/name
    status = json.loads((folder/'status.json').read_text())
    assert status['status'] == 'completed' and status['returncode'] == 0
    report = json.loads((folder/'report.json').read_text())
    with np.load(folder/'trace.npz') as archive:
        trace = {key:archive[key] for key in ['active', 'fall', 'invalid', 'slider', 'goal', 'drift', 'rotation']}
    score = score_timed_trace(trace, report['protocol']['stage_steps'], 9, 600)
    assert score['records'] == report['records']
    return folder, report, trace


def main():
    cases = []
    for arm in ['current', 'currenttwice', 'replay']:
        version = 'v1' if arm == 'currenttwice' else 'v2'
        for cp in [25, 100, 250, 500]:
            for seconds in [2, 5]:
                name = 'student-bridge3-pure250-%s500-seed60-%s-cp%d-mixed332-timed%dseconds' % (arm, version, cp, seconds)
                status = BASE/'verification'/name/'status.json'
                ready = status.exists() and json.loads(status.read_text())['status'] == 'completed'
                if cp <= 100:
                    assert ready, 'Both early matched checkpoints must be complete: '+name
                if not ready:
                    continue
                folder, report, trace = read_trial(name)
                groups = [report['records'][i:i+100] for i in [0,100,200,300]]
                cases.append(dict(name=name, arm=arm, cp=cp, seconds=seconds, folder=folder, report=report, trace=trace,
                                  joint=[sum(row['stable_full_all_endpoints'] for row in rows) for rows in groups],
                                  alive=[sum(row['alive_full'] for row in rows) for rows in groups]))
    video_name = 'student-bridge3-replay-cp25-three-grasps-video-timed2seconds-localgraphics'
    video_folder, video_report, video_trace = read_trial(video_name)
    assert video_report['initial_state_rows'] == [0,100,200]
    out = BASE/'release-student-replay-controls-20260922'
    assert not out.exists(), 'Preserve previous publication; use a new dated package'
    evidence = out/'evidence'
    evidence.mkdir(parents=True)
    prefix = 'wuji-student-replay-controls-20260922'
    provenance = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope=__doc__,
                      reports=[], source_files={}, denominators=[100,100,100,32], complete_budget_claim=False)

    def copy(source, target=None):
        destination = evidence/(target or source.name)
        shutil.copy2(source, destination)
        provenance['source_files'][str(source.relative_to(ROOT))] = sha(source)

    for case in cases:
        for name in ['report.json','status.json','config.yaml','source.py','source_metrics.py']:
            copy(case['folder']/name, case['name']+'-'+name)
        np.savez_compressed(evidence/(case['name']+'-metric-trace.npz'), **case['trace'])
        provenance['reports'].append({key:case[key] for key in ['name','arm','cp','seconds','joint','alive']})
    fig, axes = plt.subplots(2,3,figsize=(13,7.8))
    colors = dict(current='#888888', currenttwice='#e18b31', replay='#2474a4')
    labels = dict(current='Current batch', currenttwice='Second current pass', replay='Historical batch')
    for row, seconds in enumerate([2,5]):
        for col, name in enumerate(['Original grasp','Training row16','Training row15']):
            ax = axes[row,col]
            for arm in colors:
                selected = [case for case in cases if case['arm']==arm and case['seconds']==seconds]
                ax.plot([case['cp'] for case in selected], [case['joint'][col] for case in selected],
                        'o-',color=colors[arm],label=labels[arm],markersize=4)
            ax.set(title=name+' / %d s commands'%seconds, xlabel='Updates after frozen ordinary-student CP250',
                   ylabel='20 s joint success / 100',ylim=(-2,103),xticks=[25,100,250,500],xlim=(10,515))
            ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Wuji student replay: useful early gains, substantial checkpoint fluctuations')
    fig.text(.02,.014,'Matched initialization, seed60, Adam2.0e-4, 1024 environments, 16 steps/update. Historical/current-twice: same extra pass and FIFO overhead.\nEvery command tail within 2 mm for 0.3 s; body drift <10 mm / angle <0.25 rad, alive. Reused development states; held-out grasp 0/32 throughout.\nOnly completed checkpoints at packaging are drawn. Single seed, different GPU scheduling; no claim of completed comparison budgets, unseen-grasp or hardware success.',fontsize=8)
    fig.tight_layout(rect=[0,.085,1,.955])
    fig.savefig(out/(prefix+'-checkpoint-comparison.png'),dpi=170)
    plt.close(fig)

    movie = out/(prefix+'-learned-cp25-three-grasps-no-text.mp4')
    shutil.copy2(video_folder/'policy.mp4',movie)
    reader = imageio.get_reader(movie)
    imageio.imwrite(out/(prefix+'-frame-at-10seconds.png'),reader.get_data(300))
    reader.close()
    frames = sum(1 for _ in imageio.get_reader(movie))
    assert frames == 600
    for name in ['report.json','status.json','config.yaml','source.py','source_metrics.py']:
        copy(video_folder/name,video_name+'-'+name)
    np.savez_compressed(evidence/(video_name+'-metric-trace.npz'),**video_trace)
    provenance['video'] = dict(source=video_name, frames=frames, fps=30, added_text=False, initial_rows=[0,100,200],
                               joint=video_report['stable_full_all_endpoints'], alive=video_report['alive_full'],
                               sha256=sha(movie), scope='3env resimulation on local4090, not new independent trials; no success-based row selection')
    student = BASE/'frozen-candidates/student-bridge3-replay-seed60-cp25/student.pth'
    assert sha(student)=='0d2480657bf6176d32c379743f68402aba67aa868bea54b112bbc1bc34142b17'
    shutil.copy2(student,out/(prefix+'-frozen-student-cp25.pth'))
    copy(student.with_name('manifest.json'),'frozen-student-manifest.json')
    for name in ['student-replay-pair-seed60-proposal.json','student-replay-currenttwice-seed60-proposal.json',
                 'student-replay-cp25-video-proposal.json','diagnostics/student-replay-cp100-regression-1417.json',
                 'diagnostics/student-actorrl-baseline-1441.json']:
        copy(BASE/name)
    for arm, version in [('current','v2'),('currenttwice','v1'),('replay','v2')]:
        run = 'wuji_student_bridge3cp25_pure250_then_%s500_seed60_%s'%(arm,version)
        folder = ROOT/'runs'/run/'preflight/runtime-audit'
        for p in folder.glob('*.json'):
            copy(p,run+'-'+p.name)
    copy(ROOT/'scripts/publish_wuji_student_replay_results.py')
    copy(ROOT/'isaacgymenvs/utils/distill_replay.py')
    copy(BASE/'bridge3-evaluation-states/mixed332.npy','development-initial-states332.npy')
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    (out/(prefix+'-README.md')).write_text('''# Wuji student：历史样本训练与计算量对照

三组从同一普通student CP250、同teacher CP25、seed60、新Adam2e-4开始，1024环境×16步×500更新。当前组只使用当前batch；历史组50%当前MSE+50%过去自身轨迹MSE，FIFO655360；第二次当前组维持同FIFO写入、采样及额外训练前向/反向，但第二次使用当前状态/标签。后两组额外dropout使用私有随机流。当前组的计算量较少。三组实际5更新预检、初始权重和物理初态一致；额外当前组在看到早期结果后追加、运行在另一台H100，属于单seed后续对照。

CP25快速/慢速联合：当前16/54，第二次当前9/56，历史153/222（各300，三种训练抓姿各100个扰动）。历史CP100回落至63/93；row16持握仍在，但打开端点偏差约4mm。训练MSE降低并不保证开合成功。图展示打包时已经完成的后续固定checkpoint，缺失点表示尚未收齐，不能当作0或完整预算比较。所有保留的未训练第四抓姿均0/32。

视频是冻结历史CP25的真实student闭环，无文字，从左到右固定取开发集0/100/200三个初态；选择在查看汇总后，不按成功挑选。3环境本机重仿真不增加独立分母，也不保证逐帧等于332环境。三条结果、失败及所有完整评估记录见provenance和ZIP。策略输入没有当前物体真值；编码器使用50帧实测关节角/历史动作以及初始信息，actor还使用关节、命令和FK信息。当前仅仿真，不宣称真机或未见抓姿成功。

PPO后续实验固定该编码器、允许actor与privileged critic继续学习。新入口CP0在同332初态上与原student两种时序的逐条记录完全一致。其正式微调结果另行评价，本包没有把它当作已成功结果。模型PTH是冻结student编码器工件，需配套冻结teacher CP25的actor/归一化权重和源码，不能单独作为真机控制程序。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(evidence.iterdir()):
            archive.write(p,p.name)
    files = [p for p in out.iterdir() if p.is_file()]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(files))+'\n')
    print(json.dumps(dict(output=str(out),reports=len(cases),video=provenance['video'],assets=len(files)+1)))


if __name__ == '__main__':
    main()
