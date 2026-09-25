"""Complete LR/mixing controls and all frozen exploration groups, with failures."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.publish_wuji_student_replay_results import read_trial

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/wuji-goal'


def main():
    arms={
        'lrquarter0':('LR/4, broad0','#337fac','student-actorrl-replaycp25-sigmaquarter-broad0-lrquarter-seed62-v2','wuji_student_actorrl_replaycp25_sigmaquarter_broad0_lrquarter_seed62_v2'),
        'lrquarter5':('LR/4, broad5','#c19042','student-actorrl-replaycp25-sigmaquarter-broad5-lrquarter-seed62-v2','wuji_student_actorrl_replaycp25_sigmaquarter_broad5_lrquarter_seed62_v2'),
        'samegroup':('Same-group only, LR1e-5','#499777','student-actorrl-replaycp25-sigmaquarter-onpolicy-seed62-v1','wuji_student_actorrl_replaycp25_sigmaquarter_onpolicy_seed62_v1')}
    cases=[]
    for arm,(_,_,prefix,run) in arms.items():
        state=json.loads((ROOT/'runs'/run/'pipeline-status.json').read_text())
        assert state['status']=='completed' and state['stages'][-1]['returncode']==0
        for cp in [0,1,25,50,100]:
            for seconds in [2,5]:
                cases.append(dict(kind='training',arm=arm,cp=cp,seconds=seconds,
                    name=prefix+'-cp%d-mixed332-timed%dseconds'%(cp,seconds)))
    for group in range(5):
        for seconds in [2,5]:
            cases.append(dict(kind='group',group=group,seconds=seconds,
                name='frozen-student-actorrl-sigmaquarter-broad0-cp100-block%d-mixed332-timed%dseconds'%(group,seconds)))
    for case in cases:
        folder,report,trace=read_trial(case['name'])
        if case['kind']=='group':
            audit=report['exploration_group_audit']
            assert audit['model_before']==audit['model_after'] and audit['block']==case['group']
        case.update(folder=folder,trace=trace,
            joint=[sum(x['stable_full_all_endpoints'] for x in report['records'][i:i+100]) for i in [0,100,200,300]],
            alive=[sum(x['alive_full'] for x in report['records'][i:i+100]) for i in [0,100,200,300]],
            body=[sum(x['stable_full'] for x in report['records'][i:i+100]) for i in [0,100,200,300]])
    out=BASE/'release-student-actor-followup-final-20260922'
    assert not out.exists()
    evidence=out/'evidence'
    evidence.mkdir(parents=True)
    prefix='wuji-student-actor-followup-final-20260922'
    hashes={}

    def copy(source,name):
        shutil.copy2(source,evidence/name)
        hashes[str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()

    for case in cases:
        for name in ['report.json','status.json','config.yaml','source.py','source_metrics.py','exploration_block_source.py']:
            source=case['folder']/name
            if source.exists():copy(source,case['name']+'-'+name)
        np.savez_compressed(evidence/(case['name']+'-metric-trace.npz'),**case['trace'])
    for _,_,_,run in arms.values():copy(ROOT/'runs'/run/'pipeline-status.json',run+'-pipeline-status.json')
    for name in ['student-actorrl-sigmaquarter-lrquarter-seed62-v2-proposal.json','student-actorrl-onpolicy-seed62-proposal.json',
                 'student-actorrl-frozen-groups-cp100-1612-proposal.json','student-actorrl-pose-pair-seed64-proposal.json',
                 'diagnostics/actor-noise-final-endpoints-1625.py','diagnostics/actor-noise-final-endpoints-1625.json',
                 'diagnostics/frozen-student-actorrl-cp100-groups-1612/preflight.json',
                 'diagnostics/frozen-student-actorrl-cp100-groups-1612/status.json',
                 'diagnostics/frozen-student-actorrl-cp100-groups-1612/runner_source.py',
                 'diagnostics/frozen-student-actorrl-cp100-groups-1612/group_source.py']:
        copy(BASE/name,name.replace('/','-'))
    copy(Path(__file__),'publisher_source.py')
    copy(ROOT/'scripts/publish_wuji_student_replay_results.py','reader_source.py')
    copy(ROOT/'scripts/wuji_timed_command_metrics.py','metric_source.py')
    fig,axes=plt.subplots(2,3,figsize=(13,8))
    for row,seconds in enumerate([2,5]):
        for col,grasp in enumerate(['Original grasp','Training row16','Training row15']):
            ax=axes[row,col]
            for arm,(label,color,_,_) in arms.items():
                selected=[c for c in cases if c['kind']=='training' and c['arm']==arm and c['seconds']==seconds]
                ax.plot([c['cp'] for c in selected],[c['joint'][col] for c in selected],'o-',label=label,color=color,markersize=4)
            ax.set(title=grasp+' / %d s commands'%seconds,xlabel='PPO epochs',ylabel='20 s joint success / 100',ylim=(-2,103),xticks=[0,25,50,100])
            ax.grid(alpha=.2)
            ax.spines[['top','right']].set_visible(False)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Wuji: complete lower-LR and same-group-only followups')
    fig.text(.02,.015,'Same original quarter-std initialization, frozen replayCP25 encoder, seed62, 5120 x32 x100. LowerLR2.5e-6; same-group-only1e-5.\nSame-group-only retains five exploration groups but uses20 instead of24 optimizer minibatches/epoch; physics budgets match, optimizer compute differs.\nStrict command tails <2mm for0.3s and body <10mm /0.25rad; reused332 development states. All held-out fourth-grasp failures retained.',fontsize=8)
    fig.tight_layout(rect=[0,.095,1,.95])
    fig.savefig(out/(prefix+'-training-curves.png'),dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    colors=['#3b7c98','#79a966','#b49445','#996786','#839599']
    for ax,seconds in zip(axes,[2,5]):
        for group in range(5):
            case=next(c for c in cases if c['kind']=='group' and c['group']==group and c['seconds']==seconds)
            bars=ax.bar(np.arange(3)+(group-2)*.16,case['joint'][:3],width=.15,label='Group%d'%group,color=colors[group])
            ax.bar_label(bars,fontsize=8,padding=2)
        ax.set(title='%d s commands'%seconds,xticks=[0,1,2],xticklabels=['Original','Row16','Row15'],ylabel='20 s joint success /100',ylim=(0,108))
        ax.grid(axis='y',alpha=.15)
        ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
    axes[0].legend(fontsize=8,loc='lower left')
    fig.suptitle('Frozen quarter-std / broad0 CP100: all five SAPG groups')
    fig.text(.02,.015,'Only constant group ID changes; actor/encoder/normalizer frozen. Same eight-GPU host/GPU3, same332 development states.\nGroup0 wrapper matched standard physics/actions/targets over3600 real transitions before10complete trials. All failures included.\nSelecting a group is not new training, blinded evaluation, unseen-grasp success or hardware validation.',fontsize=8)
    fig.tight_layout(rect=[0,.15,1,.95])
    fig.savefig(out/(prefix+'-frozen-groups.png'),dpi=170)
    plt.close(fig)
    records=[{k:v for k,v in c.items() if k not in ['folder','trace']} for c in cases]
    (out/(prefix+'-provenance.json')).write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        reports=40,all_records_rescored_exact=True,cases=records,source_sha256=hashes),indent=2)+'\n')
    (out/(prefix+'-README.md')).write_text('''# 完整学习率/数据混用对照与冻结策略五组诊断

共40份评估逐条从trace重算：30份训练固定CP0/1/25/50/100，10份冻结CP100组间比较。全部失败保留。训练组三组100轮均正常退出；从同原std/4初始化、冻结replayCP25编码器、seed62、5120×32×100开始。低学习率两组Adam2.5e-6、宽奖励0/5；只用同组样本组Adam1e-5、宽奖励0，保留五探索组但不混用其他组样本，每轮20而非24个minibatch，物理预算相同，优化计算不同。

最终快速/慢速联合数：低学习率宽0为131/172，宽5为94/156，只用同组样本98/223，各分母300。与先前小噪声宽0最终130/218比较，没有消除退化。这里不同学习率/奖励/数据混用分支分别定义，不将任意两条曲线都称为单变量对照；各支相应基线见此前actor-noise-final发布。

冻结小噪声宽0CP100，五组最终快速/慢速：130/218、82/251、81/172、126/173、138/155。全部300存活，但联合要求还包括刀身稳定与每个端点。组1慢速改善伴随快速退化，没有单个组同时解决任务。新增组0入口先和原入口两次3×600真实物理检查，动作/目标/关节/物理trace完全相等。所有组同八卡GPU3执行、模型状态不变，实际输入ID逐次检查。

332初态均为开发集：三训练抓姿各100扰动、未训练第四抓姿32；第四抓姿全部0/32。每次指令最后0.3秒<2mm，刀身全程<10mm/.25rad，不能把不掉刀当作联合成功。附完整端点/刀身分解：此前小噪声CP100第三抓姿快速仅34/100与15/100刀身稳定，打开平均误差2.506/2.902mm。额外稳定性权重对照另行训练，不纳入本包结果。

SAPG聚合KL含跨组分布差异，旧聚合门禁已被零学习率诊断否定；本次三组通过精确同策略KL与冻结/有限性真实预检。全部为迁移研究结果，尚无可靠student、未见抓姿/几何或真机完成声明。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(evidence.iterdir()):z.write(f,f.name)
    files=[p for p in out.iterdir() if p.is_file()]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(files))+'\n')
    print(json.dumps(dict(output=str(out),reports=40,assets=len(files)+1)))


if __name__=='__main__':
    main()
