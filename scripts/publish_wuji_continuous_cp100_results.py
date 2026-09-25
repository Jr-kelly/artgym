"""Prepare measured CP100, holding and actuator results; uploading is separate."""
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / "runs/wuji-goal"
    out = base / "release-continuous-holding-20260922-0500"
    out.mkdir(exist_ok=True)
    prefix = "wuji-knife-continuous-cp100-holding-20260922"
    reports = {}
    provenance = []

    def read(relative):
        p = base / relative / "report.json"
        status = json.loads((p.parent / "status.json").read_text())
        assert status["status"] == "completed" and status["returncode"] == 0
        d = json.loads(p.read_text())
        reports[relative] = d
        provenance.append(dict(path=str(p.relative_to(root)),
            sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            checkpoint_sha256=d.get("checkpoint_sha256"), status=status))
        return d

    fresh = [read("verification/" + name) for name in [
        "precision-cont-cost1-cp100-perturb100",
        "precision-cont-cost1-cp100-blind-seed12203-perturb100",
        "precision-cont-cost1-cp100-blind-seed13313-perturb100"]]
    assert len({d["checkpoint_sha256"] for d in fresh}) == 1
    timed = {(dwell, period):read("verification/precision-hold%s-cp25-timed%dseconds-perturb100" % (dwell, period))
             for dwell in ["03", "2"] for period in [2, 5]}
    assert len({d["initial_states_sha256"] for d in timed.values()}) == 1
    for period in [2, 5]:
        read("verification/precision-cont-cost1-cp100-timed%dseconds-perturb100" % period)
    video = read("verification/precision-cont-cost1-cp100-preset3-video")
    source = base / "verification/precision-cont-cost1-cp100-preset3-video"
    shutil.copy2(source / "policy.mp4", out / (prefix + "-three-perturbed-trials-no-text.mp4"))
    shutil.copy2(source / "preview.png", out / (prefix + "-preview.png"))

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    ax = axes[0]
    x = np.arange(3)
    for j, (key, label, color) in enumerate([
        ("strict_first_cycle_trials", "First stable cycle", "#237d9f"),
        ("stable_full_rollout_trials", "Full 20 seconds stable", "#d08142")]):
        bars = ax.bar(x + (j-.5)*.35, [d[key] for d in fresh], .32, label=label, color=color)
        ax.bar_label(bars, fontsize=9, padding=2)
    ax.set_xticks(x, ["1616\nDevelopment", "12203\nFresh", "13313\nFresh"])
    ax.set_title("Continuous CP100, original gains")
    ax.legend(loc="lower left", fontsize=8)
    for ax, period in zip(axes[1:], [2, 5]):
        for j, (dwell, label, color) in enumerate([
            ("03", "Training dwell 0.3 s", "#8899a6"), ("2", "Training dwell 2 s", "#359367")]):
            d = timed[dwell, period]
            keys = ["all_commands_attained", "all_endpoints_held", "stable_full_all_endpoints"]
            bars = ax.bar(x+(j-.5)*.35, [d[k] for k in keys], .32, label=label, color=color)
            ax.bar_label(bars, fontsize=9, padding=2)
        ax.set_xticks(x, ["Every command\nattained", "Every endpoint\nheld", "Held AND\nbase stable"])
        ax.set_title("Matched CP25: fixed %d s commands" % period)
        ax.legend(loc="lower left", fontsize=8)
    for ax in axes:
        ax.set_ylim(0, 112)
        ax.set_ylabel("Trials / 100")
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    fig.text(.015, .025, "One nominal grasp with reset perturbations; 2 mm tolerance, 9 control samples to hold. "
             "Stable base: <10 mm and <0.25 rad throughout the assessed interval.\n"
             "Dwell comparison uses the same source CP25, seed and budget; training still switches on arrival. "
             "No new-grasp, geometry or hardware claim.", fontsize=9)
    fig.tight_layout(rect=[0, .10, 1, 1])
    fig.savefig(out / (prefix + "-evaluation.png"), dpi=160)
    plt.close(fig)

    analysis_path = base / "diagnostics/timed-goal-failure-components.json"
    analysis = json.loads(analysis_path.read_text())
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, (name, title) in zip(axes, [
        ("precision125-teacher-timed2seconds-perturb100", "Original precision teacher"),
        ("precision-cont-cost1-cp25-timed2seconds-perturb100", "Continuous CP25 teacher"),
        ("precision125-student-timed2seconds-perturb100", "Pilot student CP100")]):
        rows = analysis["results"][name]["rows"]
        ax.plot(range(1, 11), [r["attained"] for r in rows], "o-", label="Attained at some time", color="#237d9f")
        ax.plot(range(1, 11), [r["held"] for r in rows], "s-", label="Held at command end", color="#c35e45")
        ax.set_xticks(range(1, 11), ["O" if i%2 == 0 else "C" for i in range(10)])
        ax.set_xlabel("2-second commands: open / close")
        ax.set_title(title)
        ax.set_ylim(0, 108)
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Trials / 100")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.text(.02, .025, "Reached-but-not-held failures concentrate on closing: the slider returns toward open. "
             "Measured traces establish the failure pattern, not a unique physical cause.", fontsize=9)
    fig.tight_layout(rect=[0, .07, 1, 1])
    fig.savefig(out / (prefix + "-closing-hold-failures.png"), dpi=160)
    plt.close(fig)
    provenance.append(dict(path=str(analysis_path.relative_to(root)),
        sha256=hashlib.sha256(analysis_path.read_bytes()).hexdigest()))

    low = [read("verification/official-actuator-support%dmrad-cp25-perturb100" % span) for span in [40, 200]]
    static = [read("diagnostics/static-hold-" + hand) for hand in ["wuji_paper", "wuji_paper_official_actuator"]]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    ax = axes[0]
    for j, (key, label, color) in enumerate([
        ("successful_trials", "Complete", "#237d9f"), ("strict_first_cycle_trials", "First stable", "#359367"),
        ("stable_full_rollout_trials", "Full stable", "#d08142")]):
        bars = ax.bar(np.arange(2)+(j-1)*.25, [d[key] for d in low], .23, label=label, color=color)
        ax.bar_label(bars, fontsize=9, padding=2)
    ax.set_xticks([0, 1], ["40 mrad support", "200 mrad support"])
    ax.set_title("Retrained with official gains + armature\nCP25, development perturbations")
    ax.legend(loc="upper right", bbox_to_anchor=(1, .78), fontsize=8)
    ax = axes[1]
    bars = ax.bar([0, 1], [d["stable20s"] for d in static], .55, color=["#8899a6", "#359367"])
    ax.bar_label(bars, fontsize=10, padding=2)
    ax.set_xticks([0, 1], ["Original gains", "Official gains\nand armature"])
    ax.set_title("Hold initial joint targets, no manipulation\nBase stable for full 20 seconds")
    for ax in axes:
        ax.set_ylim(0, 113)
        ax.set_ylabel("Trials / 100")
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.text(.02, .02, "ArtBot contact geometry and PhysX retained. These are actuator sensitivity tests, not the full official MuJoCo model.\n"
             "Static pose/control measurements are valid; unavailable DOF sensor readings are not used as motor-force evidence.", fontsize=8.5)
    fig.tight_layout(rect=[0, .10, 1, 1])
    fig.savefig(out / (prefix + "-actuator-retraining.png"), dpi=160)
    plt.close(fig)

    text = """# Wuji 美工刀：持续开合、保持与执行器对照

本视频是学习策略闭环执行，600帧/30fps/20秒，无文字。CP100的SHA256为
`e68ebb65f14adbd912a1f9b39e1fcbf0b6621607e298f9f616fe09de7960e765`。
视频沿用预先固定的扰动行0/2/76，三格分别完成14/14/15次开合，
首次稳定3/3，全20秒稳定2/3；中间格最大转角0.3112rad超过0.25rad，失败保留。
该视频使用原ArtBot增益100/1，不是官方低增益策略视频。

CP100在开发100次为100次首次稳定、86次全程稳定；在预先声明的两个新种子
12203/13313上分别为100/100首次稳定、81/78次全程稳定，合计200/200与159/200。
这些都是同一个名义抓姿的微扰，不能称为新抓姿、新几何或真机泛化。

固定时间指令每2或5秒切换，不依靠到位事件；每段最后9个采样均需误差<2mm。
CP100的“全部末尾保持且全程刀身稳定”分别只有18/100、13/100。
原teacher和student轨迹分析发现，多次失败表现为关闭后又滑向打开。

同源CP25、同训练种子、新优化器、同预算的停留训练对照：

|训练停留|测试指令间隔|每段曾到位|每段末尾保持|末尾保持且全程握稳|
|---|---|---:|---:|---:|
|0.3秒|2秒|100|33|14|
|2秒|2秒|96|69|30|
|0.3秒|5秒|99|42|12|
|2秒|5秒|99|76|26|

每行100次。延长停留改善了保持，但没有解决刀身累计转动；尚未重复多个训练种子。
训练仍按到位事件切换，因此另行准备固定时间指令训练对照。

使用官方关节增益与armature重新训练的CP25：支撑范围±40mrad为100次完整、
100次首次稳定、45次全程稳定；±200mrad为98/29/0。此处为开发集，
低增益独立新种子与定时测试另行记录，不纳入以上CP100的200次成绩。
单独固定初始关节目标、完全不操作滑块时，原增益100/100、官方增益98/100能稳定20秒，
提示初始静态抓持可行，动态动作与接触协调还需改进。

低增益实验仍用ArtBot接触几何和PhysX，不能等同完整官方MuJoCo模型或真机标定。
静态实验的DOF传感器未有效启用，其零读数不作为力或电流证据。
全部实验报告及实际退出码、哈希列在provenance中；真机控制/电流换算尚未验证。
"""
    (out / (prefix + "-results.md")).write_text(text)
    (out / (prefix + "-provenance.json")).write_text(json.dumps(dict(
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reports=reports, artifacts=provenance), indent=2) + "\n")
    sums = [hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.name
            for p in sorted(out.iterdir()) if not p.name.endswith("SHA256SUMS.txt")]
    (out / (prefix + "-SHA256SUMS.txt")).write_text("\n".join(sums) + "\n")
    print(out)


if __name__ == "__main__":
    main()
