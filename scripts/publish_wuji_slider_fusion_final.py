"""Preserve the complete slider-only correction comparison, including failure."""
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
    run=BASE/'diagnostics/slider-fusion-2254-v1';out=BASE/'release-slider-fusion-final-20260922'
    assert not out.exists()
    status=json.loads((run/'status.json').read_text());assert status['status']=='completed'
    assert all(s['status']=='completed' and s['returncode']==0 for s in status['stages'])
    rows=[analyze(p.parent) for p in sorted(run.glob('*/state-estimation-audit.json'))];assert len(rows)==8
    for r in rows:
        if r['num_envs']==332:assert r['groups'][3]['joint']==0
    fitting=json.loads((run/'fitting/status.json').read_text());assert fitting['status']=='completed'
    final={arm:[next(r['joint'] for r in rows if Path(r['folder']).name==f'{arm}-mixed332-{seconds}s')
        for seconds in [2,5]] for arm in ['raw','kinematic']}
    assert final==dict(raw=[88,96],kinematic=[114,167])
    result=dict(rows=rows,fitting=fitting,all8_rescored=True,final=final,denominator=300,
        physics_transitions=sum(r['actual_transitions'] for r in rows),scope=__doc__,
        independent_generalization=False,hardware=False)
    out.mkdir();prefix='wuji-slider-fusion-final-20260922'
    (out/(prefix+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,i in zip(axes,range(2)):
        values=[[168,51][i],final['raw'][i],final['kinematic'][i]]
        bars=ax.bar(range(3),values,color=['#85919a','#c88b50','#337d9e']);ax.bar_label(bars,padding=4)
        ax.set(xticks=range(3),xticklabels=['Original TCN','Raw residual','With URDF geometry'],ylim=(0,310),
            ylabel='Strict successes /300',title=f'{[2,5][i]} s commands')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Slider-only correction: full frozen evaluation')
    fig.text(.02,.02,'Same four data sources and fixed ridge penalty. Only slider position changes; body, velocity and teacher remain frozen.\nThree training grasps x100 perturbations; fourth grasp0/32. Existing development states; no independent success claim.',fontsize=8)
    fig.tight_layout(rect=[0,.11,1,.94]);fig.savefig(out/(prefix+'-comparison.png'),dpi=160);plt.close(fig)
    (out/(prefix+'-README.md')).write_text('''# 滑块位置修正完整配对结果

|模型|快速 /300|慢速 /300|
|---|---:|---:|
|原始冻结TCN|168|51|
|raw线性残差|88|96|
|追加URDF几何残差|114|167|

第四抓姿均0/32。两组均只修正滑块位置，原TCN、刀身6维、速度和teacher保持。相同四来源teacher/student快慢轨迹、36000训练标签、每源60训练/30留出初态、训练行归一化，固定ridge均方惩罚0.01，一次求解，无参数扫描。raw103维；kinematic追加15维接触点位移、9维拇指旋转变化和1维不滑几何先验，合计128维。推理仅用因果关节/动作、初始字段及冻结TCN预测，没有物体/接触真值。

固定student快/慢留出轨迹滑块RMSE：原模型1.702/2.420mm，raw1.224/1.171mm，kinematic1.175/1.031mm。teacher留出误差相较原模型略有上升。几何组改善raw闭环，但两组仍未可靠，不能从离线误差下降推断控制成功。

独立线性求解、训练行归一化、原始历史重算、仅第6维改变、零残差恢复原模型检查通过。四次实际runtime检查中，FK指尖与仿真最大差小于0.5微米，修改当前物体/接触真值不改变动作或actor记忆；四次正式332初态及四次runtime报告从trace重算，共804000物理转移。

332为三训练抓姿各100扰动及第四抓姿32，是已有开发集，包含拟合初态。评估要求20秒每次指令末0.3秒保持2mm内、刀身全程10mm/0.25rad内并存活。尚无新的独立验证、几何泛化或真机成功。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            p=Path(row['folder']);name=p.name
            for f in p.iterdir():
                if f.is_file() and (f.suffix in ['.json','.yaml','.py'] or f.name=='estimation-trace.npz'):
                    archive.write(f,name+'/'+f.name)
            with np.load(p/'trace.npz') as z:values={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            stream=io.BytesIO();np.savez_compressed(stream,**values);archive.writestr(name+'/metric-trace.npz',stream.getvalue())
        for arm in ['raw','kinematic']:
            p=run/'fitting'/f'{arm}.pth'
            assert hashlib.sha256(p.read_bytes()).hexdigest()==json.loads(p.with_suffix('.json').read_text())['sha256']
            archive.write(p,'artifacts/'+p.name);archive.write(p.with_suffix('.json'),'artifacts/'+p.with_suffix('.json').name)
        for p in [run/'status.json',run/'fitting/status.json']:archive.write(p,'training/'+str(p.relative_to(run)))
        for name in ['publish_wuji_slider_fusion_final.py','fit_wuji_slider_fusion.py','wuji_slider_fusion.py',
            'analyze_wuji_kinematic_slider.py','wuji_kinematics.py','audit_wuji_slider_fusion.py',
            'eval_wuji_fitted_state_encoder.py','analyze_wuji_state_encoder_evaluations.py','wuji_timed_command_metrics.py']:
            archive.write(ROOT/'scripts'/name,'source/'+name)
        for p in [BASE/'student-slider-fusion-2254-v1-proposal.json',BASE/'diagnostics/slider-fusion-offline-audit-2256.json',
            BASE/'diagnostics/kinematic-slider-prior-2250-v1.json']:archive.write(p,'source/'+p.name)
    files=sorted(out.iterdir());(out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),final=final,reports=len(rows),files=[(p.name,p.stat().st_size) for p in out.iterdir()])))


if __name__=='__main__':main()
