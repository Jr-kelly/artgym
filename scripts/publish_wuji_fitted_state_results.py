"""Publish both final offline fits' complete closed-loop outcomes and estimation traces."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/wuji-goal'


def main():
    analysis=BASE/'diagnostics/fitted-state-complete-rescored-2110.json'
    result=json.loads(analysis.read_text())
    assert len(result['rows'])==8 and result['records_rescored_exact']
    original=BASE/'diagnostics/fitted-state-evaluation-2046-v1'
    status=json.loads((original/'status.json').read_text())
    assert status['status']=='completed' and len(status['stages'])==8
    assert all(v['returncode']==0 for v in status['stages'])
    out=BASE/'release-fitted-state-final-20260922'
    out.mkdir(exist_ok=False)
    prefix='wuji-fitted-state-closed-loop-20260922'
    splits={}
    for arm in ['precision_units','motion_units']:
        fig,axes=plt.subplots(3,2,figsize=(13,8),sharex=True,sharey=True)
        for col,seconds in enumerate([2,5]):
            folder=original/('%s-mixed332-%ds'%(arm,seconds))
            report=json.loads((folder/'report.json').read_text())
            with np.load(folder/'estimation-trace.npz') as z:
                prediction=z['prediction'][:,:,6]*.5
                target=z['target'][:,:,6]*.5
                active=z['active']
            for row,index in enumerate([0,100,200]):
                ax=axes[row,col]
                x=np.arange(600)/30
                ax.plot(x,np.where(active[:,index],target[:,index],np.nan),label='Actual slider',color='#347e9c',lw=1.3)
                ax.plot(x,np.where(active[:,index],prediction[:,index],np.nan),label='Estimated slider',color='#be7337',lw=1.1,alpha=.85)
                ax.set(title='Initial row %d / %d s commands'%(index,seconds),ylabel='Slider displacement (mm)',xlabel='Simulation time (s)')
                ax.grid(alpha=.2)
                ax.spines[['top','right']].set_visible(False)
            records=report['records']
            sets=dict(fit=[i+j for i in [0,100,200] for j in range(20)],
                      validation=[i+j for i in [0,100,200] for j in range(20,30)],
                      other_development=[i+j for i in [0,100,200] for j in range(30,100)],
                      fourth_grasp=list(range(300,332)))
            splits['%s-%ds'%(arm,seconds)]={k:dict(count=len(indices),joint=sum(records[i]['stable_full_all_endpoints'] for i in indices)) for k,indices in sets.items()}
        handles,labels=axes[0,0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.96),ncol=2,frameon=False)
        fig.suptitle('Offline fitted state model: '+arm.replace('_',' '))
        fig.text(.02,.016,'Predetermined rows0/100/200 from the full332 physics evaluation; these3 rows were part of the fitting set. No successful-row selection.\nBoth signals are pre-action; inactive rows masked. Both models fitted only on teacher2s trajectories; no teacher prefix during these tests.\nDevelopment visualization only. Full success/failure records for every row and both clocks are in the accompanying evidence.',fontsize=8)
        fig.tight_layout(rect=[0,.11,1,.91])
        fig.savefig(out/(prefix+'-'+arm+'-traces.png'),dpi=160)
        plt.close(fig)
    result['fit_validation_development_split']=splits
    (out/(prefix+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    readme='''# 离线状态拟合模型的完整闭环评估

|1000更新最终模型|2秒指令成功/300|5秒指令成功/300|快/慢存活/332|
|---|---:|---:|---:|
|precision_units|168|51|299/299|
|motion_units|40|111|300/300|

第四抓姿均0/32。两模型均按预先固定的1000更新最终权重评估，未挑选中期峰值。8项运行检查/正式评估均正常退出，实际物理步数、观测历史推进、无当前私有状态输入及物理评分逐条重算。正式796,800物理转移，运行检查7,200转移。

离线验证滑块RMSE约0.740/0.701mm，闭环时约2.25/2.84mm与2.11/2.40mm（快/慢）。较小的离线或平均闭环误差都不能保证完整任务成功。慢时钟的弱表现与训练数据只有teacher2秒轨迹有关的假设仍需对照验证，不能直接认定已经找到唯一原因。

开发332初态包含60拟合行、30验证行、另外210已有开发行和第四抓姿32行；都不算新独立验证集。results保留这四组分母和每项评分。曲线固定显示0/100/200行，这三行在拟合集内，未按成功筛选。完整结果包括全部失败。

证据ZIP包含两模型最终权重和来源元数据、全部8项估计trace与物理评分trace、报告、配置和源码。完整原始物理trace在本机及远端保留，SHA256在results记录。推理仍假设已知初始获取坐标信息；没有真机标定或部署成功声明。
'''
    (out/(prefix+'-README.md')).write_text(readme)
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(original/'status.json','evaluation/status.json')
        for row in result['rows']:
            folder=Path(row['folder']);name=folder.name
            for p in folder.iterdir():
                if p.is_file() and (p.suffix in ['.json','.yaml','.py'] or p.name=='estimation-trace.npz'):
                    archive.write(p,name+'/'+p.name)
            with np.load(folder/'trace.npz') as z:
                trace={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            stream=io.BytesIO();np.savez_compressed(stream,**trace)
            archive.writestr(name+'/metric-trace.npz',stream.getvalue())
        for arm in ['precision_units','motion_units']:
            artifact=BASE/'diagnostics/state-scale-2036-v1/artifacts'/(arm+'.pth')
            meta=json.loads(artifact.with_suffix('.json').read_text())
            assert hashlib.sha256(artifact.read_bytes()).hexdigest()==meta['sha256']
            archive.write(artifact,'artifacts/'+artifact.name)
            archive.write(artifact.with_suffix('.json'),'artifacts/'+arm+'.json')
        for p in [Path(__file__),ROOT/'scripts/eval_wuji_fitted_state_encoder.py',ROOT/'scripts/wuji_physical_state_encoder.py',
                  ROOT/'scripts/analyze_wuji_state_encoder_evaluations.py',ROOT/'scripts/wuji_timed_command_metrics.py',
                  BASE/'student-fitted-state-evaluation-2046-v1-proposal.json']:
            archive.write(p,'source/'+p.name)
    files=sorted(p for p in out.iterdir() if p.is_file())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(out)


if __name__=='__main__':
    main()
