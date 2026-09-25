"""Preserve all fixed-data aggregation outcomes, including the failed final model."""
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
    run=BASE/'diagnostics/state-aggregation-2207-v1';out=BASE/'release-state-aggregation-final-20260922'
    assert not out.exists()
    status=json.loads((run/'status.json').read_text());assert status['status']=='completed'
    assert all(s['status']=='completed' and s['returncode']==0 for s in status['stages'])
    rows=[]
    for p in sorted(run.glob('*/')):
        if (p/'state-estimation-audit.json').exists():rows.append(analyze(p))
    assert len(rows)==16
    for row in rows:
        if row['num_envs']==332:assert row['groups'][3]['joint']==0
    fitting=json.loads((run/'fitting/status.json').read_text())
    assert fitting['status']=='completed' and fitting['updates_completed']==1000
    assert set(fitting['supervised_counts'].values())=={512000}
    gates=json.loads((BASE/'diagnostics/state-aggregation-gates-2206.json').read_text())
    validations=json.loads((run/'fitting/validation.json').read_text())
    result=dict(rows=rows,training=fitting,gates=gates,validations=validations,all16_rescored=True,
        scope='One fixed dataset-aggregation round. Sameinitialencoder,1000Adam2e-5updates,batch512. Teacher-only vs50%teacher/50%frozenstudentowntrajectories. Bothclocksbalanced. Existingdevelopmentstates;notindependentgeneralizationorhardware.',
        fixed_final_fast_slow={'teacher_only':[183,188],'aggregated':[139,28]},denominator=300,fourth_grasp_failures=32)
    out.mkdir();prefix='wuji-state-aggregation-final-20260922'
    (out/(prefix+'-results.json')).write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,seconds in zip(axes,[2,5]):
        values=[168 if seconds==2 else 51]+[result['fixed_final_fast_slow'][arm][0 if seconds==2 else 1] for arm in ['teacher_only','aggregated']]
        bars=ax.bar(range(3),values,color=['#83909b','#4583a0','#be7740']);ax.bar_label(bars,padding=4)
        ax.set(xticks=range(3),xticklabels=['Initial','Teacher data','Mixed own data'],ylim=(0,310),ylabel='Strict successes /300',title=f'{seconds} s commands')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Fixed-data fitting: final1000 updates, frozen closed-loop evaluation')
    fig.text(.02,.015,'Same weights at start and same sample budget. Mixed-data model lowers heldout own-trajectory slider RMSE but reduces closed-loop success.\nThree training grasps x100perturbations; fourthgrasp0/32. Reused development states; all failures included.',fontsize=8)
    fig.tight_layout(rect=[0,.12,1,.94]);fig.savefig(out/(prefix+'-comparison.png'),dpi=160);plt.close(fig)
    (out/(prefix+'-README.md')).write_text('''# 固定数据聚合完整结果

|冻结模型|快速 /300|慢速 /300|
|---|---:|---:|
|共同初始模型|168|51|
|teacher_only最终1000|183|188|
|aggregated最终1000|139|28|

第四抓姿所有条件0/32。两组同初始权重、新Adam2e-5、1000更新、batch512。teacher_only使用2/5秒teacher数据；aggregated一半teacher、一半同初始student自己产生的轨迹，两时钟均衡。控制器、物理、成功标准不变。正式512000监督样本/组，不把离线梯度当作新增物理步。

固定留出student轨迹滑块RMSE：起点1.702/2.420mm，teacher_only最终1.533/2.058mm，aggregated最终1.339/1.555mm。较低离线误差没有转换为更好的新闭环，混合组慢速显著退化。保留CP250和最终全部结果，不能挑中期峰值，也不能把某个误差指标下降称为完成任务。

16份运行检查/正式报告从实际trace逐条重算。收集每个时钟199200物理转移；所得物理评分逐行与原基线相等。每源60初态9000拟合帧、30初态4500留出帧，留出帧不参与梯度；物理开发集包含这些拟合初态，并非独立验证。预检实际2个Adam更新已由优化器计数核对，旧status末更新字段1是心跳记录问题，修正说明保留。

证据ZIP含16份报告/估计trace/评分trace、两个最终模型、所有拟合验证指标、两份冻结student自身数据和源码。不是论文latentMSE流程，也不表示真机或泛化成功。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            p=Path(row['folder']);name=p.name
            for f in p.iterdir():
                if f.is_file() and (f.suffix in ['.json','.yaml','.py'] or f.name in ['estimation-trace.npz','history-state-pairs.npz']):archive.write(f,name+'/'+f.name)
            with np.load(p/'trace.npz') as z:values={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            stream=io.BytesIO();np.savez_compressed(stream,**values);archive.writestr(name+'/metric-trace.npz',stream.getvalue())
        for arm in ['teacher_only','aggregated']:
            p=run/'fitting'/f'{arm}-update1000.pth'
            assert hashlib.sha256(p.read_bytes()).hexdigest()==json.loads(p.with_suffix('.json').read_text())['sha256']
            archive.write(p,'artifacts/'+p.name);archive.write(p.with_suffix('.json'),'artifacts/'+p.with_suffix('.json').name)
        for p in [run/'status.json',run/'fitting/status.json',run/'fitting/validation.json',run/'preflight/status.json']:
            archive.write(p,'training/'+str(p.relative_to(run)))
        for p in [Path(__file__),ROOT/'scripts/fit_wuji_state_aggregation_pair.py',ROOT/'scripts/audit_wuji_state_aggregation_data.py',
            ROOT/'scripts/eval_wuji_fitted_state_encoder.py',ROOT/'scripts/analyze_wuji_state_encoder_evaluations.py',
            ROOT/'scripts/wuji_timed_command_metrics.py',BASE/'diagnostics/state-aggregation-gates-2206.json',
            BASE/'diagnostics/state-aggregation-split-wording-2204.json',BASE/'student-state-aggregation-2207-v1-proposal.json']:
            archive.write(p,'source/'+p.name)
    files=sorted(out.iterdir());(out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),reports=len(rows),files=[(p.name,p.stat().st_size) for p in out.iterdir()])))


if __name__=='__main__':main()
