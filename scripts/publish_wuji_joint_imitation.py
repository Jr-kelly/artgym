"""Package the full encoder+actor imitation comparison against frozen-encoder actor imitation."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.publish_wuji_student_replay_results import read_trial

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'runs/wuji-goal'


def main():
    checkpoints = [0,1,25,100,250,500]
    rows = []
    for arm in ['actor','joint']:
        for cp in checkpoints:
            for sec in [2,5]:
                prefix = 'student-actionimit-actor-seed68-v5' if arm=='actor' else 'student-jointimit-seed68-v1'
                name = '%s-cp%d-mixed332-timed%dseconds'%(prefix,cp,sec)
                folder, report, trace = read_trial(name)
                assert report['policy_kind'] == ('student_with_direct_teacher_action_imitation' if arm=='actor' else 'student_with_joint_encoder_action_imitation')
                body = (np.isfinite(trace['drift']) & np.isfinite(trace['rotation']) &
                        (trace['drift']<.01) & (trace['rotation']<.25)).all(0)
                alive = np.array([v['alive_full'] for v in report['records']])
                body &= alive
                rows.append(dict(name=name,arm=arm,checkpoint=cp,seconds=sec,
                    joint=[sum(v['stable_full_all_endpoints'] for v in report['records'][i:i+100]) for i in [0,100,200,300]],
                    alive=[int(alive[i:i+100].sum()) for i in [0,100,200,300]],
                    body=[int(body[i:i+100].sum()) for i in [0,100,200,300]],folder=folder,trace=trace))
    out = BASE/'release-joint-imitation-final-20260922'
    out.mkdir(exist_ok=False)
    evidence = out/'evidence'
    evidence.mkdir()
    prefix = 'wuji-joint-imitation-final-20260922'
    hashes = {}
    def copy(path, destination):
        shutil.copy2(path,evidence/destination)
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for row in rows:
        for p in row['folder'].iterdir():
            if p.is_file() and p.suffix in ('.json','.yaml','.py'):
                copy(p,row['name']+'-'+p.name)
        np.savez_compressed(evidence/(row['name']+'-metric-trace.npz'),**row['trace'])
    for arm, run in [('actor','wuji_student_actionimit_actor_seed68_v5'),('joint','wuji_student_jointimit_seed68_v1')]:
        b = ROOT/'runs'/run
        status = json.loads((b/'pipeline-status.json').read_text())
        assert status['status']=='completed' and status['stages'][-1]['returncode']==0
        for rel in ['pipeline-status.json','imitation/status.json','imitation/report.json','imitation/metrics.jsonl','preflight/report.json','runtime/report.json']:
            copy(b/rel,arm+'-'+rel.replace('/','-'))
    for p in [Path(__file__),ROOT/'scripts/train_wuji_joint_imitation.py',ROOT/'scripts/train_wuji_actor_imitation.py',
              ROOT/'scripts/wuji_timed_command_metrics.py',BASE/'student-jointimit-seed68-v1-proposal.json']:
        copy(p,p.name)
    fig,axes=plt.subplots(2,3,figsize=(12,7.5))
    for ri,sec in enumerate([2,5]):
        for ci,label in enumerate(['Original grasp','Training row16','Training row15']):
            ax=axes[ri,ci]
            for arm,caption,color in [('actor','Frozen encoder + actor imitation','#317994'),('joint','Encoder + actor imitation','#bd8134')]:
                selected=[r for r in rows if r['arm']==arm and r['seconds']==sec]
                ax.plot(range(len(checkpoints)),[r['joint'][ci] for r in selected],'o-',label=caption,color=color,markersize=4)
            ax.set(title=label+' / %d s commands'%sec,ylim=(-2,103),xticks=range(len(checkpoints)),
                   xticklabels=checkpoints,xlabel='Saved updates',ylabel='20 s joint success /100')
            ax.grid(alpha=.2)
            ax.spines[['top','right']].set_visible(False)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.96),ncol=2,frameon=False)
    fig.suptitle('Wuji direct action imitation: complete 500-update comparison')
    fig.text(.02,.014,'Same actor initialization, seed68, Adam1e-5, 2048 x32 transitions/update; sequential runs on the same H100 host.\nFrozen teacher labels its own recurrent history of student-induced states; student alone drives physics. Each run: 32,768,000 formal transitions.\nReused 332 development states: 3 training grasps x100 and fourth unseen grasp x32. Strict 2 mm tails and body stability; no hardware/generalization claim.',fontsize=8)
    fig.tight_layout(rect=[0,.11,1,.9])
    fig.savefig(out/(prefix+'-curves.png'),dpi=170)
    plt.close(fig)
    records=[{k:v for k,v in r.items() if k not in ['folder','trace']} for r in rows]
    provenance=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),records_rescored_exact=True,
                    reports=len(rows),formal_budgets_completed=True,records=records,source_sha256=hashes)
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    table=['|CP|冻结encoder 快/慢|联合encoder 快/慢|','|---|---:|---:|']
    for cp in checkpoints:
        cells=['/'.join(str(sum(next(r for r in rows if r['arm']==arm and r['checkpoint']==cp and r['seconds']==sec)['joint'][:3])) for sec in [2,5]) for arm in ['actor','joint']]
        table.append('|%d|%s|%s|'%(cp,*cells))
    (out/(prefix+'-README.md')).write_text('# Wuji 动作模仿：编码器是否可更新\n\n'+
        '两组均500轮正常完成，24份固定评估从原物理trace逐条重算一致。\n\n'+'\n'.join(table)+
        '\n\n每项分母300，三训练抓姿各100扰动；第四抓姿32次另保留于provenance。'+
        '完整actor组冻结历史编码器；联合组允许其22个参数张量更新，输入仍为50帧关节/动作与初始信息。'+
        '同seed68、同初始actor和初态文件，先后在同一八卡主机运行；不声明后续PhysX逐位相同。'+
        'teacher保持独立循环历史，只供动作标签；原teacher及标准化权重冻结，student独立驱动物理。'+
        '联合组在normalizer之后插入可微latent，并在每次参数更新后重算当前latent；跨batch actor记忆沿用旧权重产生的detached状态。'+
        '新显式状态估计器V2的历史刷新遗漏不适用于这两组：两组均通过WujiFixedStudentActor开启历史更新。'+
        '这里评价的是完整500轮预算和严格2mm时钟指标，不能借中期峰值或训练loss宣称可靠策略。\n')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(evidence.iterdir()):
            archive.write(p,p.name)
    files=sorted(p for p in out.iterdir() if p.is_file())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),reports=len(rows))))


if __name__=='__main__':
    main()
