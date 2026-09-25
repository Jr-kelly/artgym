"""Package all frozen component oracles plus the two-clock offline data diagnostic."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.analyze_wuji_state_component_probes import analyze

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/wuji-goal'


def main():
    out=BASE/'release-state-components-final-20260922'
    assert not out.exists()
    rows=[]
    for seconds in [2,5]:
        folder=BASE/f'diagnostics/state-components-{seconds}s-2138-v1'
        status=json.loads((folder/'status.json').read_text())
        assert status['status']=='completed' and len(status['stages'])==8
        assert all(s['returncode']==0 for s in status['stages'])
        for runtime in [True,False]:
            for condition in ['estimated','true_body','true_slider','true_both']:
                name=('runtime-' if runtime else '')+condition
                rows.append(analyze(folder/name))
    assert len(rows)==16
    for row in rows:
        if not row['runtime']:assert row['groups'][3]['joint']==0
    clock=BASE/'diagnostics/state-clock-transfer-2154.json'
    clocks=json.loads(clock.read_text())
    assert clocks['encoder_unchanged'] and all(d['physics_records_rescored_exact'] for d in clocks['datasets'])
    result=dict(rows=rows,records_rescored_exact=True,component_selection_independently_verified=True,
        formal_physics_transitions=sum(r['actual_transitions'] for r in rows if not r['runtime']),
        runtime_physics_transitions=sum(r['actual_transitions'] for r in rows if r['runtime']),
        clock_diagnostic=clocks,
        scope='All conditions reuse development states. True-body/slider/both use live simulator state and are privileged diagnostics; never deployable student success. Independent NumPy rigid-transform and physical scoring checks passed. Different conditions induce different trajectories.')
    out.mkdir();prefix='wuji-state-components-final-20260922'
    (out/(prefix+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    conditions=['estimated','true_body','true_slider','true_both']
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,seconds in zip(axes,[2,5]):
        selected=[next(r for r in rows if not r['runtime'] and r['seconds']==seconds and r['condition']==c) for c in conditions]
        values=[sum(g['joint'] for g in r['groups'][:3]) for r in selected]
        bars=ax.bar(range(4),values,color=['#4c829e','#c5955a','#c5955a','#c5955a'])
        ax.bar_label(bars,labels=[str(v)+'/300' for v in values],padding=3)
        ax.set(xticks=range(4),xticklabels=['Estimated','True body','True slider','True both'],ylim=(0,330),title=f'{seconds} s commands',ylabel='Strict complete successes')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Frozen estimator: feedback component intervention')
    fig.text(.02,.01,'Three training grasps x100 perturbations; fourth grasp0/32 in every condition. Brown bars use current simulation truth.\nReused development data,20 s rollouts,2 mm endpoint holds; neither independent validation nor hardware.',fontsize=8)
    fig.tight_layout(rect=[0,.12,1,.94]);fig.savefig(out/(prefix+'-comparison.png'),dpi=160);plt.close(fig)
    (out/(prefix+'-README.md')).write_text('''# Wuji 状态估计组件诊断

|冻结策略输入|2秒指令 /300|5秒指令 /300|
|---|---:|---:|
|全部估计|168|51|
|刀身换成真值|190|136|
|滑块位移/速度换成真值|270|244|
|刀身和滑块都换成真值|299|299|

每项另有第四抓姿32次，全部失败。所有16项运行检查和正式评估均正常结束，所有物理评分从trace重算；组件选择和刚体运动学另用NumPy独立核对。混合条件使用当前仿真真值，仅是诊断，不能作为部署成功。完整成功/失败都保留。

同一冻结估计器在teacher2秒/5秒轨迹的留出30行上的滑块RMSE为0.740/0.702mm；其自行控制闭环时约2.25/2.84mm。慢节奏teacher数据上的误差并未显著恶化，因此仅补慢节奏teacher轨迹不足以解释闭环差距。此结果支持进一步检查自身轨迹分布偏移；不能据此证明仅有一个根因或本体感知不可能成功。

数据全部属于已经观察的开发集。拟合60行、留出30行使用同一固定划分，另有210开发行及第四抓姿32行；不是332个独立抓姿。公开证据包含16份报告/混合状态trace/物理评分trace、5秒teacher收集数据、固定权重来源与分析源码；大型原始物理trace在两端保留，其SHA256列于results。时变误差与动作反馈导致的轨迹变化需要后续训练检验。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            folder=Path(row['folder']);name=folder.parent.name+'/'+folder.name
            for p in folder.iterdir():
                if p.is_file() and (p.suffix in ['.json','.yaml','.py'] or p.name=='hybrid-trace.npz'):
                    archive.write(p,name+'/'+p.name)
            with np.load(folder/'trace.npz') as z:
                values={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            stream=io.BytesIO();np.savez_compressed(stream,**values)
            archive.writestr(name+'/metric-trace.npz',stream.getvalue())
        second=BASE/'diagnostics/state-second-clock-2146-v1/collection'
        for name in ['history-state-pairs.npz','dataset-manifest.json','report.json','config.yaml']:
            archive.write(second/name,'second-clock/'+name)
        for p in [Path(__file__),ROOT/'scripts/analyze_wuji_state_component_probes.py',
                  ROOT/'scripts/analyze_wuji_state_clock_transfer.py',ROOT/'scripts/probe_wuji_fitted_state_components.py',
                  ROOT/'scripts/collect_wuji_state_fit_multiclock.py',ROOT/'scripts/wuji_physical_state_encoder.py',
                  ROOT/'scripts/wuji_timed_command_metrics.py',clock,
                  BASE/'diagnostics/state-endpoint-bias-2148-v2.json',ROOT/'scripts/analyze_wuji_state_endpoint_bias.py']:
            archive.write(p,'source/'+p.name)
        artifact=BASE/'diagnostics/state-scale-2036-v1/artifacts/precision_units.pth'
        archive.write(artifact,'artifacts/'+artifact.name)
        archive.write(artifact.with_suffix('.json'),'artifacts/precision_units.json')
    files=sorted(out.iterdir())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),formal=result['formal_physics_transitions'],runtime=result['runtime_physics_transitions'],files=[(p.name,p.stat().st_size) for p in out.iterdir()])))


if __name__=='__main__':main()
