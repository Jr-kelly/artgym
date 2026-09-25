"""Publish complete fixed-checkpoint action-imitation comparisons, including failures."""
import argparse
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
from scripts.publish_wuji_student_replay_results import read_trial

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'runs/wuji-goal'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoints', type=int, nargs='+', default=[0, 1, 25])
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label.replace('-', '').isalnum()
    assert args.checkpoints == sorted(set(args.checkpoints))
    rows = []
    for scope in ['head', 'actor']:
        for cp in args.checkpoints:
            for seconds in [2, 5]:
                name = 'student-actionimit-%s-seed68-v5-cp%d-mixed332-timed%dseconds' % (scope, cp, seconds)
                folder, report, trace = read_trial(name)
                assert report['policy_kind'] == 'student_with_direct_teacher_action_imitation'
                assert report['imitation']['scope'] == scope
                groups = [report['records'][i:i+100] for i in [0, 100, 200, 300]]
                body = (np.isfinite(trace['drift']) & np.isfinite(trace['rotation']) &
                        (trace['drift'] < .01) & (trace['rotation'] < .25)).all(0)
                body &= np.array([x['alive_full'] for x in report['records']])
                rows.append(dict(name=name, scope=scope, checkpoint=cp, seconds=seconds,
                    joint=[sum(x['stable_full_all_endpoints'] for x in g) for g in groups],
                    alive=[sum(x['alive_full'] for x in g) for g in groups],
                    body=[int(body[i:i+100].sum()) for i in [0, 100, 200, 300]],
                    folder=folder, trace=trace))
    out = BASE / ('release-actionimit-' + args.label)
    out.mkdir(exist_ok=False)
    evidence = out / 'evidence'
    evidence.mkdir()
    prefix = 'wuji-action-imitation-' + args.label
    hashes = {}

    def copy(path, target):
        shutil.copy2(path, evidence / target)
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()

    for row in rows:
        for p in row['folder'].iterdir():
            if p.is_file() and p.suffix in ['.json', '.yaml', '.py']:
                copy(p, row['name'] + '-' + p.name)
        np.savez_compressed(evidence / (row['name'] + '-metric-trace.npz'), **row['trace'])
    complete = True
    for scope in ['head', 'actor']:
        run = ROOT / 'runs' / ('wuji_student_actionimit_%s_seed68_v5' % scope)
        status = json.loads((run / 'pipeline-status.json').read_text())
        complete &= status['status'] == 'completed'
        for p in [run / 'pipeline-status.json', run / 'imitation/status.json', run / 'imitation/metrics.jsonl']:
            copy(p, scope + '-' + p.name)
    complete &= 500 in args.checkpoints
    for p in [BASE / 'student-actionimit-seed68-v5-proposal.json', Path(__file__),
              ROOT / 'scripts/train_wuji_actor_imitation.py', ROOT / 'scripts/wuji_timed_command_metrics.py']:
        copy(p, p.name)
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.3))
    for row_index, seconds in enumerate([2, 5]):
        for col, label in enumerate(['Original grasp', 'Training row16', 'Training row15']):
            ax = axes[row_index, col]
            for scope, caption, color in [('head', 'Output layer only', '#33829d'), ('actor', 'Full actor', '#c48a36')]:
                selected = [x for x in rows if x['scope'] == scope and x['seconds'] == seconds]
                ax.plot(range(len(selected)), [x['joint'][col] for x in selected],
                        'o-', label=caption, color=color, markersize=4)
            ax.set(title=label + ' / %d s commands' % seconds, xlabel='Saved checkpoints (updates)',
                   ylabel='20 s joint success /100', ylim=(-2, 103),
                   xticks=list(range(len(args.checkpoints))), xticklabels=args.checkpoints)
            ax.grid(alpha=.2)
            ax.spines[['top', 'right']].set_visible(False)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, .96), ncol=2, frameon=False)
    fig.suptitle('Wuji direct teacher-action imitation: ' + ('final' if complete else 'interim'))
    fig.text(.02, .013, 'Student alone drives physics; frozen teacher supplies labels with its own recurrent history. Encoder and observation statistics frozen.\nSame initialization, seed68, Adam1e-5, 2048 x32 per update; different H100 hosts. Strict 2 mm /0.3 s tails, body <10 mm /0.25 rad.\nReused332 development states: three training grasps x100, fourth unseen grasp x32. No independent generalization or hardware claim.', fontsize=8)
    fig.tight_layout(rect=[0, .11, 1, .9])
    fig.savefig(out / (prefix + '-curves.png'), dpi=170)
    plt.close(fig)
    records = [{k:v for k,v in x.items() if k not in ['folder', 'trace']} for x in rows]
    provenance = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        reports=len(rows), records_rescored_exact=True, full_budget_completed=bool(complete),
        records=records, source_sha256=hashes)
    (out / (prefix + '-provenance.json')).write_text(json.dumps(provenance, indent=2) + '\n')
    table = ['|CP|输出层 快/慢|完整actor 快/慢|', '|---|---:|---:|']
    for cp in args.checkpoints:
        cells = []
        for scope in ['head', 'actor']:
            cells.append('/'.join(str(sum(next(x for x in rows if x['scope'] == scope and
                x['checkpoint'] == cp and x['seconds'] == seconds)['joint'][:3])) for seconds in [2, 5]))
        table.append('|%d|%s|%s|' % (cp, *cells))
    (out / (prefix + '-README.md')).write_text('# Wuji 直接动作模仿\n\n' +
        ('完整预算评估。' if complete else '中期评估，500更新预算仍未完成。') +
        '全部列出的checkpoint和两种时序已完成，原物理trace逐条重算一致。\n\n' + '\n'.join(table) +
        '\n\n每项分母300，为三种训练抓姿各100扰动；另32个第四抓姿结果和所有失败保留于provenance。'
        '两组初始化相同、不同H100主机。student自己执行动作；冻结teacher只在训练时提供标签，保有独立RNN历史。'
        '直接20维动作均值MSE，区别于论文冻结actor的latent蒸馏。编码器和归一化统计冻结；完整actor组更新与critic共享的探索embedding，但不优化critic loss。'
        '2mm固定时钟联合成功不等价于论文10mm循环指标。训练MSE和中期峰值不代表可靠收敛；未进行新盲测或真机验证。\n')
    with zipfile.ZipFile(out / (prefix + '-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()):
            z.write(p, p.name)
    files = sorted(p for p in out.iterdir() if p.is_file())
    (out / (prefix + '-SHA256SUMS.txt')).write_text('\n'.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name for p in files) + '\n')
    print(json.dumps(dict(output=str(out), reports=len(rows), full_budget_completed=bool(complete))))


if __name__ == '__main__':
    main()
