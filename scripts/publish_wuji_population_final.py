"""Complete one-versus-five population comparison with all fixed checkpoints."""
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
    cases=[]
    for arm in ['one','five']:
        run=ROOT/'runs'/('wuji_student_population_%s_smallcp25_seed67_v1'%arm)
        state=json.loads((run/'pipeline-status.json').read_text())
        assert state['status']=='completed' and state['stages'][-1]['returncode']==0
        for cp in [0,1,25,50,100]:
            for seconds in [2,5]:
                name='student-population-%s-smallcp25-seed67-v1-cp%d-mixed332-timed%dseconds'%(arm,cp,seconds)
                folder,report,trace=read_trial(name)
                records=report['records']
                body=(np.isfinite(trace['drift']) & np.isfinite(trace['rotation']) &
                      (trace['drift']<.01) & (trace['rotation']<.25)).all(0)
                body &= np.array([r['alive_full'] for r in records])
                cases.append(dict(arm=arm,cp=cp,seconds=seconds,name=name,folder=folder,trace=trace,
                    joint=[sum(r['stable_full_all_endpoints'] for r in records[i:i+100]) for i in [0,100,200,300]],
                    alive=[sum(r['alive_full'] for r in records[i:i+100]) for i in [0,100,200,300]],
                    body=[int(body[i:i+100].sum()) for i in [0,100,200,300]]))
    out=BASE/'release-population-final-20260922';out.mkdir(exist_ok=False)
    evidence=out/'evidence';evidence.mkdir()
    prefix='wuji-student-population-final-20260922'
    hashes={}
    def copy(p,name):
        shutil.copy2(p,evidence/name);hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    for c in cases:
        for p in c['folder'].iterdir():
            if p.is_file() and p.suffix in ['.json','.py','.yaml']:copy(p,c['name']+'-'+p.name)
        np.savez_compressed(evidence/(c['name']+'-metric-trace.npz'),**c['trace'])
    for arm in ['one','five']:
        name='wuji_student_population_%s_smallcp25_seed67_v1'%arm
        copy(ROOT/'runs'/name/'pipeline-status.json',name+'-pipeline-status.json')
        for stage in [name,name+'_smoke']:
            for p in (ROOT/'runs'/stage/'runtime-audit').glob('*.json'):copy(p,stage+'-'+p.name)
    for name in ['student-population-seed67-proposal.json','student-actionimit-seed68-v2-proposal.json']:
        copy(BASE/name,name)
    for name in ['scripts/publish_wuji_population_final.py','scripts/train_wuji_population_student.py',
                 'isaacgymenvs/learning/wuji_population_student_actor.py','scripts/wuji_timed_command_metrics.py']:
        copy(ROOT/name,Path(name).name)
    fig,axes=plt.subplots(2,3,figsize=(12,7.4))
    for row,sec in enumerate([2,5]):
        for col,grasp in enumerate(['Original grasp','Training row16','Training row15']):
            ax=axes[row,col]
            for arm,label,color in [('one','Single deployed group','#33829d'),('five','Five exploration groups','#aa8453')]:
                selected=[c for c in cases if c['arm']==arm and c['seconds']==sec]
                ax.plot([c['cp'] for c in selected],[c['joint'][col] for c in selected],'o-',label=label,color=color,markersize=4)
            ax.set(title=grasp+' / %d s commands'%sec,xlabel='PPO epochs',ylabel='20 s joint success /100',ylim=(-2,103),xticks=[0,25,50,100])
            ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.96),ncol=2,frameon=False)
    fig.suptitle('Wuji: complete single versus five population training')
    fig.text(.02,.015,'Both: same CP25 model, seed67, Adam1e-5, 5120 x32 x100, off-policy ratio0, 20 optimizer minibatches/epoch, pose1/ramp0.\nOne group uses ID50 in all5120 envs; five groups use1024 envs each. Original per-group entropy coefficients retained. Different H100 hosts.\nStrict tails <2mm for0.3s, body <10mm /0.25rad. Reused332 development states; fourth-grasp failures retained. No hardware claim.',fontsize=8)
    fig.tight_layout(rect=[0,.11,1,.9]);fig.savefig(out/(prefix+'-curves.png'),dpi=170);plt.close(fig)
    records=[{k:v for k,v in c.items() if k not in ['folder','trace']} for c in cases]
    (out/(prefix+'-provenance.json')).write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reports=20,all_records_rescored_exact=True,cases=records,source_sha256=hashes),indent=2)+'\n')
    (out/(prefix+'-README.md')).write_text('''# 单组与五组完整训练对照

两组均100/100正常退出，20项固定CP0/1/25/50/100评估从原trace逐条重算一致。最终单组快速113/300、慢速209/300；五组88/300、219/300。起点快速均208，慢速238/239。单组训练没有解决退化；独立PhysX进程CP0也存在小差异，不能宣称位级相同。

同一个历史小噪声CP25、seed67、新Adam1e-5、5120×32×100、两组都关闭跨组样本混用，20个optimizer minibatches/轮；near5、pose1/ramp0、broad0。模型保留原五行探索embedding和sigma，单组只用ID50；实际预检确认首模型权重完全相同、所有96次rollout编号正确、单组未用四行不变/第0行更新。冻结student与normalizer、有限性、学习率及同策略KL检查均通过。

这是探索人口数量对照，区别于此前仍保留五组、仅关闭数据混用的实验。按原公式单组保留第0组熵系数0.0025；五组系数0.0025到0，因此总体熵系数分布也改变。两组在不同H100主机运行，不能把一个seed的差值当作唯一因果证明。冻结诊断的总体提升/第0组下降支持检验这个假设，当前结果未证明集中训练部署组足够。

332初态为三个训练抓姿各100扰动及第四未训练抓姿32；不是332种抓姿。每次指令末0.3秒持续<2mm，刀身全程<10mm/.25rad且存活；第四抓姿均失败。附纯刀身稳定分解不混入首次循环条件。直接动作蒸馏头层/完整actor的新迁移实验另列，不混入本包，也未声明可靠student或真机完成。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()):z.write(p,p.name)
    files=sorted(p for p in out.iterdir() if p.is_file())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),reports=20,assets=len(files)+1)))


if __name__=='__main__':main()
