"""Publish the completed frozen-policy noise diagnostic, with every failure."""
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
BASE = ROOT/'runs/wuji-goal'


def main():
    cases = []
    for policy in ['teacher', 'student']:
        for mode in ['deterministic', 'noisequarter', 'stochastic']:
            for seconds in [2,5]:
                name = 'frozen-%s-exploration-%s-mixed332-timed%dseconds'%(policy, mode, seconds)
                folder, report, trace = read_trial(name)
                rows = report['records']
                if mode != 'deterministic':
                    checks = report['stochastic_checks']
                    assert checks['model_before'] == checks['model_after']
                    assert checks['sampled_actions_differ'] > 0
                    if mode == 'noisequarter':
                        assert checks['noise_sigma_factor'] == .25
                cases.append(dict(name=name, policy=policy, mode=mode, seconds=seconds,
                                  joint=[sum(x['stable_full_all_endpoints'] for x in rows[i:i+100]) for i in [0,100,200,300]],
                                  alive=[sum(x['alive_full'] for x in rows[i:i+100]) for i in [0,100,200,300]],
                                  folder=folder, trace=trace))
    prefix = 'wuji-frozen-policy-exploration-20260922'
    out = BASE/'release-frozen-policy-exploration-20260922'
    assert not out.exists()
    evidence = out/'evidence'
    evidence.mkdir(parents=True)
    sources = {}

    def copy(source, name):
        shutil.copy2(source, evidence/name)
        sources[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()

    for case in cases:
        for name in ['report.json', 'status.json', 'config.yaml', 'source.py', 'source_metrics.py',
                     'stochastic_source.py', 'base_report.json']:
            path = case['folder']/name
            if path.exists():
                copy(path, case['name']+'-'+name)
        np.savez_compressed(evidence/(case['name']+'-metric-trace.npz'), **case['trace'])
    for name in ['student-exploration-shift-1512-proposal.json', 'student-noise-quarter-1517-proposal.json',
                 'student-noise-quarter-1522-v2-proposal.json', 'student-exploration-mean-reference-1535-proposal.json',
                 'student-actorrl-sigmaquarter-seed62-proposal.json', 'student-actorrl-sigmaquarter-lrquarter-seed62-proposal.json']:
        copy(BASE/name, name)
    copy(Path(__file__), 'publisher_source.py')
    copy(ROOT/'scripts/publish_wuji_student_replay_results.py', 'reader_source.py')
    copy(ROOT/'scripts/wuji_timed_command_metrics.py', 'metric_source.py')
    colors = dict(deterministic='#397b63', noisequarter='#5d78b4', stochastic='#d28a38')
    labels = dict(deterministic='Mean actions', noisequarter='Quarter original std', stochastic='Original std')
    fig, axes = plt.subplots(2,2,figsize=(12,8))
    for row, policy in enumerate(['teacher','student']):
        for col, seconds in enumerate([2,5]):
            ax = axes[row,col]
            for offset, mode in enumerate(colors):
                case = next(c for c in cases if c['policy']==policy and c['seconds']==seconds and c['mode']==mode)
                bars = ax.bar(np.arange(3)+(offset-1)*.25, case['joint'][:3], width=.23,
                              color=colors[mode], label=labels[mode])
                ax.bar_label(bars, fontsize=9, padding=2)
            ax.set(title=policy.title()+' / %d s commands'%seconds, ylabel='20 s joint success / 100',
                   ylim=(0,110), xticks=[0,1,2], xticklabels=['Original grasp','Training row16','Training row15'])
            ax.grid(axis='y', alpha=.15)
            ax.set_axisbelow(True)
            ax.spines[['top','right']].set_visible(False)
    axes[0,0].legend(loc='lower left', fontsize=9)
    fig.suptitle('Frozen Wuji policies: exploration noise exposes a large student control gap')
    fig.text(.02,.015,'All12 conditions on the same four-GPU host/GPU1, same332 saved development states and seed. TeacherCP25; replay-studentCP25.\nMean weights/encoders/normalizers stay fixed. Quarter-noise inference adjusts only logstd; this is not newly learned improvement.\nEvery command tail <2 mm for0.3 s; full body drift <10 mm / angle <0.25 rad, alive. Held-out fourth grasp0/32 throughout.\nOnly exploration block0; independent PhysX processes may differ. No new blind, unseen-geometry, or hardware claim.',fontsize=8)
    fig.tight_layout(rect=[0,.115,1,.95])
    fig.savefig(out/(prefix+'-comparison.png'),dpi=170)
    plt.close(fig)
    provenance = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      reports=12, all_records_rescored_exact=True, source_sha256=sources,
                      cases=[{k:v for k,v in x.items() if k not in ['folder','trace']} for x in cases])
    (out/(prefix+'-provenance.json')).write_text(json.dumps(provenance,indent=2)+'\n')
    (out/(prefix+'-README.md')).write_text('''# 冻结策略的探索噪声诊断

同四卡机器GPU1、同332开发初态、同随机种子；三训练抓姿各100个扰动，未训练第四抓姿32个。全部12项评估从原trace逐条重算一致，所有失败保留。它是已有开发条件的机制诊断，不增加独立验证分母。

|策略/动作|快速联合/300|慢速联合/300|
|---|---:|---:|
|teacher均值|294|298|
|teacher原噪声|179|194|
|teacher四分之一std|298|296|
|student均值|153|222|
|student原噪声|2|12|
|student四分之一std|126|190|

只在推理时改高斯动作标准差；原5×20的logstd统一加log(.25)，mean、encoder、normalizer全部保持。原噪声拇指目标增量相对均值的平均绝对偏差约5.8–6.0mrad/步；四分之一std约1.46–1.53mrad/步。采样动作经过原[-1,1]裁剪。额外均值动作只作反事实读数，恢复RNN/RNG，不进入物理。只使用探索组0，不是完整五组PPO训练复刻。

Student对动作扰动比teacher更敏感，与其依赖估计、teacher读取当前物体状态相符；这不唯一证明信息缺口是全部原因。降低噪声恢复了一部分能力，但仍低于可靠控制要求，也不能当作新训练成功。后续std×奖励PPO对照另行评估；观测到较大KL后追加的学习率对照不计入本包成功结果。

四分之一噪声最初等待八卡GPU3的已有Sharpa评估锁，确认无子进程、无物理执行后转移到四卡GPU1。原student均值参考曾来自八卡；为了同主机比较，在看到噪声结果后补齐这里两项均值参考，结果与原参考相同。独立PhysX进程仍不保证逐位一致，不能把微小计数差异视为确定因果。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(evidence.iterdir()):
            archive.write(p,p.name)
    files = [p for p in out.iterdir() if p.is_file()]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(files))+'\n')
    print(json.dumps(dict(assets=len(files)+1, reports=len(cases), output=str(out))))


if __name__ == '__main__':
    main()
