"""Package every small-geometry/inertia trial with independently rescored traces."""
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
    jobs = json.loads((base/'audit-queue-geometry-sensitivity-paired.json').read_text())
    jobs += json.loads((base/'audit-queue-object-inertia.json').read_text())
    assert len(jobs) == 24
    output = base/'release-geometry-inertia-20260922'
    output.mkdir(exist_ok=False)
    evidence = output/'evidence'
    evidence.mkdir()
    prefix = 'wuji-knife-geometry-inertia-20260922'
    reports, extras, sources = {}, {}, {}
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

    def archive_file(p, label=None):
        sources[str(p.relative_to(root))] = sha(p)
        shutil.copy2(p, evidence/(label or str(p.relative_to(root)).replace('/', '__')))

    for job in jobs:
        name = job['name']
        folder = base/'verification'/name
        status = json.loads((folder/'status.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        report = json.loads((folder/'report.json').read_text())
        seconds = report['protocol']['stage_seconds']
        with np.load(folder/'trace.npz') as data:
            trace = {k: data[k] for k in ['active', 'slider', 'goal', 'drift', 'rotation', 'fall', 'invalid']}
        scored = score_timed_trace(trace, round(seconds*30), 9, 600)
        assert all(report[k] == scored[k] for k in ['first_cycle', 'first_cycle_strict', 'stable_full_all_endpoints', 'alive_full', 'records'])
        np.savez_compressed(evidence/(name+'-metric-trace.npz'), **trace)
        sources[str((folder/'trace.npz').relative_to(root))] = sha(folder/'trace.npz')
        for filename in ['status.json', 'report.json', 'config.yaml', 'source.py', 'source_metrics.py']:
            archive_file(folder/filename, name+'-'+filename)
        extra_type = 'geometry' if name.startswith('geometry-') else 'inertia'
        extra = json.loads((folder/(extra_type+'-report.json')).read_text())
        assert extra['status'] == 'passed' and extra['model_unchanged']
        archive_file(folder/(extra_type+'-report.json'), name+'-'+extra_type+'-report.json')
        archive_file(folder/(extra_type+'-source.py'), name+'-'+extra_type+'-source.py')
        if extra_type == 'geometry':
            alive = trace['active'].all(0) & (~trace['fall']).all(0) & (~trace['invalid']).all(0)
            pose = alive & (trace['drift'] < .01).all(0) & (trace['rotation'] < .25).all(0)
            assert extra['pure_pose_stable_count'] == int(pose.sum())
        reports[name], extras[name] = report, extra

    assert len({r['checkpoint_sha256'] for r in reports.values()}) == 1
    variants = ['nominal', 'length142', 'length152', 'width18', 'width20', 'body7', 'body9']
    labels = ['Anchor\n147/19/8', 'Length\n142 mm', 'Length\n152 mm', 'Width\n18 mm', 'Width\n20 mm', 'Body\n7 mm', 'Body\n9 mm']
    key = lambda v, m: 'geometry-near5cp50-'+v+'-'+m+'-seed51-timed2seconds'
    correct = [reports[key(v, 'correct')]['stable_full_all_endpoints'] for v in variants]
    observation = [reports[key(v, 'observation_only' if v != 'nominal' else 'correct')]['stable_full_all_endpoints'] for v in variants]
    static = [extras[key(v, 'static')]['pure_pose_stable_count'] for v in variants]
    pose = [extras[key(v, 'correct')]['pure_pose_stable_count'] for v in variants]
    fig, axes = plt.subplots(2, 1, figsize=(11.8, 8.1))
    x = np.arange(len(variants))
    for values, shift, color, label in [(correct, -.18, '#297da6', 'Changed physical geometry + honest dimensions'),
                                      (observation, .18, '#e4a144', 'Nominal physics + altered dimensions (diagnostic)')]:
        bars = axes[0].bar(x+shift, values, .34, color=color, label=label)
        axes[0].bar_label(bars, padding=2, fontsize=9)
    for values, shift, color, label in [(pose, -.18, '#297da6', 'Learned teacher, physical geometry changed'),
                                      (static, .18, '#aab4be', 'Constant initial targets (no manipulation policy)')]:
        bars = axes[1].bar(x+shift, values, .34, color=color, label=label)
        axes[1].bar_label(bars, padding=2, fontsize=9)
    axes[0].set_title('Same frozen teacher, one grasp with 32 paired perturbations per geometry')
    axes[0].set_ylabel('Joint successes / 32')
    axes[1].set_title('Pose stability alone: every command need not be achieved')
    axes[1].set_ylabel('Pose-stable trials / 32')
    for ax in axes:
        ax.set(xticks=x, xticklabels=labels, ylim=(0, 43))
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True)
        ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .015, '20 s simulation, 2 s commands. Anchor is 147 x 19 x 11 mm including the 3 mm slider; body thickness is 8 mm.\nGeometry trials retain inherited density-derived inertia. Altered-input controls are counterfactuals, not honest transfer. All failures retained.', fontsize=8)
    fig.tight_layout(rect=[0, .065, 1, 1])
    fig.savefig(output/(prefix+'-geometry-and-static-holding.png'), dpi=165)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.6))
    for i, seconds in enumerate([2, 5]):
        values = [reports['object-inertia-near5cp50-'+mode+'-seed51-timed%dseconds'%seconds]['stable_full_all_endpoints'] for mode in ['imported', 'authored']]
        bars = axes[0].bar(np.arange(2)+(i-.5)*.34, values, .32, label='%d s commands'%seconds)
        axes[0].bar_label(bars, padding=3)
    axes[0].set(xticks=[0, 1], xticklabels=['Inherited import', 'Mass-consistent boxes'], ylim=(0, 42), ylabel='Joint successes / 32', title='Same teacher and same 32 anchor initial states')
    extra = extras['object-inertia-near5cp50-authored-seed51-timed2seconds']['expected']
    ratio = [extra[n]['imported'][0]/extra[n]['authored'][0] for n in ['link_0', 'link_1']]
    bars = axes[1].bar([0, 1], ratio, .6, color=['#297da6', '#e4a144'])
    axes[1].bar_label(bars, labels=['%.3f'%v for v in ratio], padding=3)
    axes[1].axhline(1, ls='--', color='black', lw=1)
    axes[1].set(xticks=[0, 1], xticklabels=['Body, 29 g', 'Slider, 6 g'], ylim=(0, 1.2), ylabel='Inherited / authored inertia', title='Runtime mass and inertia were checked')
    axes[0].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True); ax.spines[['top', 'right']].set_visible(False)
    fig.text(.02, .015, 'All 32 trials survive in all four conditions. Equal aggregate counts do not establish identical trajectories.\nAuthored box inertia is internally mass-consistent; it is not a measured real knife calibration. Simulation only.', fontsize=8)
    fig.tight_layout(rect=[0, .09, 1, 1])
    fig.savefig(output/(prefix+'-actual-object-inertia.png'), dpi=165)
    plt.close(fig)

    manifest_path = base/'geometry-sensitivity-20260922/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    archive_file(manifest_path)
    for variant in manifest['variants'].values():
        archive_file(root/variant['states'])
        for p, h in variant['artifact_sha256'].items():
            assert sha(root/p) == h
            archive_file(root/p)
    for p in [Path(__file__), base/'geometry-sensitivity-proposal.json', root/'isaacgymenvs/cfg/object/knife_wuji_precision_authored_inertia.yaml', base/'audit-queue-object-inertia.json']:
        archive_file(p)
    provenance = dict(scope=__doc__,evaluations=len(jobs),reports=reports,diagnostics=extras,original_file_sha256=sources,
        limits='One training grasp, small geometry perturbations, teacher privileged inputs, uncalibrated friction/damping. No new-grasp, student, or hardware claim. Geometry and inertia comparisons use different devices; only within-experiment comparisons are intended.')
    (output/(prefix+'-all-trials-provenance.json')).write_text(json.dumps(provenance, indent=2)+'\n')
    lines = ['# Wuji 刀具几何和惯量检查', '', '同一个冻结 teacher，1 个名义训练抓姿，每种几何 32 个配对扰动；20 秒、2 秒开/关指令。全部失败保留。', '',
        '|几何|真实几何变化：联合成功|只变尺寸观测：联合成功|恒定初始目标：纯持姿稳定|', '|---|---:|---:|---:|']
    for i, v in enumerate(variants):
        lines.append('|%s|%d/32|%s|%d/32|'%(v, correct[i], str(observation[i])+'/32' if v!='nominal' else '同基线', static[i]))
    lines += ['', '名义外形 147×19×11 mm，其中刀身厚 8 mm、滑块厚 3 mm。厚度变化同时改变滑块安装高度 ±0.5 mm，初态中的滑块位姿相应变换；手关节和刀身初态保持配对。尺寸观测单独变化属于人为诊断，不是诚实的几何迁移。',
        '', '联合成功要求每次指令最后 0.3 秒在 ±2 mm 内，全程刀身漂移 <10 mm、旋转 <0.25 rad，且存活、状态有限。纯持姿列不要求操作成功；所有静态动作都是零，关节目标固定，不能算 RL 开合成功。',
        '', '厚度变化比这些小幅长宽变化更敏感。输入尺寸变化不足以解释全部下降；实际接触关系变化是线索，尚未证明唯一机制。三维形状变化会同时影响接触和导入惯量。几何实验保留了原导入惯量，不能把它称为质量一致模型。',
        '', '另一个独立惯量对照保持同一刀具、质量、控制和模型：原导入惯量相对质量一致箱体惯量为刀身 0.77048 倍、滑块 0.15 倍。实际第一/最后环境的质量与惯量均逐项断言；原设置与修正设置，2 秒联合均 31/32、5 秒均 32/32，全部存活。相同计数不保证相同轨迹。',
        '', '几何实验在本机，惯量对照在远端；不跨机器把 32/32 与 31/32 当作某个物理参数的单变量效应。两者共同使用 seed51 生成的配对初态、实际物理 seed707。测试对象仍是一种抓姿附近的小变化，不代表广泛类别泛化。',
        '', '这些都是带特权物体状态的 teacher 仿真。惯量是箱体近似，摩擦与滑块阻力尚未实物标定；student 与真机成功均未达成。证据 ZIP 包含 24 项全部试验、重算评分轨迹、资产、初态、执行源码和哈希。']
    (output/(prefix+'-results.md')).write_text('\n'.join(lines)+'\n')
    with zipfile.ZipFile(output/(prefix+'-metric-evidence.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()): z.write(p, p.name)
    (output/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(output.iterdir()) if p.is_file())+'\n')
    print(json.dumps(dict(output=str(output), evaluations=24, assets=6)))


if __name__ == '__main__':
    main()
