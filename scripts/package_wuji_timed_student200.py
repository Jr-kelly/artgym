"""Package the low-gain student candidate, full failures and diagnostic limits."""
import hashlib,json,shutil
from pathlib import Path
import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root=Path(__file__).resolve().parents[1];goal=root/'runs/wuji-goal'
    out=goal/'release-official-student200-20260922-0630';out.mkdir(exist_ok=False)
    prefix='wuji-knife-official-student-warm200-cp200-20260922'
    names=[f'student-official-timed10-warm200-cp200-timed{s}seconds-perturb100' for s in [2,5]]
    names += [f'official-timed2-cp10-timed{s}seconds-perturb100' for s in [2,5]]
    video_name='student-official-timed10-warm200-cp200-2seconds-preset3-video';names.append(video_name)
    data={}
    for name in names:
        p=goal/'verification'/name
        status=json.loads((p/'status.json').read_text());assert status['status']=='completed' and status['returncode']==0
        data[name]=dict(report=json.loads((p/'report.json').read_text()),status=status,report_sha256=sha(p/'report.json'))
    video=goal/'verification'/video_name/'policy.mp4'
    reader=imageio.get_reader(str(video));media=reader.get_meta_data();media.pop('nframes',None)
    media['decoded_frames']=reader.count_frames();assert media['decoded_frames']==600 and media['fps']==30 and media['size']==(1536,384)
    imageio.imwrite(out/(prefix+'-preview.png'),reader.get_data(50));reader.close()
    shutil.copy2(video,out/(prefix+'-three-trials-no-text-failures-retained.mp4'))
    keys=['first_cycle','first_cycle_strict','stable_full','stable_full_all_endpoints']
    labels=['First open\n+ close','First stable\nopen + close','Full 20 s\nbase stable','Every endpoint\n+ base stable']
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
    for ax,seconds in zip(axes,[2,5]):
        for i,(kind,color) in enumerate([('teacher','#2c7fb8'),('student','#f28e2b')]):
            name=f'official-timed2-cp10-timed{seconds}seconds-perturb100' if kind=='teacher' else f'student-official-timed10-warm200-cp200-timed{seconds}seconds-perturb100'
            row=data[name]['report'];values=[row[k] for k in keys]
            bars=ax.bar(np.arange(4)+(i-.5)*.36,values,.36,label=kind,color=color);ax.bar_label(bars,fontsize=8)
        ax.set(ylim=(0,115),xticks=np.arange(4),xticklabels=labels,title=f'{seconds} s external commands',ylabel='Successes / 100')
        ax.legend(fontsize=9)
    fig.suptitle('One nominal grasp, identical development perturbations; simulation only',fontsize=12)
    fig.savefig(out/(prefix+'-teacher-student-independent-evaluation.png'),dpi=170);plt.close(fig)
    p=goal/'diagnostics/student-latent-on-teacher32';diag=json.loads((p/'encoder_report.json').read_text())
    assert json.loads((p/'status.json').read_text())['returncode']==0 and diag['model_before']==diag['model_after']
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for row,label in zip(diag['summaries'],['Earlier student-only CP100','Teacher-prefix CP200']):
        x=np.arange(1,11)
        axes[0].plot(x,[v['latent_mse'] for v in row['stages']],'o-',label=label)
        axes[1].plot(x,[v['thumb_increment_error_mrad'] for v in row['stages']],'o-',label=label)
    axes[0].set(xlabel='Command (odd=open, even=close)',ylabel='Latent MSE',title='Latent prediction on teacher states')
    axes[1].set(xlabel='Command (odd=open, even=close)',ylabel='Mean thumb target-increment error (mrad)',title='Instantaneous control error on the same RNN state')
    for ax in axes:ax.legend(fontsize=8)
    fig.suptitle('Diagnostic: 32 teacher-driven traces; different training seeds/update counts, not a causal comparison',fontsize=10)
    fig.savefig(out/(prefix+'-latent-and-action-errors.png'),dpi=170);plt.close(fig)
    result=dict(source_sha256=sha(Path(__file__)),reports=data,media=media,encoder_diagnostic=diag,
        encoder_diagnostic_report_sha256=sha(p/'encoder_report.json'),
        teacher_sha256='38903d492ee7d6c372633ce5584c6ea7703034362f3bab8928e31eda599e977e',
        student_sha256='59e3346f51f36bc8773edae14dcff80e3db0cf21afa50e44a5f8415772c5ddb5')
    (out/(prefix+'-provenance-and-all-trials.json')).write_text(json.dumps(result,indent=2)+'\n')
    text='''# Wuji 低增益 student CP200：初步开合，仍有明显失败

这是学习得到的 student 编码器驱动冻结 teacher 策略，不是关节轨迹重放。训练前200次更新由teacher采样并监督student潜变量；该CP200的独立评估全部由student自己控制。之后的训练才切换为student自采样，匹配的全程自采样对照仍在运行，不能由这份结果宣称teacher引导的因果优势。

控制参数采用官方逐关节Kp/Kv和armature，保留ArtBot几何与PhysX。student执行时用本体感知历史、初始化信息和目标指令，不读取实时物体特权状态；潜变量误差诊断另外使用teacher状态，不是部署输入。

| 20秒独立评估，每协议100个相同开发扰动初态 | 完成首次开合 | 首次稳定开合 | 全程刀身稳定 | 每次末尾保持且全程稳定 |
|---|---:|---:|---:|---:|
| student CP200，2秒指令 | 79 | 67 | 50 | 9 |
| student CP200，5秒指令 | 85 | 73 | 29 | 5 |
| teacher CP10，2秒指令 | 99 | 99 | 93 | 63 |
| teacher CP10，5秒指令 | 99 | 99 | 94 | 51 |

到位误差<2mm连续9个采样；每次末尾保持指每个指令窗口最后9个采样全部到位；全程稳定要求20秒平移<10mm、转角<0.25rad，无掉落/无无效状态并完成首次开合。此处是同一名义抓姿的开发扰动，不是新抓姿、新几何或真机结果。

无字视频使用预定行0/2/76，20秒、30fps、1536×384，不换样。左侧完成所有目标且刀身稳定，但有两次打开窗口末尾保持失败；中间未完成首次开合且最大转角0.299rad；右侧完成首次稳定开合，后期最大转角0.263rad。三个案例的联合指标全部失败，原样发布。

另有32条teacher驱动轨迹诊断：在相同teacher状态和相同进入RNN状态下比较两份student，评估后丢弃其RNN和随机数状态，仅teacher动作进入物理仿真。CP200潜变量和即时拇指动作误差比旧CP100更小，但两者训练种子和更新数不同，且这不是student闭环成功率。teacher权重和normalizer哈希前后一致。

student SHA256：`59e3346f51f36bc8773edae14dcff80e3db0cf21afa50e44a5f8415772c5ddb5`。
teacher SHA256：`38903d492ee7d6c372633ce5584c6ea7703034362f3bab8928e31eda599e977e`。
本机3环境视频与H100百环境批次不是逐帧相同的复现。当前还不适合宣称真机部署成功，持续保持、多抓姿和物理标定仍未完成。
'''
    (out/(prefix+'-results.md')).write_text(text)
    files=sorted(out.iterdir());(out/(prefix+'-SHA256SUMS.txt')).write_text(''.join(f'{sha(p)}  {p.name}\n' for p in files))
    print(out)


if __name__=='__main__':main()
