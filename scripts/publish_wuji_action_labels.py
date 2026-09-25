"""Package six frozen action-label diagnostics, preserving failures and scores."""
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
from scripts.wuji_timed_command_metrics import score_timed_trace

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/wuji-goal'


def main():
    out=BASE/'release-action-labels-20260922'
    out.mkdir(exist_ok=False)
    evidence=out/'evidence';evidence.mkdir()
    prefix='wuji-action-labels-20260922'
    records=[];hashes={};phases=[]
    colors=['#348799','#cb8d38','#885b8d']
    names=['initial','head100','actor100']
    captions=['Initial','Output layer CP100','Full actor CP100']
    fig,axes=plt.subplots(2,3,figsize=(11.5,7))

    def copy(path,target):
        shutil.copy2(path,evidence/target)
        hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()

    for ri,sec in enumerate([2,5]):
        analysis=BASE/'diagnostics'/('action-label-analysis-%ds-final-1855.json'%sec)
        data=json.loads(analysis.read_text());assert data['complete']
        copy(analysis,analysis.name)
        directory=BASE/'diagnostics'/('action-label-probe-%ds-1845-v1'%sec)
        copy(directory/'status.json','%ds-status.json'%sec)
        for ci,name in enumerate(names):
            b=directory/name
            report=json.loads((b/'report.json').read_text())
            check=json.loads((b/'label-probe-report.json').read_text())
            assert check['status']=='passed' and check['checks']['actual_student_actions']==199200
            with np.load(b/'trace.npz') as a:
                physics={k:a[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
            assert score_timed_trace(physics,sec*30,9,600)['records']==report['records']
            case='%ds-%s'%(sec,name)
            np.savez_compressed(evidence/(case+'-metric-trace.npz'),**physics)
            for p in b.iterdir():
                if p.is_file() and p.suffix in ['.json','.py','.yaml']:
                    copy(p,case+'-'+p.name)
            for file in ['trace.npz','action-label-trace.npz']:
                hashes[str((b/file).relative_to(ROOT))]=hashlib.sha256((b/file).read_bytes()).hexdigest()
            with np.load(b/'action-label-trace.npz') as a:
                assert np.array_equal(a['active'],physics['active'])
                executed_error=(a['student_action'].astype(np.float64)-a['teacher_action'].astype(np.float64))
                pre_goal=a['goal'];pre_slider=a['slider'];active=a['active']
            row=dict(seconds=sec,candidate=name,joint=[],alive=[],body=[],analysis=[])
            for gi,grasp in enumerate(['source','row16','row15','fourth']):
                ids=slice(100*gi,min(100*(gi+1),332))
                group=report['records'][ids]
                survivors=np.array([x['alive_full'] for x in group])
                row['joint'].append(sum(x['stable_full_all_endpoints'] for x in group))
                row['alive'].append(int(survivors.sum()))
                row['body'].append(int(((physics['drift'][:,ids]<.01)&(physics['rotation'][:,ids]<.25)).all(0).astype(bool).__and__(survivors).sum()))
                found=[x for x in data['rows'] if x['candidate']==name and x['grasp']==grasp and x['population']=='active' and x['command']=='all']
                row['analysis'].append(found[0] if found else None)
                for population in ['active','full_survivors']:
                    for command in ['open','close']:
                        mask=active[:,ids].copy()
                        if population=='full_survivors':mask &= survivors[None,:]
                        # Pre-action label/goal phase. The independent scorer
                        # continues to use its original post-action trace.
                        mask &= (pre_goal[:,ids]>-.01)==(command=='open')
                        for phase in ['all','first9','last9']:
                            selected=mask.copy();index=np.arange(600)%(sec*30)
                            if phase=='first9':selected &= index[:,None]<9
                            if phase=='last9':selected &= index[:,None]>=sec*30-9
                            if not selected.any():continue
                            e=executed_error[:,ids][selected]
                            slider_error=1000*(pre_slider[:,ids]-pre_goal[:,ids])[selected]
                            phases.append(dict(seconds=sec,candidate=name,grasp=grasp,population=population,
                                command=command,phase=phase,transitions=int(selected.sum()),
                                per_joint_executed_signed_error=e.mean(0).tolist(),
                                per_joint_executed_mse=(e*e).mean(0).tolist(),
                                pre_action_slider_error_mean_mm=float(slider_error.mean()),
                                pre_action_slider_absolute_error_mean_mm=float(np.abs(slider_error).mean())))
                if gi<3:
                    ax=axes[ri,gi];x=found[0]['mapped_thumb_target_rmse_mrad'];y=row['joint'][-1]
                    ax.scatter(x,y,color=colors[ci],s=75,marker=['o','s','^'][ci],label=captions[ci])
                    ax.annotate(str(y),(x,y),xytext=(5,5),textcoords='offset points',fontsize=8)
                    ax.set(title=grasp+' / %ds commands'%sec,xlabel='Thumb mapped-target RMSE (mrad)',
                           ylabel='Strict 20s joint success /100',ylim=(-3,105))
                    ax.grid(alpha=.2)
            records.append(row)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.945),ncol=3,frameon=False)
    fig.suptitle('Smaller action error does not ensure complete knife cycles')
    fig.text(.02,.012,'Student alone drives physics; frozen teacher labels have separate recurrent history. Mapped targets are before actuator smoothing.\nEach candidate visits its own closed-loop states: descriptive comparison, not fixed-input causality. Same332 development states; fourth grasp0/32.\nStrict score: every command last0.3s <2mm, full body <10mm /0.25rad, alive and finite. No independent or hardware validation.',fontsize=8)
    fig.tight_layout(rect=[0,.11,1,.88]);fig.savefig(out/(prefix+'-error-vs-success.png'),dpi=170);plt.close(fig)
    for p in [Path(__file__),ROOT/'scripts/analyze_wuji_action_labels.py',ROOT/'scripts/probe_wuji_action_labels.py',
              ROOT/'scripts/wuji_timed_command_metrics.py',BASE/'action-label-probe-1845-v1-proposal.json']:
        copy(p,p.name)
    copy(BASE/'diagnostics/action-label-probe-2s-1845-v1/runtime/label-probe-report.json','runtime-2s.json')
    copy(BASE/'diagnostics/action-label-probe-5s-1845-v1/runtime/label-probe-report.json','runtime-5s.json')
    (out/(prefix+'-phases.json')).write_text(json.dumps(dict(rows=phases,note='Pre-action phases; active and full-survivor populations are explicitly separate.'),indent=2)+'\n')
    provenance=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),records=records,
        formal_transitions=1195200,runtime_transitions=3600,all_records_rescored_exact=True,
        raw_trace_and_source_sha256=hashes,
        evidence_scope='Metric traces permit exact success rescoring. Action-label aggregate and phase statistics are supplied; full action-label traces retained locally and on remote with SHA256 identities, not included in this smaller publication.')
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    table=['|模型|快速成功/300|慢速成功/300|','|---|---:|---:|']
    for name,caption in zip(names,captions):
        values=[sum(next(x for x in records if x['candidate']==name and x['seconds']==s)['joint'][:3]) for s in [2,5]]
        table.append('|%s|%d|%d|'%(caption,*values))
    (out/(prefix+'-README.md')).write_text('# Wuji 动作标签诊断\n\n'+ '\n'.join(table)+
        '\n\n六项冻结模型闭环诊断及两项运行检查全部通过，学生独立驱动物理，teacher仅提供标签且保有独立RNN历史。'
        '全部成功计数与原trace逐条重算一致。332为三训练抓姿各100扰动及第四抓姿32扰动，第四全部失败；这是复用开发集。\n\n'
        '完整actor第三抓姿快速：拇指映射目标RMSE从4.311降到2.760mrad，完整成功从80降到10/100。'
        '平均动作误差降低仍伴随端点精度和刀身稳定性损失，不能把MSE改善当任务成功。初始被动作裁剪完全消去的原始误差仅约0.1–3.7%，不支持裁剪项主导。'
        '不同候选的误差来自各自闭环状态，不能作相同输入的因果结论。\n\n'
        'phases报告按打开/关闭、开始/末尾9帧拆分动作有符号偏差和滑块误差，区分活跃样本与全程存活条件。'
        '标签在动作前记录，成功评分仍使用原动作后轨迹。\n\n'
        '证据包含全部原报告、可重评分的物理列、统计与源码；完整动作标签trace保存于本机及服务器，SHA256列于provenance。未做独立泛化或真机验证。\n')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()):z.write(p,p.name)
    files=sorted(p for p in out.iterdir() if p.is_file())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out),reports=len(records),files=len(files)+1)))


if __name__=='__main__':main()
