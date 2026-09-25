"""Bundle frozen training-distribution and same-model input diagnostics."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
from scripts.publish_wuji_student_replay_results import read_trial

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'runs/wuji-goal'


def main():
    folder = BASE/'diagnostics/frozen-training-objective-1708-v1'
    status = json.loads((folder/'status.json').read_text())
    assert status['status'] == 'completed'
    assert len(status['stages']) == 7 and all(s['returncode'] == 0 for s in status['stages'])
    reports = []
    for stage in status['stages']:
        p = folder/stage['name']
        report = json.loads((p/'report.json').read_text())
        assert report['model_unchanged'] and report['encoder_unchanged']
        with np.load(p/'metrics.npz') as m:
            assert np.allclose(m['total_reward'].mean(0), report['reward_per_transition'], atol=2e-5)
            mask = m['active'] & m['stable'] & m['all_tails'] & (m['commands'] > 0)
            assert mask.reshape(5, -1).sum(1).tolist() == report['full_cohort_all_complete_command_tails']
            assert m['active'].reshape(5, -1).sum(1).tolist() == report['full_cohort_alive']
        components = json.loads((p/'reward-components.json').read_text())
        for name, value in report['weighted_component_mean'].items():
            assert abs(np.mean([r[name] for r in components])-value) < 1e-8
        reports.append(dict(name=stage['name'], report=report))
    ablations = []
    for cp in [25, 100]:
        for enabled in ['true', 'false']:
            for sec in [2, 5]:
                name = 'student-controller-tracking-policy-cp%d-input%s-seed65-v2-mixed332-timed%dseconds' % (cp, enabled, sec)
                p, report, trace = read_trial(name)
                ablations.append(dict(name=name, cp=cp, enabled=enabled=='true', seconds=sec,
                    checkpoint_sha256=report['checkpoint_sha256'], joint=report['stable_full_all_endpoints'],
                    per_grasp=[sum(x['stable_full_all_endpoints'] for x in report['records'][i:i+100]) for i in [0,100,200,300]],
                    folder=p, trace=trace))
        assert len({a['checkpoint_sha256'] for a in ablations if a['cp']==cp}) == 1
    out = BASE/'release-population-diagnostics-20260922'
    out.mkdir(exist_ok=False)
    evidence = out/'evidence'
    evidence.mkdir()
    prefix = 'wuji-student-population-diagnostics-20260922'
    hashes = {}

    def copy(p, name):
        shutil.copy2(p, evidence/name)
        hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()

    for p in folder.rglob('*'):
        if p.is_file() and p.suffix in ['.json', '.npz', '.npy', '.yaml', '.py']:
            copy(p, 'training-'+str(p.relative_to(folder)).replace('/', '-'))
    for item in ablations:
        for p in item['folder'].iterdir():
            if p.is_file() and p.suffix in ['.json', '.yaml', '.py']:
                copy(p, item['name']+'-'+p.name)
        np.savez_compressed(evidence/(item['name']+'-metric-trace.npz'), **item['trace'])
    for name in ['student-training-objective-seed66-proposal.json',
                 'student-controller-frozen-input-ablation-seed65-proposal.json',
                 'student-controller-frozen-input-ablation-seed65-gpu5-initial-proposal.json',
                 'student-population-seed67-proposal.json']:
        copy(BASE/name, name)
    for name in ['scripts/probe_wuji_training_objective.py', 'scripts/run_wuji_training_objective_probe.py',
                 'scripts/publish_wuji_population_diagnostics.py', 'scripts/wuji_timed_command_metrics.py']:
        copy(ROOT/name, Path(name).name)
    record = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        training_distribution_reports=reports,
        fixed_clock_ablations=[{k:v for k,v in x.items() if k not in ['folder', 'trace']} for x in ablations],
        source_sha256=hashes,
        verification='Eight fixed-clock trials rescored from physical traces. Training diagnostic aggregate arrays/rewardcomponents checked against reports; command-tail flags were recorded online, not independently reconstructed from per-step physical endpoint traces.')
    (out/(prefix+'-provenance.json')).write_text(json.dumps(record, indent=2)+'\n')
    lines = ['# 冻结训练分布与同模型输入诊断', '',
        '训练分布诊断六项5120×600，共18,432,000正式转移，另320×600预检。三训练抓姿、随机2/5秒指令、五组各1024初态，模型和student编码器冻结；全部采用pose1完整代价。完整命令末9帧<2mm、首批初态全程<10mm/.25rad且存活；末尾不完整命令不计，重置不能补回失败样本。该指标与原332固定时钟指标不同。', '',
        '|候选/动作|五组平均回报每步|五组合计联合/5120|第0组联合/1024|', '|---|---:|---:|---:|']
    for item in reports:
        if item['name']=='preflight':
            continue
        r=item['report']
        lines.append('|%s|%.6f|%d|%d|' % (item['name'], np.mean(r['reward_per_transition']),
            sum(r['full_cohort_all_complete_command_tails']), r['full_cohort_all_complete_command_tails'][0]))
    lines += ['', '总体回报及总体表现改善同时第0组下降，支持检验探索组人口分配和共享训练的取舍；尚不能唯一证明组间梯度冲突。均值/采样会引起不同物理轨迹，不能把数字当作完全相同状态上的比较。每步奖励分项之和与环境实际reward核对通过，聚合数组和组件均值复核一致；训练诊断未保存完整逐步端点轨迹，因此不声称从物理trace独立重算了每个训练命令。', '',
        '|相同tracking策略|输入开启 快/慢|输入屏蔽 快/慢|', '|---|---:|---:|---:|']
    for cp in [25,100]:
        values=[]
        for enabled in [True, False]:
            values.append('/'.join(str(next(x for x in ablations if x['cp']==cp and x['enabled']==enabled and x['seconds']==sec)['joint']) for sec in [2,5]))
        lines.append('|CP%d|%s|%s|' % (cp, values[0], values[1]))
    lines += ['', '八项输入消融均在八卡GPU2、同332开发初态执行，开启模式也重新运行作为配对参考；同CP权重完全相同，仅把adapter的20个输入置零，bias仍保留。原计划GPU5被显存检查拒绝，确认仍有Sharpa评估后未启动进程，改用训练完成释放的GPU2。八项固定时钟评估均从原trace逐条重算，所有第四抓姿失败保留。当前输入未提供可靠收益。', '',
        '据此新增单组/五组训练配对：同历史CP25、seed67、5120×32×100、新Adam1e-5，两边都关闭跨组混用。保留五行模型参数以维持初始策略，仅单组数据使用ID50；实际编号、首模型权重和未使用行检查在真实PPO预检中执行。组数改变也按原公式改变总体熵系数分布，单组保留第0组系数。四卡/八卡不同主机的限制保留；这项新训练的结果另列。所有现有数据都是开发数据，不构成真机或未见泛化验证。']
    (out/(prefix+'-README.md')).write_text('\n'.join(lines)+'\n')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()):
            z.write(p, p.name)
    files=sorted(p for p in out.iterdir() if p.is_file())
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n')
    print(json.dumps(dict(output=str(out), assets=len(files)+1)))


if __name__ == '__main__':
    main()
