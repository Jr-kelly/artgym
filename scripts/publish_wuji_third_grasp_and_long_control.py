"""Package third-grasp validation, long-control failures and dropout diagnosis."""
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
    base = root / 'runs/wuji-goal'
    cases = [('functional15-%s-fresh200-seed44-timed%dseconds' % (model, seconds), seconds, 600)
             for model in ['functional20-cp100', 'bridge2-cp50'] for seconds in [2, 5]]
    cases += [('bridge2-cp50-mixed432-extended60-timed%dseconds' % seconds, seconds, 1800) for seconds in [2, 3, 5]]
    # Check completion before creating any published output.
    for name, _, _ in cases:
        folder = base / 'verification' / name
        status = json.loads((folder / 'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        assert (folder / 'report.json').exists()
    output = base / 'release-third-grasp-and-long-control-20260922'
    output.mkdir(exist_ok=False)
    evidence = output / 'evidence'
    evidence.mkdir()
    prefix = 'wuji-knife-third-grasp-and-long-control-20260922'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    reports, original = {}, {}
    for name, seconds, steps in cases:
        folder = base / 'verification' / name
        report = json.loads((folder / 'report.json').read_text())
        with np.load(folder / 'trace.npz') as arrays:
            trace = {k: arrays[k] for k in ['active', 'slider', 'goal', 'drift', 'rotation', 'fall', 'invalid']}
        scored = score_timed_trace(trace, seconds * 30, 9, steps)
        for key in ['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints', 'alive_full', 'records']:
            assert scored[key] == report[key]
        np.savez_compressed(evidence / (name + '-metric-trace.npz'), **trace)
        for filename in ['status.json', 'report.json', 'source.py', 'source_metrics.py', 'config.yaml']:
            source = folder / filename
            original[str(source.relative_to(root))] = sha(source)
            shutil.copy2(source, evidence / (name + '-' + filename))
        original[str((folder / 'trace.npz').relative_to(root))] = sha(folder / 'trace.npz')
        reports[name] = report
    assert len({reports[name]['initial_states_sha256'] for name, _, _ in cases[:4]}) == 1
    splits = {}
    for seconds in [2, 3, 5]:
        rows = reports['bridge2-cp50-mixed432-extended60-timed%dseconds' % seconds]['records']
        splits[seconds] = {label: dict(n=stop - start, **{
            key: sum(row[key] for row in rows[start:stop])
            for key in ['all_commands_attained', 'all_endpoints_held', 'stable_full_all_endpoints', 'alive_full']})
            for label, start, stop in [('source', 0, 200), ('novel16', 200, 400), ('heldout', 400, 432)]}
    dropout = json.loads((base / 'diagnostics/student-rollout-dropout-runtime/report.json').read_text())
    status = json.loads((base / 'diagnostics/student-rollout-dropout-runtime/status.json').read_text())
    assert dropout['status'] == 'passed' and status['returncode'] == 0
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7))
    for i, (model, label) in enumerate([('bridge2-cp50', 'Two-grasp CP50'), ('functional20-cp100', '20-grasp CP100')]):
        y = [reports['functional15-%s-fresh200-seed44-timed%dseconds' % (model, t)]['stable_full_all_endpoints'] for t in [2, 5]]
        bars = axes[0].bar(np.arange(2) + (i - .5) * .34, y, .32, label=label)
        axes[0].bar_label(bars, padding=3)
    axes[0].set(title='Third training grasp15\nSame fresh 200 states, 20 s', xticks=[0, 1], xticklabels=['2 s commands', '5 s commands'], ylabel='Joint successes / 200', ylim=(0, 280))
    axes[0].legend(fontsize=8, loc='upper left')
    for label, display in [('source', 'Original grasp'), ('novel16', 'Training grasp16')]:
        y = [splits[t][label]['stable_full_all_endpoints'] for t in [2, 3, 5]]
        axes[1].plot([2, 3, 5], y, 'o-', label=display)
        for x, value in zip([2, 3, 5], y):
            axes[1].annotate(str(value), (x, value), xytext=(0, 7), textcoords='offset points', ha='center')
    axes[1].set(title='Two-grasp CP50 extended to 60 s\nExisting 200 states per training grasp', xticks=[2, 3, 5], xlabel='Command duration (s)', ylabel='Joint successes / 200', ylim=(0, 225))
    axes[1].legend(fontsize=8, loc='lower right')
    steps = [v['step'] for v in dropout['records']]
    axes[2].plot(steps, [v['legacy_max_repeat_action_error'] for v in dropout['records']], 'o-', label='Legacy: dropout on')
    axes[2].plot(steps, [v['eval_mode_max_repeat_action_error'] for v in dropout['records']], 's-', label='Eval-mode rollout')
    axes[2].set(title='Frozen input and actor RNN state\n4 repeated action calls per physical state', xlabel='Physical step of diagnostic', ylabel='Maximum normalized action difference', ylim=(-.003, .04))
    axes[2].legend(fontsize=8, loc='upper right')
    for ax in axes:
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True); ax.spines[['top', 'right']].set_visible(False)
    fig.text(.015, .015, 'Grasp15 was seen by the 20-grasp model. The two-grasp model does not generalize here; no three-grasp policy success yet.\nAll held-out 32 perturbations fail in long tests. Dropout action variance is a mechanism check, not proof of training-performance benefit. Simulation only.', fontsize=8)
    fig.tight_layout(rect=[0, .09, 1, 1])
    fig.savefig(output / (prefix + '-validation-failures-and-dropout.png'), dpi=165)
    plt.close(fig)
    sources = [base / 'functional15-fresh200-seed20261044/manifest.json', base / 'functional15-fresh200-seed20261044/initial_states.npy',
               base / 'third-grasp-validation-proposal.json', base / 'bridge3-dataset-manifest.json',
               base / 'bridge3-curriculum-proposal.json', base / 'bridge2-horizon-pair-proposal.json',
               base / 'student-rollout-mode-pair-proposal.json', base / 'diagnostics/bridge2-long60-novel-endpoint-breakdown.json', Path(__file__)]
    sources += [p for p in (base / 'diagnostics/student-rollout-dropout-runtime').iterdir() if p.is_file()]
    for source in sources:
        original[str(source.relative_to(root))] = sha(source)
        shutil.copy2(source, evidence / str(source.relative_to(root)).replace('/', '__'))
    (output / (prefix + '-all-trials-provenance.json')).write_text(json.dumps(dict(reports=reports, long_splits=splits, dropout=dropout, original_file_sha256=original), indent=2) + '\n')
    third = {model: [reports['functional15-%s-fresh200-seed44-timed%dseconds' % (model, t)]['stable_full_all_endpoints'] for t in [2, 5]] for model in ['functional20-cp100', 'bridge2-cp50']}
    body = '''# 第三训练抓姿、长时保持失败与学生采样诊断

全部为Wuji/PhysX仿真、官方逐关节执行器参数、147×19×11mm刀具。联合成功要求每条指令末尾0.3秒在±2mm内，全程漂移<10mm、旋转<0.25rad，存活且有限。没有真机成功或未见几何泛化证据。

第三抓姿是functional20训练第15行，由训练开发集表现选择，冻结CP100后生成seed44的200新扰动。两协议复用同一批，无结果筛选。该策略2/5秒20秒联合%s；现有两抓姿CP50在相同初态上%s。不能把两份模型各自擅长的抓姿合称为一个三抓姿成功策略。三抓姿课程已保留原先两行并加入此行，另1个测试抓姿仍不用于训练，100轮训练和严格评估继续。

两抓姿CP50在相同已有初态上延长至60秒：2/3/5秒指令，原抓姿联合%s，训练第16行%s；每项分母200，额外测试抓姿32个扰动全部失败。三种周期对应不同循环数，不能唯一隔离频率因素。第16行2秒时200次均稳定持住刀身，但最后一次关闭只有63/200保持到位；最后20秒关闭末尾误差中位数2.910mm，90分位8.193mm。20秒成功不足以证明长期保持。

学生编码器实际为50帧历史、5层核3且倍增dilation的TCN，理论感受野63帧，覆盖输入历史。问题不是默认2层TCN忽略长历史。实际5层均有5%% Dropout，训练采样时保持training模式，即使Gaussian动作选择deterministic，同输入/同RNN四次调用也存在最大0.0163–0.0304归一化动作差异。只在采样时切为eval后差异为0，动作和输出RNN与部署逐项相等，随后恢复training模式。256次实际物理转移核对模型未变。这是采样与部署存在差异的证据，还不能证明它是闭环失败的主要原因；同起点、同seed40、500更新的模式对照已安排，梯度训练仍保留Dropout。

ZIP保留7项全样本轨迹评分，并从轨迹重算核对；包含全部失败。两个CP、所有初态和源码都有哈希。旧结果、旧模型和原本机训练保留。
''' % (third['functional20-cp100'], third['bridge2-cp50'], [splits[t]['source']['stable_full_all_endpoints'] for t in [2, 3, 5]], [splits[t]['novel16']['stable_full_all_endpoints'] for t in [2, 3, 5]])
    (output / (prefix + '-results.md')).write_text(body)
    with zipfile.ZipFile(output / (prefix + '-metric-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(evidence.iterdir()): archive.write(source, source.name)
    (output / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(sha(p) + '  ' + p.name for p in sorted(output.iterdir()) if p.is_file()) + '\n')
    print(json.dumps(dict(output=str(output), evaluations=len(cases), assets=len([p for p in output.iterdir() if p.is_file()]))))


if __name__ == '__main__':
    main()
