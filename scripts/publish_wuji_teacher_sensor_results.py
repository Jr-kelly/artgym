"""Publish all completed teacher sensor interventions, including failures."""
import argparse
import hashlib
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=json.loads(args.analysis.read_text())
    assert result['records_rescored_exact'] and result['interventions_independently_checked']
    assert len(result['rows'])==40
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    prefix='wuji-teacher-feedback-tolerance-20260922'
    rows=[r for r in result['rows'] if not r['runtime']]
    modes=[r['mode'] for r in rows if r['seconds']==2]
    labels=['Full state','Body 0.5 mm','Body 2 mm','Rotation 0.5 deg','Rotation 2 deg',
            'Slider 0.25 mm','Slider 1 mm','Delay 33 ms','Delay 100 ms','Delay 200 ms']
    fig,axes=plt.subplots(1,2,figsize=(13,5.8),sharey=True)
    for ax,sec in zip(axes,[2,5]):
        selected=[r for r in rows if r['seconds']==sec]
        assert [r['mode'] for r in selected]==modes
        y=np.arange(len(selected))
        ax.barh(y,[r['joint'] for r in selected],color=['#347e9c']*7+['#c48739']*3)
        for i,r in enumerate(selected):
            ax.text(r['joint']+3,i,str(r['joint']),va='center',fontsize=9)
        ax.invert_yaxis()
        ax.set(yticks=y,yticklabels=labels,xlim=(0,328),xticks=[0,100,200,300],
               xlabel='20 s strict joint success / 300',title='%d s fixed commands'%sec)
        ax.grid(axis='x',alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Frozen Wuji teacher: sensitivity to feedback error and delay')
    fig.text(.02,.015,'Each bias acts alone in a fixed per-environment direction/sign. Delays affect coherent body/link/articulation state.\nThree training grasps x100 development perturbations; fourth grasp 0/32 in all conditions. Strict 2 mm endpoints and body stability.\nLive privileged measurements: controller diagnostic, not student or hardware validation. All 40 runtime/formal physical traces independently rescored.',fontsize=8)
    fig.tight_layout(rect=[0,.12,1,.96])
    fig.savefig(args.output/(prefix+'-comparison.png'),dpi=170)
    plt.close(fig)
    shutil.copy2(args.analysis,args.output/(prefix+'-results.json'))
    table=['|Condition|2 s /300|5 s /300|','|---|---:|---:|']
    for mode in modes:
        table.append('|%s|%d|%d|'%(mode,*[next(r['joint'] for r in rows if r['seconds']==sec and r['mode']==mode) for sec in [2,5]]))
    readme='# Wuji teacher 反馈精度与延迟\n\n'+'\n'.join(table)+'\n\n'+\
        '全部40项（运行检查20项、正式20项）正常退出，逐条重算物理评分及验证输入干预；正式3,984,000转移，运行检查36,000转移。'+\
        '同一冻结teacher、相同332开发初态。当前刀身、滑块和移动link输入以一致运动学重构；critic、动作控制和物理真值不改。'+\
        '小偏差是各自独立且全程固定方向/符号，不代表时间变化噪声的可接受范围，更不能代表真实传感器性能。'+\
        '延迟组同时延迟当前物体反馈；这些结果表明本控制器对时序敏感，不能直接断言student的失败就是延迟导致。'+\
        '证据包包含全部干预输入trace、物理评分trace、配置、报告、程序和运行状态；完整原始物理trace留在本机及远端，其SHA256见results。\n'
    (args.output/(prefix+'-README.md')).write_text(readme)
    with zipfile.ZipFile(args.output/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for sec in [2,5]:
            folder=BASE/'diagnostics'/('teacher-sensor-%ds-1957-v1'%sec)
            archive.write(folder/'status.json','%ds/status.json'%sec)
            for runtime in [True,False]:
                for mode in modes:
                    name=('runtime-' if runtime else '')+mode
                    trial=folder/name
                    for f in trial.iterdir():
                        if f.is_file() and (f.suffix in ['.json','.yaml','.py'] or f.name=='input-trace.npz'):
                            archive.write(f,'%ds/%s/%s'%(sec,name,f.name))
                    with np.load(trial/'trace.npz') as z:
                        trace={k:z[k] for k in ['active','fall','invalid','slider','goal','drift','rotation']}
                    import io
                    stream=io.BytesIO()
                    np.savez_compressed(stream,**trace)
                    archive.writestr('%ds/%s/metric-trace.npz'%(sec,name),stream.getvalue())
        for f in [Path(__file__),ROOT/'scripts/analyze_wuji_teacher_sensor_accuracy.py',
                  ROOT/'scripts/probe_wuji_teacher_sensor_accuracy.py',ROOT/'scripts/wuji_timed_command_metrics.py']:
            archive.write(f,'source/'+f.name)
    files=sorted(p for p in args.output.iterdir() if p.is_file())
    (args.output/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(args.output)


if __name__=='__main__':
    main()
