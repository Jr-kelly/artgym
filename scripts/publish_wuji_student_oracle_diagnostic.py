"""Publish complete privileged-oracle diagnostics, never student success claims."""
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
    root = Path(__file__).resolve().parents[1]
    base = root/'runs/wuji-goal'
    cases = [('student-teacher500-cp500-oracleblend%s-timed%dseconds' % (alpha, seconds), alpha, seconds)
             for alpha in ['0', '0p5', '1'] for seconds in [2, 5]]
    for name, _, _ in cases:
        status = json.loads((base/'verification'/name/'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
    output = base/'release-student-oracle-diagnostic-20260922'
    output.mkdir(exist_ok=False)
    evidence = output/'evidence'
    evidence.mkdir()
    prefix = 'wuji-knife-student-oracle-diagnostic-20260922'
    reports, oracle, sources = {}, {}, {}
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, alpha, seconds in cases:
        folder = base/'verification'/name
        report = json.loads((folder/'report.json').read_text())
        extra = json.loads((folder/'oracle-blend-report.json').read_text())
        assert extra['model_unchanged'] and extra['uses_privileged_oracle'] == (alpha != '0')
        with np.load(folder/'trace.npz') as loaded:
            trace = {k: loaded[k] for k in ['active', 'slider', 'goal', 'drift', 'rotation', 'fall', 'invalid']}
        scored = score_timed_trace(trace, seconds*30, 9, 600)
        for key in ['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints', 'alive_full', 'records']:
            assert report[key] == scored[key]
        np.savez_compressed(evidence/(name+'-metric-trace.npz'), **trace)
        for filename in ['status.json', 'report.json', 'oracle-blend-report.json', 'oracle-blend-source.py', 'source.py', 'source_metrics.py', 'config.yaml']:
            source = folder/filename
            sources[str(source.relative_to(root))] = sha(source)
            shutil.copy2(source, evidence/(name+'-'+filename))
        sources[str((folder/'trace.npz').relative_to(root))] = sha(folder/'trace.npz')
        reports[name], oracle[name] = report, extra
    assert len({r['initial_states_sha256'] for r in reports.values()}) == 1
    assert len({r['student_sha256'] for r in oracle.values()}) == 1
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.6))
    x = np.arange(3)
    for i, seconds in enumerate([2, 5]):
        names = ['student-teacher500-cp500-oracleblend%s-timed%dseconds' % (a, seconds) for a in ['0', '0p5', '1']]
        y = [reports[n]['stable_full_all_endpoints'] for n in names]
        bars = axes[0].bar(x+(i-.5)*.34, y, .32, label='%d s commands' % seconds)
        axes[0].bar_label(bars, padding=3)
        axes[1].plot(x, [oracle[n]['latent_mse_on_actual_closed_loop_states'] for n in names], 'o-', label='%d s commands' % seconds)
    labels = ['Pure student\n(no oracle)', '50% oracle\n(privileged)', '100% oracle\n(privileged)']
    axes[0].set(title='Same frozen student and actor, same 100 starts', ylabel='Joint successes / 100', ylim=(0, 130), xticks=x, xticklabels=labels)
    axes[1].set(title='Student prediction error on each induced trajectory', ylabel='Latent MSE before mixing', ylim=(0, .34), xticks=x, xticklabels=labels)
    for ax in axes:
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True); ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .01, 'Oracle variants use privileged object information and cannot be deployed as proprioceptive students.\nTrajectories change with oracle fraction; MSE differences are not comparisons at identical physical states. All failures retained. Simulation only.', fontsize=8)
    fig.tight_layout(rect=[0, .09, 1, 1])
    fig.savefig(output/(prefix+'-privileged-diagnostic-only.png'), dpi=165)
    plt.close(fig)
    for source in [Path(__file__), base/'student-latent-curriculum-proposal.json', base/'student-near5cp50-after-teacher500-mix-spec.json']:
        sources[str(source.relative_to(root))] = sha(source)
        shutil.copy2(source, evidence/str(source.relative_to(root)).replace('/', '__'))
    provenance = dict(reports=reports, oracle=oracle, original_file_sha256=sources,
        interpretation='Privileged diagnostics localize a latent-estimation/control interaction. They do not prove latent error is uniquely causal or establish deployable student success.')
    (output/(prefix+'-all-trials-provenance.json')).write_text(json.dumps(provenance, indent=2)+'\n')
    text = '''# 学生状态估计与闭环误差诊断

全部为相同冻结student CP500、相同冻结teacher actor、同一批100个已有开发扰动，20秒PhysX仿真，2/5秒外部指令。
联合成功要求每条指令最后0.3秒在±2mm内，全程刀身漂移<10mm、旋转<0.25rad，有限且存活。

|teacher latent混入比例|2秒联合|5秒联合|可否当作纯本体感知student成绩|
|---|---:|---:|---|
|0|7/100|10/100|可以，但成功率低|
|0.5|85/100|94/100|不可以，使用了特权物体状态|
|1|100/100|100/100|不可以，实际用准确teacher latent控制|

每种条件都100次存活。全oracle的动作控制通过同一学生评估入口执行，模型张量未修改。
这些结果支持优先处理latent预测与闭环分布偏移；它们不证明部分可观测性可以完全消除，也不证明唯一故障机制。
图中MSE是原学生预测相对于teacher的误差，统计于各自策略实际产生的不同轨迹；不能解释为同状态误差下降。
零oracle的2秒7/100与先前8/100有轻微运行差异，5秒10/100一致；这里比较同一诊断实现的结果，不替换历史结果。

新训练课程已事先记录：从同student CP500出发，500更新、1024环境、每更新16步、新Adam、LR1e-4，采样用eval模式，与evalmode对照保持相同。
前250更新将teacher latent混入比例从0.5线性降至0，后250更新全部student；梯度仍监督原student latent，actor/normalizer冻结。
正式评估始终关闭所有混合，仅有本体感知student。该课程是Wuji适应实验，与论文全student采样有差异；是否有益尚待独立闭环结果。

ZIP包含6个完整评估的全部100次结果及评分轨迹，均重算核对；包含所有失败、原始源码和哈希。
没有真机成功或未见几何泛化声明。
'''
    (output/(prefix+'-results.md')).write_text(text)
    with zipfile.ZipFile(output/(prefix+'-metric-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(evidence.iterdir()):
            archive.write(source, source.name)
    (output/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(output.iterdir()) if p.is_file())+'\n')
    print(json.dumps(dict(output=str(output), evaluations=6, assets=5)))


if __name__ == '__main__':
    main()
