"""Publish the position/velocity split, preserving the cross-host queue handoff."""
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

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'runs/wuji-goal'


def main():
    folders=[BASE/'diagnostics/slider-components-2s-2219-v1',BASE/'diagnostics/slider-components-5s-2219-v1',
        BASE/'diagnostics/slider-components-5s-remaining-2234-v1']
    out=BASE/'release-slider-components-final-20260922';assert not out.exists()
    state=[json.loads((p/'status.json').read_text()) for p in folders]
    assert [s['status'] for s in state]==['completed','stopped_handoff','completed']
    assert [len(s['stages']) for s in state]==[8,5,3]
    assert all(item['status']=='completed' and item['returncode']==0 for s in state for item in s['stages'])
    rows=[]
    for folder in folders:
        for p in sorted(folder.glob('*/')):
            if (p/'hybrid-state-audit.json').exists():rows.append(analyze(p))
    assert len(rows)==16
    assert len({(r['seconds'],r['condition'],r['runtime']) for r in rows})==16
    assert all(r['groups'][3]['joint']==0 for r in rows if not r['runtime'])
    result=dict(rows=rows,records_rescored_exact=True,component_selection_independently_verified=True,
        formal_transitions=sum(r['actual_transitions'] for r in rows if not r['runtime']),
        runtime_transitions=sum(r['actual_transitions'] for r in rows if r['runtime']),
        queue_states=state,scope='Frozenposition/velocityoracleandzero-velocityablation. Estimated/zerovelocityusenocurrenttruth;position/velocitytruthconditionsareprivilegeddiagnostics. Existingdevelopmentstates;notindependentorhardware.')
    out.mkdir();prefix='wuji-slider-components-final-20260922'
    (out/(prefix+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    conditions=['estimated','true_slider_position','true_slider_velocity','zero_slider_velocity'];numbers={}
    fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True)
    for ax,seconds in zip(axes,[2,5]):
        values=[next(r['joint'] for r in rows if not r['runtime'] and r['condition']==c and r['seconds']==seconds) for c in conditions]
        numbers[seconds]=values
        bars=ax.bar(range(4),values,color=['#44849e','#c79452','#c79452','#44849e']);ax.bar_label(bars,padding=4)
        ax.set(xticks=range(4),xticklabels=['Estimated','True position','True velocity','Zero velocity'],ylim=(0,310),ylabel='Strict successes /300',title=f'{seconds} s commands')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Frozen observer: split slider position and velocity feedback')
    fig.text(.02,.015,'Brown bars use live simulation truth. Blue bars use joint/action history and known initial values only.\nThree training grasps x100 perturbations; fourth grasp0/32 throughout. Reused development data,all failures included.',fontsize=8)
    fig.tight_layout(rect=[0,.12,1,.94]);fig.savefig(out/(prefix+'-comparison.png'),dpi=160);plt.close(fig)
    text='''# 滑块位置/速度细分诊断

|条件|2秒指令 /300|5秒指令 /300|
|---|---:|---:|
'''
    for i,name in enumerate(['全部估计','滑块位置真值','滑块速度真值','滑块速度置零']):text+=f'|{name}|{numbers[2][i]}|{numbers[5][i]}|\n'
    text+='''
第四抓姿均0/32。16项运行检查/正式评估完成并逐条重算，1,593,600正式物理转移。位置替换时移动link位置仍按同一刀身和关节运动学重构，速度替换只改速度。组件选择、单位和运动学由NumPy独立复核。estimated/zero速度运行检查还逐步反事实修改当前私有状态，预测、动作和actor记忆保持相等。

两种真值条件仅用于定位，不能当可部署成功。成功数差异支持位置估计的重要性，但不同闭环诱发不同轨迹，不能将差值看成相互独立的因果贡献。速度置零虽然不读取当前真值，也只是消融对照。

5秒队列在八卡完成全部4项runtime和estimated正式评估后，确认无子任务，仅停止空闲调度器。剩余3项正式评估转到四卡空闲GPU1，执行源码仍是同一不可变pin。原状态、停止前状态、移交程序和新状态均保留。没有停止物理子进程，没有重复已完成评分。

全部是观察过的开发状态，三个训练抓姿各100扰动和第四抓姿32。原始大物理trace保留在两端，摘要列SHA；ZIP包含完整评分trace、混合状态trace、报告及代码。没有独立泛化或真机成功声明。
'''
    (out/(prefix+'-README.md')).write_text(text)
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            p=Path(row['folder']);name=p.parent.name+'/'+p.name
            for f in p.iterdir():
                if f.is_file() and (f.suffix in ['.json','.yaml','.py'] or f.name=='hybrid-trace.npz'):archive.write(f,name+'/'+f.name)
            with np.load(p/'trace.npz') as z:values={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            stream=io.BytesIO();np.savez_compressed(stream,**values);archive.writestr(name+'/metric-trace.npz',stream.getvalue())
        for folder in folders:
            for p in folder.glob('*.json'):archive.write(p,'queues/'+folder.name+'/'+p.name)
        for p in [Path(__file__),ROOT/'scripts/probe_wuji_fitted_state_components.py',ROOT/'scripts/analyze_wuji_state_component_probes.py',
            ROOT/'scripts/wuji_physical_state_encoder.py',ROOT/'scripts/wuji_timed_command_metrics.py',
            BASE/'diagnostics/slider-components-5s-handoff-2234.py',BASE/'student-slider-components-2219-v1-proposal.json']:
            archive.write(p,'source/'+p.name)
    files=sorted(out.iterdir());(out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),numbers=numbers,files=[(p.name,p.stat().st_size) for p in out.iterdir()])))


if __name__=='__main__':main()
