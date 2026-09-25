"""Preserve the complete matched state-estimator continuation comparison."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.analyze_wuji_state_encoder_evaluations import analyze

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/wuji-goal'


def main():
    out=BASE/'release-state-replay-final-20260922';assert not out.exists()
    rows=[];training={};artifacts=[]
    for arm in ['current','teacher_replay']:
        run=ROOT/f'runs/wuji_physical_state_replay_{arm}_seed73_v1/training'
        report=json.loads((run/'report.json').read_text())
        assert report['status']=='passed' and report['teacher_unchanged'] and report['optimizer_steps']==500
        assert report['checks']['student_physics_transitions']==report['checks']['presim_action_checks']==8192000
        assert report['checks']['latest_history_matches']==8192000 and report['checks']['teacher_physics_transitions']==0
        assert sum(report['supervised_counts'].values())==4096000
        training[arm]=report
        path=run/'checkpoints/student_000500.pth';meta=json.loads(path.with_suffix('.json').read_text())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['sha256']
        artifacts += [path,path.with_suffix('.json')]
        for update in [0,1,25,100,250,500]:
            for seconds in [2,5]:
                p=BASE/f'verification/student-physical-state-replay-{arm}-seed73-v1-cp{update}-mixed332-timed{seconds}seconds'
                row=analyze(p);row['arm']=arm;rows.append(row)
                assert row['groups'][3]['joint']==0
        for seconds in [2,5]:
            p=BASE/f'verification/student-physical-state-replay-{arm}-seed73-v1-cp0-runtime3-timed{seconds}seconds'
            row=analyze(p);row['arm']=arm;rows.append(row)
    assert len(rows)==28
    assert training['current']['initial_encoder_sha256']==training['teacher_replay']['initial_encoder_sha256']
    result=dict(rows=rows,training=training,records_rescored_exact=True,full500_budget_verified=True,
        scope='Matched continuation seed73,own1024x16x500physics each. Current-only or half current/half fixed teacher data. Frozen controller,not independent validation or hardware.',
        initial_fast_slow=[168,51],final_fast_slow={'current':[124,76],'teacher_replay':[174,169]},denominator=300,fourth_grasp=32)
    for arm,expected in result['final_fast_slow'].items():
        assert [next(r['joint'] for r in rows if r['arm']==arm and r['update']==500 and r['seconds']==s) for s in [2,5]]==expected
    out.mkdir();prefix='wuji-state-replay-final-20260922'
    (out/(prefix+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    updates=[0,1,25,100,250,500]
    for ax,seconds in zip(axes,[2,5]):
        for arm,color in [('current','#407f9f'),('teacher_replay','#c27b38')]:
            y=[next(r['joint'] for r in rows if r['arm']==arm and r['update']==u and r['seconds']==seconds and r['num_envs']==332) for u in updates]
            ax.plot(range(len(updates)),y,'o-',label=arm.replace('_',' '),color=color)
        ax.set(xticks=range(len(updates)),xticklabels=updates,ylim=(0,300),xlabel='Optimizer updates (categorical)',ylabel='Strict successes /300',title=f'{seconds} s commands')
        ax.grid(alpha=.2);ax.legend(frameon=False);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('State estimator continuation: complete fixed checkpoint schedule')
    fig.text(.02,.015,'Three training grasps x100 perturbations; fourth grasp0/32 throughout. Same initial encoder,500 updates and8.192M own physics transitions per arm.\nReused development states; all final failures included. Neither an independent generalization test nor hardware.',fontsize=8)
    fig.tight_layout(rect=[0,.12,1,.94]);fig.savefig(out/(prefix+'-comparison.png'),dpi=160);plt.close(fig)
    (out/(prefix+'-README.md')).write_text('''# 状态估计续训完整配对结果

两组共同起点快速168/300、慢速51/300，固定500更新后，current组为124/76，teacher_replay组174/169。第四抓姿始终0/32。每组1024环境×16步×500更新=8,192,000自身物理转移，无teacher前缀；每次8192监督样本，共4,096,000。teacher_replay将其中一半换为已冻结teacher的训练帧；固定留出帧不参与优化。

两组从同一离线precision估计器初始化，控制器冻结，Adam2e-5。所有CP0/1/25/100/250/500两时钟及初始运行检查，共28份报告逐条重算；实际物理动作/历史计数、训练预算和最终权重SHA全部核对。中期波动和退化完整保留。teacher_replay最终优于current，但仍不足以成为可靠部署策略。

证据包括全部物理评分trace、估计trace、配置/审计报告、两最终权重及训练日志。状态全部属于开发集，三个训练抓姿各100扰动加第四抓姿32；不是332个独立抓姿。没有真机或独立泛化成功声明。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            p=Path(row['folder']);name=p.name
            for f in p.iterdir():
                if f.is_file() and (f.suffix in ['.json','.yaml','.py'] or f.name=='estimation-trace.npz'):
                    archive.write(f,name+'/'+f.name)
            with np.load(p/'trace.npz') as z:values={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            buf=io.BytesIO();np.savez_compressed(buf,**values);archive.writestr(name+'/metric-trace.npz',buf.getvalue())
        for arm in training:
            p=ROOT/f'runs/wuji_physical_state_replay_{arm}_seed73_v1/training'
            for name in ['status.json','report.json','metrics.jsonl','config.yaml']:
                archive.write(p/name,'training/'+arm+'/'+name)
        for f in artifacts:archive.write(f,'artifacts/'+f.parts[-4]+'/'+f.name)
        for f in [Path(__file__),ROOT/'scripts/train_wuji_physical_state_replay.py',
                  ROOT/'scripts/eval_wuji_physical_state_encoder.py',ROOT/'scripts/wuji_physical_state_encoder.py',
                  ROOT/'scripts/analyze_wuji_state_encoder_evaluations.py',ROOT/'scripts/wuji_timed_command_metrics.py']:
            archive.write(f,'source/'+f.name)
    files=sorted(out.iterdir())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name for f in files)+'\n')
    print(json.dumps(dict(output=str(out),reports=len(rows),files=[(f.name,f.stat().st_size) for f in out.iterdir()])))


if __name__=='__main__':main()
