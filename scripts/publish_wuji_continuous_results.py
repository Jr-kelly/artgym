"""Package measured continuous-control results and an uncut text-free video."""
import hashlib,json,shutil
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal/verification'
    out=root/'runs/wuji-goal/release-continuous-20260922-0430';out.mkdir(exist_ok=True)
    prefix='wuji-knife-continuous-cp25-20260922'
    keys=['successful_trials','strict_first_cycle_trials','stable_full_rollout_trials']
    names=['precision-near01-cp125-perturb-small','precision-cont-cost1-cp25-perturb100',
           'precision-cont-cost0-cp25-perturb100','precision-cont-cost1-cp25-blind-seed10103-perturb100',
           'precision-cont-cost1-cp25-blind-seed11213-perturb100',
           'student-precision125-pilot-cp100-blind-seed8147-perturb100',
           'student-precision125-pilot-cp100-blind-seed9257-perturb100']
    timed=['precision125-teacher-timed2seconds-perturb100','precision-cont-cost1-cp25-timed2seconds-perturb100',
           'precision125-student-timed2seconds-perturb100']
    names+=timed+[n.replace('timed2seconds','timed5seconds') for n in timed]
    reports={n:json.loads((base/n/'report.json').read_text()) for n in names}
    fig,axes=plt.subplots(1,3,figsize=(15,4.8))
    vals=[reports[n]['stable_full_rollout_trials'] for n in names[:5]]
    ax=axes[0];bars=ax.bar(range(5),vals,color=['#82959e','#277f9f','#549267','#277f9f','#277f9f'])
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+2,str(v),ha='center')
    ax.set_xticks(range(5),['Source\nDev','Cost 1\nDev','Cost 0\nDev','Cost 1\nFresh A','Cost 1\nFresh B'])
    ax.set_title('Stable full 20s: continuous cycles')
    for ax,seconds in zip(axes[1:],[2,5]):
        group=[n.replace('timed2seconds','timed%dseconds'%seconds) for n in timed]
        for j,(key,label,color) in enumerate([('all_commands_attained','All commands reached','#277f9f'),('all_endpoints_held','All endpoints held','#c58b39'),('stable_full_all_endpoints','Held + base stable','#549267')]):
            vals=[reports[n][key] for n in group]
            bars=ax.bar(np.arange(3)+(j-1)*.26,vals,.24,label=label,color=color)
            for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+2,str(v),ha='center',fontsize=8)
        ax.set_xticks(range(3),['Source\nteacher','Continuous\nteacher','Pilot\nstudent'])
        ax.set_title('External commands every %ds'%seconds)
    axes[2].legend(loc='upper right',fontsize=7)
    for ax in axes:
        ax.set_ylim(0,115);ax.set_ylabel('Trials / 100');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
    fig.text(.02,.02,'Same nominal grasp; initial position +/-0.5 mm/axis, joints +/-0.01 rad, rotation vector +/-0.5 deg/axis.\n'
        'Timed endpoint: final 0.3s within 2mm. Stable base: <10mm and <0.25rad for20s. No new-grasp or hardware claim.',fontsize=9)
    fig.tight_layout(rect=[0,.105,1,1]);fig.savefig(out/(prefix+'-evaluation.png'),dpi=160);plt.close(fig)
    video=base/'precision-cont-cost1-cp25-preset3-video'
    shutil.copy2(video/'policy.mp4',out/(prefix+'-three-perturbed-trials-no-text.mp4'))
    shutil.copy2(video/'preview.png',out/(prefix+'-preview.png'))
    sources={}
    for n,d in reports.items():
        sources[n]=dict(report_sha256=hashlib.sha256((base/n/'report.json').read_bytes()).hexdigest(),
                       report={k:v for k,v in d.items() if k!='records'})
    sources['video']=json.loads((video/'report.json').read_text())
    (out/(prefix+'-provenance.json')).write_text(json.dumps(sources,indent=2)+'\n')
    text="""# Wuji 连续精细开合与外部定时指令评估

视频为实际闭环学习策略：20 秒、600 帧、30 fps、1536×384，无文字叠加。左/中/右使用之前已经指定的扰动行 0/2/76，分别完成 12/12/13 次开合。三个均首次开合并稳定；全程稳定为 2/3，中间格转角达到 0.277 rad，超过 0.25 rad 标准，失败保留。视频为本机三环境结果，不能代替 H100 批量试验。

刀柄约 147×19×11 mm、35 g，滑块目标行程 40 mm。策略根据观测输出手的 20 个动作，物体基座自由、滑块被动，没有加载脚本关节轨迹。单个开合阶段要求误差小于 2 mm 并连续停留 0.3 秒。

连续训练 CP25 系数1/0两组在相同开发扰动下均100/100首次完成并稳定，全20秒稳定分别78/77。共同源模型为50/100；两组均改成连续训练，因此不能把改善全部归因于绝对姿态成本。系数1 CP25 在选定后两个新种子10103/11213分别为100/100首次严格成功、69/73全程稳定，合计142/200全程稳定。这些只验证同一抓姿附近扰动。

外部定时测试完全按时钟每2秒或5秒发出相反目标，不使用到位事件切换；仍运行20秒。图中“reached”要求每段曾连续0.3秒到位，“endpoints held”要求每段最后0.3秒到位，“held + base stable”进一步要求整段刀身稳定。连续teacher的2秒测试分别94/19/10，5秒为96/32/16，每项分母100。到位后持续保持仍未解决。原teacher和pilot student的失败结果同时列入图。

Pilot student CP100由原teacher CP125蒸馏；新种子8147/9257合计173/200完成、172/200首次稳定、100/200全程稳定。student继续训练正在评估，未把更晚轮数自动视为更好。

多抓姿精细任务仍失败：单抓姿连续teacher直接应用5个验证抓姿为0/160；仅转换物体观测坐标后仍0/160。多抓姿teacher CP250在原5mm/零停留条件下160/160完成，但改成2mm/0.3秒仅1/160，且0次姿态稳定。以上不能称为新抓姿、未见几何或真机泛化。

每个报告和checkpoint哈希见provenance；本批制品没有替换旧视频，也没有裁去中间格失败。原论文的有效物性参数包含真机校准，Wuji尚未完成该步骤。
"""
    (out/(prefix+'-results.md')).write_text(text)
    sums=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(out.iterdir()) if not p.name.endswith('SHA256SUMS.txt')]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sums)+'\n');print(out)


if __name__=='__main__':main()
