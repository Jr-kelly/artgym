"""Preserve the zero-learning-rate evidence and the resulting KL correction."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'runs/wuji-goal'


def main():
    diagnostic = BASE/'diagnostics/student-actorrl-zero-lr-kl-v2'
    analysis = json.loads((diagnostic/'analysis.json').read_text())
    assert analysis['all_model_parameters_equal_initial'] and analysis['physics_transitions'] == 491520
    rows = analysis['epochs']
    assert all(row['on']['exact_gaussian_max'] == 0 for row in rows)
    assert json.loads((diagnostic/'parameter-invariance.json').read_text())['all_unchanged']
    out = BASE/'release-sapg-kl-diagnostic-20260922'
    assert not out.exists()
    evidence = out/'evidence'
    evidence.mkdir(parents=True)
    prefix = 'wuji-sapg-kl-diagnostic-20260922'
    sources = {}

    def copy(source, name):
        shutil.copy2(source, evidence/name)
        sources[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()

    for version in [1,2]:
        folder = BASE/('diagnostics/student-actorrl-zero-lr-kl-v%d'%version)
        for source in folder.iterdir():
            if source.is_file():
                copy(source, 'zero-lr-v%d-'%version + source.name)
    for coeff in [0,5]:
        for version in [1,2]:
            name = 'wuji_student_actorrl_replaycp25_sigmaquarter_broad%d_lrquarter_seed62_v%d'%(coeff,version)
            for filename in ['pipeline-status.json','preflight.log']:
                copy(ROOT/'runs'/name/filename, name+'-'+filename)
            if version == 2:
                for source in (ROOT/'runs'/(name+'_smoke')/'runtime-audit').glob('*.json'):
                    copy(source, name+'-'+source.name)
    for name in ['student-actorrl-zero-lr-kl-v1-proposal.json','student-actorrl-zero-lr-kl-v2-proposal.json',
                 'student-actorrl-sigmaquarter-lrquarter-seed62-proposal.json',
                 'student-actorrl-sigmaquarter-lrquarter-seed62-v2-proposal.json',
                 'student-actorrl-onpolicy-seed62-proposal.json',
                 'diagnostics/kl-split-analytical-test-1555.json',
                 'diagnostics/failed-lrquarter-idle-queue-cleanup-1553.json']:
        copy(BASE/name, Path(name).name)
    for name in ['diagnose_wuji_sapg_kl.py','wuji_sapg_kl_metrics.py','check_wuji_sapg_kl_metrics.py',
                 'train_wuji_student_actor_audited.py','run_reference_experiment.py',Path(__file__).name]:
        copy(ROOT/'scripts'/name, name)
    epochs = [row['epoch'] for row in rows]
    fig, axes = plt.subplots(1,2,figsize=(11,4.8))
    axes[0].plot(epochs,[row['reported_kl'] for row in rows],'o-',label='Reported aggregate',color='#ae7638')
    axes[0].plot(epochs,[row['off']['exact_gaussian_mean'] for row in rows],'s-',label='Exact cross-group',color='#9d5057')
    axes[0].plot(epochs,[row['on']['exact_gaussian_mean'] for row in rows],'o-',label='Exact same-group',color='#267fa5')
    axes[0].set(title='Zero optimizer learning rate',xlabel='Epoch',ylabel='Gaussian KL',xticks=epochs)
    axes[0].legend(fontsize=9)
    axes[1].plot(epochs,[row['on']['upstream_mean'] for row in rows],'o-',label='Upstream epsilon formula',color='#ae7638')
    axes[1].plot(epochs,[row['on']['exact_gaussian_mean'] for row in rows],'o-',label='Exact float64 formula',color='#267fa5')
    axes[1].set(title='Same-group distributions are identical',xlabel='Epoch',ylabel='Same-group KL',xticks=epochs,ylim=(-.017,.003))
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.grid(alpha=.2)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('SAPG aggregate KL is not solely optimizer movement')
    fig.text(.02,.025,'5120 environments x32 steps x3 epochs =491520 physical transitions; all model parameters equal the initialization.\nOnly critic value statistics changed. Frozen student encoder unchanged. Cross-group relabeling remains active at LR0.\nThis diagnostic corrects an interpretation and gate; it does not establish improved task success.',fontsize=8)
    fig.tight_layout(rect=[0,.14,1,.95])
    fig.savefig(out/(prefix+'-comparison.png'),dpi=170)
    plt.close(fig)
    (out/(prefix+'-provenance.json')).write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        analysis=analysis, source_sha256=sources),indent=2)+'\n')
    (out/(prefix+'-README.md')).write_text('''# SAPG KL诊断与判断更正

小噪声训练的聚合info/kl约0.16–0.25曾被解读为更新过大，并对低学习率预检设置<=0.05门禁。两组实际3轮物理预检完成但门禁拒绝，未开始正式训练。该判断现由零学习率实验证明不成立；失败和旧方案均保留。

5120环境×32步×3轮零学习率，共491520真实转移。最终所有模型参数、观测归一化状态与初始化相同，仅critic的value统计改变，冻结学生编码器也未改变。聚合KL为0.30877/0.15512/0.17596；同策略精确高斯KL每个样本均0；跨探索组均值约1.94/1.02/1.14。SAPG混用样本时替换探索标识并沿用旧分布/RNN状态，因此聚合读数包含跨组差异。上游epsilon公式对相同分布还产生约-0.01424偏差。

诊断首版遗漏rnn_masks=None而退出；修正后的V2处理空掩码为单位权重，并核对聚合重建、全部72个minibatch、全模型参数和最终checkpoint。新日志分别记录精确同策略与跨组KL，解析的高斯例子同时覆盖有/无mask。新门禁采用三轮同策略加权均值<=0.05；这是工程阈值，不是论文参数，也不是全epoch累计距离，因为SAPG会刷新minibatch参考。

两组低学习率V2通过新门禁并开始100轮，第三组关闭跨组混用、保留五探索组也通过预检。跨组KL大本身不证明混用一定有害，因此关闭混用单列迁移消融；其每轮minibatch24→20，物理预算相同但优化计算量不同。后续成功与否用严格开合评估判断。本包没有把诊断当作新策略进步，没有硬件或泛化成功声明。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(evidence.iterdir()):
            archive.write(source,source.name)
    files = [p for p in out.iterdir() if p.is_file()]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(files))+'\n')
    print(json.dumps(dict(output=str(out),assets=len(files)+1)))


if __name__=='__main__':
    main()
