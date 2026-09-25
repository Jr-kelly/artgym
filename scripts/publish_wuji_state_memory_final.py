"""Archive the full persistent-memory/reset-memory paired experiment."""
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

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'runs/wuji-goal'


def main():
    run=BASE/'diagnostics/state-memory-2227-v2';out=BASE/'release-state-memory-final-20260922'
    assert not out.exists()
    status=json.loads((run/'status.json').read_text());assert status['status']=='completed'
    assert all(s['status']=='completed' and s['returncode']==0 for s in status['stages'])
    rows=[analyze(p.parent) for p in sorted(run.glob('*/state-estimation-audit.json'))]
    assert len(rows)==20
    for row in rows:
        if row['num_envs']==332:assert row['groups'][3]['joint']==0
    fitting=json.loads((run/'fitting/status.json').read_text())
    assert fitting['status']=='completed' and fitting['updates_completed']==1000
    assert fitting['optimizer_counters_verified']
    final={arm:[next(r['joint'] for r in rows if Path(r['folder']).name==f'{arm}-cp1000-mixed332-{seconds}s')
                for seconds in [2,5]] for arm in ['persistent','reset_each_step']}
    result=dict(rows=rows,training=fitting,validations=json.loads((run/'fitting/validation.json').read_text()),
        all20_rescored=True,final=final,denominator=300,
        scope='Paired 64D GRU residual, persistent memory versus per-step zero memory. Frozen TCN, teacher and normalization. Four data sources, 1000 updates each. Reused development states; no independent success claim.')
    out.mkdir();prefix='wuji-state-memory-final-20260922'
    (out/(prefix+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,i in zip(axes,range(2)):
        values=[[168,51][i],final['persistent'][i],final['reset_each_step'][i]]
        bars=ax.bar(range(3),values,color=['#85919a','#337d9e','#b67c41']);ax.bar_label(bars,padding=4)
        ax.set(xticks=range(3),xticklabels=['Initial TCN','Persistent GRU','Reset GRU'],ylim=(0,310),
            ylabel='Strict successes /300',title=f'{[2,5][i]} s commands')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Final 1000 updates: causal memory alone remains insufficient')
    fig.text(.02,.02,'Same initialization, data and sample budget. Both arms preserve the original frozen state estimator and teacher.\nThree training grasps x100 perturbations; fourth grasp0/32. Existing development states; all outcomes included.',fontsize=8)
    fig.tight_layout(rect=[0,.11,1,.94]);fig.savefig(out/(prefix+'-comparison.png'),dpi=160);plt.close(fig)
    (out/(prefix+'-README.md')).write_text(f'''# 因果记忆估计器配对完整结果

|模型|快速 /300|慢速 /300|
|---|---:|---:|
|原始冻结TCN|168|51|
|persistent最终1000|{final['persistent'][0]}|{final['persistent'][1]}|
|reset_each_step最终1000|{final['reset_each_step'][0]}|{final['reset_each_step'][1]}|

第四抓姿全部0/32。64维单层GRU残差，起始输出头为零，原TCN、teacher及其归一化冻结；两组相同初始化/训练序列/1000次Adam2e-4更新，唯一记忆控制是每步是否清零。每组240万监督标签、955.2万真实因果传感器帧；离线拟合无新增物理步。

用4套已保存teacher/student快慢轨迹，每源60拟合初态/30留出初态。从重叠历史精确恢复597个30Hz输入，仍只使用150个实际记录标签，不插值标签。推理不读取当前物体/接触真值或目标时钟。参数、动作、历史、真值扰动不变性和记忆有效性均独立检查；20份运行检查和正式评估逐条重算。

CP250 persistent为121/116，reset为100/129。最终结果和中期结果全部保留。离线误差降低不能当作闭环可靠性或泛化成功。第一版cuDNN预检失败、CPU/GPU数值容差澄清及修正第二版均另有公开记录。

332为三训练抓姿各100个扰动加第四抓姿32，包含拟合初态，是开发集。严格标准仍为20秒、各指令末0.3秒误差小于2mm、刀身全程小于10mm/0.25rad并存活；不是论文10mm评估，也不是硬件验证。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            p=Path(row['folder']);name=p.name
            for f in p.iterdir():
                if f.is_file() and (f.suffix in ['.json','.yaml','.py'] or f.name=='estimation-trace.npz'):
                    archive.write(f,name+'/'+f.name)
            with np.load(p/'trace.npz') as z:values={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            stream=io.BytesIO();np.savez_compressed(stream,**values);archive.writestr(name+'/metric-trace.npz',stream.getvalue())
        for arm in ['persistent','reset_each_step']:
            p=run/'fitting'/f'{arm}-update1000.pth'
            assert hashlib.sha256(p.read_bytes()).hexdigest()==json.loads(p.with_suffix('.json').read_text())['sha256']
            archive.write(p,'artifacts/'+p.name);archive.write(p.with_suffix('.json'),'artifacts/'+p.with_suffix('.json').name)
        for p in [run/'status.json',run/'fitting/status.json',run/'fitting/validation.json',run/'preflight/status.json']:
            archive.write(p,'training/'+str(p.relative_to(run)))
        data=BASE/'diagnostics/state-memory-2225-v1/data'
        for p in [data/'memory-features.npz',data/'manifest.json']:archive.write(p,'data/'+p.name)
        for p in [Path(__file__),ROOT/'scripts/fit_wuji_state_memory_pair.py',ROOT/'scripts/prepare_wuji_state_memory_data.py',
            ROOT/'scripts/wuji_state_memory.py',ROOT/'scripts/eval_wuji_state_memory.py',ROOT/'scripts/audit_wuji_memory_data.py',
            ROOT/'scripts/audit_wuji_state_memory_runtime.py',ROOT/'scripts/analyze_wuji_state_encoder_evaluations.py',
            ROOT/'scripts/wuji_timed_command_metrics.py',BASE/'diagnostics/state-memory-fit-and-runtime-audit-2242.json',
            BASE/'student-state-memory-2227-v2-proposal.json']:
            archive.write(p,'source/'+p.name)
    files=sorted(out.iterdir());(out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),reports=len(rows),final=final,files=[(p.name,p.stat().st_size) for p in out.iterdir()])))


if __name__=='__main__':main()
