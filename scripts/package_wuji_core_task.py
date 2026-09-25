"""Package the frozen Wuji teacher/student and complete core-task evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def main():
    root = Path(__file__).resolve().parents[1]
    goal = root/'runs/wuji-goal'
    summary_path = goal/'diagnostics/core-task-collected-20260924-v2/latest.json'
    summary = json.loads(summary_path.read_text())
    assert summary['all_queues_completed'], 'Finish and rescore every declared trial first'
    out = goal/'release-core-teacher-student-20260924-v1'
    out.mkdir(exist_ok=False)
    prefix = 'wuji-core-teacher-student-20260924'
    files = {
        'teacher.pth': goal/'frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth',
        'student.pth': goal/'frozen-candidates/student-pure1000-artgym-core-20260924/student.pth',
        'initial-states.npy': goal/'core-task-fresh100-each-seed20261210-v1/states.npy',
        'source.tar.gz': goal/'source-history/pinned-core-teacher-student-evaluation-20260924-v2.tar.gz',
        'source-manifest.json': goal/'source-history/pinned-core-teacher-student-evaluation-20260924-v2-manifest.json',
        'evaluation.json': summary_path,
    }
    for kind in ('teacher', 'student'):
        files[kind+'-arrival-20s-three-grasps.mp4'] = goal/('verification/core-task-'+kind+'-arrival20-textfree-video-20260924-v5/policy.mp4')
        files[kind+'-arrival-20s-original-camera.mp4'] = goal/('verification/core-task-'+kind+'-arrival20-textfree-video-20260924-v4/policy.mp4')
        files[kind+'-original-camera-contact-sheet.png'] = goal/('diagnostics/core-video-inspection-20260924-v1/'+kind+'-contact-sheet.png')
        files[kind+'-front-camera-contact-sheet.png'] = goal/('diagnostics/core-video-inspection-20260924-v1/'+kind+'-front-contact-sheet.png')
    for label, source in files.items():
        assert source.is_file(), source
        shutil.copy2(source, out/(prefix+'-'+label))
    rows = []
    for kind in ('teacher', 'student'):
        for horizon in (20, 60):
            key = 'runs/wuji-goal/verification/core-task-%s-arrival%d-fresh300-20260924-v2' % (kind, horizon)
            result = summary['results'][key]
            total = result['totals']
            mean = sum(g['cycles_mean'] for g in result['groups'])/3
            rows.append('| %s | %d s | %d/300 | %d/300 | %d/300 | %.2f |' %
                        (kind, horizon, total['first_cycle'], total['three_cycles'], total['alive_full'], mean))
    fixed_rows = []
    for clock in (2, 5):
        key = 'runs/wuji-goal/verification/core-task-student-fixed-fresh300-%ds-20260924-v1' % clock
        result = summary['results'][key]
        fixed_rows.append('| %d s | %d/300 | %d/300 | %d/300 |' %
                          (clock, sum(g['all_endpoints_held_10mm'] for g in result['groups']),
                           result['totals']['stable_full_all_endpoints'], result['totals']['alive_full']))
    readme = '''# Wuji teacher + student：预置功能抓姿下伸缩美工刀

本包复用 ArtGym teacher → student 框架，在 Wuji 手与现实尺寸刀具上学习开合。
Teacher 使用物体特权状态；student 通过50帧关节角/动作历史及已知初始化信息预测16维latent，接入冻结actor。
Student 是原 latent MSE 蒸馏的最终1000更新权重，不是 RGB 状态估计、脚本动作或teacher接管。
参数化刀具147×19×11mm、35g，由刀身和被动滑块两个刚体组成；3个训练功能抓姿、同1把刀。刀身自由、动作驱动手关节，没有切割/刀刃接触模型。

候选冻结后生成新300个初态（每抓姿100，无结果过滤）。以下结果均由原始物理轨迹重算。

| 策略 | 时长 | 至少1轮 | 至少3轮 | 全程自然存活 | 平均循环 |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(rows) + '''

上表为10mm到位即刻换向、无阶段超时的连续循环。高层评估器读取仿真到位信号以发下一命令，student动作输入没有当前物体真值。
下表为固定外部时钟，连换向调度也不依赖到位信号，20秒内依次开/关。

| 换向间隔 | 全部端点末0.3秒保持<10mm | 原2mm+严格刀身联合 | 全程自然存活 |
|---|---:|---:|---:|
'''+ '\n'.join(fixed_rows) + '''

这些数字体现基本开合能力；自然终止阈值与额外刀身10mm/0.25rad阈值不同，后者完整列在evaluation.json。
保持现实尺寸的手型迁移使用了不同执行器/动作映射、物性、奖励和训练规模；不能称逐项完全复现论文。
本包不含桌面取刀、未见几何泛化或真机验证。四个无字视频是在预定新初态行0/100/200重新运行两策略、各两个视角，不能额外加成功分母。

## 在已经按 ArtGym README 安装的 Isaac Gym 环境运行

将source.tar.gz解压到新的工作目录；在该目录激活ArtGym环境，并设置PYTHONPATH为该目录及其rl_games子目录。
把本包teacher.pth、student.pth、initial-states.npy放在同目录（可重命名去掉发布前缀），然后执行：

```bash
python -m scripts.audit_wuji_arrival_commands --checkpoint teacher.pth --student-artifact student.pth --task wuji_acquisition_bridge3_hemisphere --hand wuji_paper_official_actuator --object knife_wuji_bridge3_20260922 --initial-states initial-states.npy --total-seconds 20 --tolerance-mm 10 --seed 20261210 --output evaluation-new
```

去掉--student-artifact即评估teacher。每次使用新的output目录。
显卡渲染可追加--video --initial-state-rows 0 100 200 --physical-gpu-index 0；渲染时CUDA与Vulkan需指向同一物理GPU。
本次H100使用已经隔离验证的EGL运行库；完整环境配置、V1/V2/V3渲染失败、终止步审计修复和V4/V5视频证据都保存在evidence.zip。
主视频为V5正面视角以露出滑块，original-camera视频为V4原视角，均保留完整20秒及后段不稳定情况。V5只增加相机参数，源码覆盖文件core-video-front-20260924-v5-audit.py位于evidence.zip/source-history对应路径；数值实验使用未改动的V2源码。

teacher/student/源码/初态和视频均有SHA256SUMS。evidence.zip含原始物理trace、配置、进程退出状态、各项报告、蒸馏最终审计及交接文档。
'''
    (out/(prefix+'-README.md')).write_text(readme)
    evidence = {summary_path, goal/'research/core-teacher-student-evaluation-20260924.md',
                goal/'research/core-teacher-student-final-20260924.md',
                goal/'research/goal-scope-teacher-student-20260924.md',
                root/'scripts/collect_wuji_core_evaluation.py', Path(__file__),
                root/'scripts/publish_wuji_core_task.py',
                goal/'source-history/core-video-egl-20260924-v3-runner.py',
                goal/'source-history/core-video-egl-20260924-v3-manifest.json',
                goal/'source-history/core-video-front-20260924-v5-audit.py',
                goal/'source-history/core-video-front-20260924-v5-manifest.json'}
    for condition in summary['results']:
        evidence.update(p for p in (root/condition).iterdir() if p.is_file() and p.suffix != '.mp4')
    for condition in summary['historical_failed_paths']:
        evidence.update(p for p in (root/condition).iterdir() if p.is_file() and p.suffix != '.mp4')
    for pattern in ('core-task-*-spec.json',):
        evidence.update(goal.glob(pattern))
    evidence.update((goal/'core-task-fresh100-each-seed20261210-v1').glob('*'))
    evidence.update((goal/'diagnostics/core-student-training-provenance-20260924-v1').glob('*'))
    evidence.update((goal/'diagnostics').glob('core-task-*verified*.json'))
    evidence.update((goal/'diagnostics').glob('core-video-egl-*.json'))
    evidence.update((goal/'diagnostics').glob('core-video-front-*.json'))
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'), 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for path in sorted(evidence):
            if path.is_file():
                archive.write(path, str(path.relative_to(root)))
    sums = ['%s  %s' % (hashlib.sha256(p.read_bytes()).hexdigest(), p.name)
            for p in sorted(out.iterdir()) if p.is_file()]
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sums)+'\n')
    print(json.dumps(dict(output=str(out), assets=len(sums)+1)))


if __name__ == '__main__':
    main()
