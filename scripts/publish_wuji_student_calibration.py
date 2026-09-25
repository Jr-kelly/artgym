"""Publish the bounded affine student test, including unsuccessful rollouts."""
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


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    out=base/'release-student-calibration-20260922';out.mkdir(exist_ok=False)
    evidence=out/'evidence';evidence.mkdir()
    prefix='wuji-knife-student-calibration-20260922'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    calibration=base/'frozen-candidates/student-cp500-affine-calibration-seed53/calibration.json'
    cal=json.loads(calibration.read_text());reports={};sources={}
    for mode in ['identity','affine']:
        for seconds in [2,5]:
            name='student-cp500-calibration-'+mode+'-fresh64-seed54-timed%dseconds'%seconds
            folder=base/'verification'/name
            status=json.loads((folder/'status.json').read_text());assert status['status']=='completed' and status['returncode']==0
            report=json.loads((folder/'report.json').read_text());extra=json.loads((folder/'calibration-report.json').read_text())
            assert extra['status']=='passed' and extra['model_unchanged'] and not extra['privileged_inputs_to_calibration']
            with np.load(folder/'trace.npz') as loaded:
                trace={k:loaded[k] for k in ['active','slider','goal','drift','rotation','fall','invalid']}
            scored=score_timed_trace(trace,seconds*30,9,600)
            assert all(report[k]==scored[k] for k in ['records','stable_full_all_endpoints','alive_full'])
            np.savez_compressed(evidence/(name+'-metric-trace.npz'),**trace)
            sources[str((folder/'trace.npz').relative_to(root))]=sha(folder/'trace.npz')
            for file in ['source.py','source_metrics.py','report.json','status.json','config.yaml','calibration-source.py','calibration-report.json']:
                p=folder/file;sources[str(p.relative_to(root))]=sha(p);shutil.copy2(p,evidence/(name+'-'+file))
            reports[mode+str(seconds)]=report
    assert len({r['initial_states_sha256'] for r in reports.values()})==1
    for folder in [base/'diagnostics/student-cp500-calibration-training32',base/'student-calibration-training-seed20261053',base/'student-calibration-fresh64-seed20261054']:
        for p in folder.iterdir():
            if p.is_file():
                sources[str(p.relative_to(root))]=sha(p);shutil.copy2(p,evidence/(folder.name+'-'+p.name))
    for p in [calibration,Path(__file__),root/'scripts/fit_wuji_student_latent_calibration.py']:
        sources[str(p.relative_to(root))]=sha(p);shutil.copy2(p,evidence/p.name)
    shutil.copy2(calibration,out/(prefix+'-frozen-affine-model.json'))
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.6));x=np.arange(2)
    for i,(label,values) in enumerate([('Original encoder',[cal['baseline_mse']['fit'],cal['baseline_mse']['validation']]),
                                     ('Affine calibration',[cal['selected']['fit_mse'],cal['selected']['validation_mse']])]):
        bars=axes[0].bar(x+(i-.5)*.34,values,.32,label=label)
        axes[0].bar_label(bars,fmt='%.3f',padding=3)
    axes[0].set(xticks=x,xticklabels=['24 fit trajectories','8 validation trajectories'],ylim=(0,.075),ylabel='Latent MSE on teacher trajectories',title='Small regression fit; frozen base encoder')
    for i,mode in enumerate(['identity','affine']):
        values=[reports[mode+str(s)]['stable_full_all_endpoints'] for s in [2,5]]
        bars=axes[1].bar(x+(i-.5)*.34,values,.32,label='Original student' if mode=='identity' else 'Affine student')
        axes[1].bar_label(bars,padding=3)
    axes[1].set(xticks=x,xticklabels=['2 s commands','5 s commands'],ylim=(0,80),ylabel='Joint successes / 64',title='New initial states after calibration was frozen')
    for ax in axes:
        ax.legend(loc='upper right',fontsize=8);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
    fig.text(.02,.015,'One training grasp. Every rollout lasts 20 s; all 64 survive in each condition. No privileged state enters calibrated inference.\nLower teacher-trajectory error has not produced reliable closed-loop control. All failures retained; simulation only.',fontsize=8)
    fig.tight_layout(rect=[0,.09,1,1]);fig.savefig(out/(prefix+'-regression-versus-control.png'),dpi=165);plt.close(fig)
    provenance=dict(reports=reports,calibration=cal,original_file_sha256=sources,scope=__doc__)
    (out/(prefix+'-all-trials-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    (out/(prefix+'-results.md')).write_text('''# Student 线性校准：误差下降仍不代表控制可靠

冻结 teacher、student CP500 和所有归一化统计；新增16×16线性映射和16维偏置，仅作用于原 student latent。推理只依赖原 student 的本体感知历史和初始观测，不读取当前物体真值，也不改变 actor。

先新生成seed53的32条teacher驱动轨迹。按完整环境轨迹划分：前24条拟合，后8条选择ridge系数。分别有14,400和4,800帧，它们不是这么多条独立轨迹。验证MSE从0.0490到0.0295；最优ridge为0.0001，映射最大奇异值约7.43，低回归误差不保证闭环稳健性。

模型冻结后另生成seed54的64个扰动初态，同一训练抓姿；原student与校准student配对测试，均20秒、同严格联合标准。所有64次都存活。

|推理模型|2秒指令联合|5秒指令联合|
|---|---:|---:|
|原student CP500|1/64|5/64|
|冻结线性校准student|9/64|7/64|

快速协议有小幅改善，但绝大多数仍不能持续准确开合，不能算可靠student。不要将本批原student的1/64与旧100样本的8/100视作同数据退化。ZIP包括四项全部评分轨迹、所有失败、拟合轨迹、初态、源码和冻结校准参数。本测试不是未见抓姿或真机验证。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()):z.write(p,p.name)
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(out.iterdir()) if p.is_file())+'\n')
    print(json.dumps(dict(output=str(out),assets=6,evaluations=4)))


if __name__=='__main__':main()
