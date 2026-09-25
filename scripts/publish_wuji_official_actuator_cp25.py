"""Publishable, failure-preserving artifacts for the official-actuator teacher."""
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
    base = root/"runs/wuji-goal"
    out = base/"release-official-actuator-cp25-20260922-0518"
    out.mkdir(exist_ok=True)
    prefix = "wuji-knife-official-actuator-cp25-20260922"
    names = ["official-actuator-support40mrad-cp25-perturb100",
             "official-actuator-support40mrad-cp25-blind-seed14503-perturb100",
             "official-actuator-support40mrad-cp25-blind-seed15613-perturb100",
             "official-actuator-support40-cp25-preset3-video"]
    reports, provenance = {}, []
    for name in names:
        p = base/"verification"/name
        status = json.loads((p/"status.json").read_text())
        assert status["status"] == "completed" and status["returncode"] == 0
        reports[name] = json.loads((p/"report.json").read_text())
        provenance.append(dict(path=str((p/"report.json").relative_to(root)),
            sha256=hashlib.sha256((p/"report.json").read_bytes()).hexdigest(), status=status))
    assert len({d["checkpoint_sha256"] for d in reports.values()}) == 1
    video = base/"verification"/names[-1]
    shutil.copy2(video/"policy.mp4", out/(prefix+"-three-trials-no-text-failures-retained.mp4"))
    shutil.copy2(video/"preview.png", out/(prefix+"-preview.png"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    ax = axes[0]
    for j, (key, label, color) in enumerate([
        ("successful_trials", "Complete", "#237d9f"), ("strict_first_cycle_trials", "First stable", "#359367"),
        ("stable_full_rollout_trials", "Full 20 seconds stable", "#d08142")]):
        values = [reports[n][key] for n in names[:3]]
        bars = ax.bar(np.arange(3)+(j-1)*.25, values, .23, label=label, color=color)
        ax.bar_label(bars, fontsize=8, padding=2)
    ax.set_xticks([0, 1, 2], ["1616\nDevelopment", "14503\nFresh", "15613\nFresh"])
    ax.set_ylabel("Trials / 100")
    ax.set_ylim(0, 112)
    ax.set_title("Low-gain CP25: one nominal grasp\n40 mrad support range")
    ax.legend(loc="lower left", fontsize=8)
    ax = axes[1]
    values = []
    for hand in ["wuji_paper", "wuji_paper_official_actuator"]:
        p = base/"diagnostics"/("multigrasp-static-"+hand)
        d = json.loads((p/"report.json").read_text())
        status = json.loads((p/"status.json").read_text())
        assert status["status"] == "completed" and status["returncode"] == 0 and d["num_envs"] == 5
        reports[p.name] = d
        values.append(d["stable20s"])
        provenance.append(dict(path=str((p/"report.json").relative_to(root)),
            sha256=hashlib.sha256((p/"report.json").read_bytes()).hexdigest(), status=status))
    bars = ax.bar([0, 1], values, .55, color=["#8899a6", "#359367"])
    ax.bar_label(bars, fontsize=10, padding=2)
    ax.set_xticks([0, 1], ["Original gains", "Official gains\nand armature"])
    ax.set_ylim(0, 5.6)
    ax.set_yticks(range(6))
    ax.set_ylabel("Grasps / 5")
    ax.set_title("Different validation grasp pool\nStatic hold, no learned actions")
    for ax in axes:
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.text(.02, .02, "ArtBot geometry + PhysX; official joint gains/armature only. "
             "Stable base: <10 mm translation and <0.25 rad rotation.\n"
             "Left: nominal-grasp perturbations. Right: five distinct development-validation grasps; four fall with low gains. No hardware claim.", fontsize=8.5)
    fig.tight_layout(rect=[0, .10, 1, 1])
    fig.savefig(out/(prefix+"-fresh-results-and-grasp-failures.png"), dpi=160)
    plt.close(fig)

    text = """# 官方执行器参数下的 Wuji CP25

模型固定为40mrad支撑范围的低增益teacher，完整CP25 SHA256：
`1a22aa97f87b8d4b2346ec21aa3e4be5b5cb86223b58ae61feb89e60a76a0f3f`。
仍是ArtBot几何与PhysX，只替换官方逐关节Kp/Kv和armature。

|评估|完整开合|首次握稳|全20秒握稳|
|---|---:|---:|---:|
|开发1616，100次|100|100|45|
|新种子14503，100次|100|97|46|
|新种子15613，100次|100|98|49|

独立新种子合计200/200完整、195/200首次握稳、95/200全程握稳。
都是一个名义抓姿的微扰，不是新抓姿或未见几何泛化。

无字视频在本机4090上录制，20秒、30fps、1536×384，沿用原先预定的0/2/76行。
三格分别10/2/7次开合，首次握稳3/3，**全20秒握稳0/3**。
左格最大旋转0.341rad，中格后续目标超时，右格位移24.64mm/旋转0.821rad。
三项失败全部保留，未换成好看的样本。这个3环境视频与H100上100环境评估不构成逐帧复现，
也不计入上面的200次新种子成绩；不能从三个例子断言差异由GPU型号单独造成。

独立静态检查还发现：旧多抓姿池的全部五个验证初态，在原增益下5/5稳定20秒，
在官方增益下仅1/5，另外4个掉落。与单案例100初态的98/100静态稳定是不同分布。
这些失败未从验证池删除；仅对33训练行另行测试初始化命令目标的内压，后续验证单独报告。

学习策略的固定时间指令保持正在另行训练；该CP25视频不能代表后续定时训练结果。
物性标定、实际电流/力矩换算、控制滤波、学生观测与硬件部署尚未验证。
"""
    (out/(prefix+"-results.md")).write_text(text)
    (out/(prefix+"-provenance.json")).write_text(json.dumps(dict(
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reports=reports, artifacts=provenance,
        video_metadata=json.loads((video/"media-check.json").read_text())), indent=2)+"\n")
    sums = [hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.name
            for p in sorted(out.iterdir()) if not p.name.endswith("SHA256SUMS.txt")]
    (out/(prefix+"-SHA256SUMS.txt")).write_text("\n".join(sums)+"\n")
    print(out)


if __name__ == "__main__":
    main()
