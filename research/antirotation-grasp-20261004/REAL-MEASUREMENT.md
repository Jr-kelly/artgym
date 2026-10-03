# 双向滑块最小测量（未取得实测数据）

固定本轮真实135×16×12 mm刀柄主体，不含滑块凸起；这把刀无需按下解锁。刀片收起并保持刀身安全固定，用已有推拉力计沿滑块方向缓慢推进、拉回。不要磨卡槽或更换刀具。没有力计时先记录带尺视频与行程，牛顿值留空，视频不能标定阻力。

1. 记录刀片完全收起的滑块位置作为0 mm，测量实际有效行程；不能把仿真40 mm指令、50 mm导轨或回缩<8 mm当成实物端点。
2. 每方向记录起动峰值，然后每约2–5 mm记录沿程阻力，明显卡点加一行；重复2次即可看基本一致性。推拉方向分别记extend/retract。阻力列为沿运动反方向的非负力大小N，不填写SDK effort。
3. 如已有条件，再记录另一档真实按压力；不要求新购工具。无法测法向按压力则该列为空，不能据关节目标偏置填恒力值。
4. 记录仪器、日期、安装方式、重复编号及完全收起标定。分开记录按压力条件，不把不同条件平均成一条真实曲线。

CSV列：`direction,position_mm,resistance_N,phase,repeat,normal_pressure_N`。phase为startup/running；normal_pressure_N可空。导入入口：

```bash
python -m scripts.fit_wuji_passive_resistance --csv measurements.csv --output research/measured-knife-profile
```

输出原始点/分方向简化曲线图、测量范围和被动制动容量profile。容量拟合是工程近似，不等于已验证真实卡槽动力学，也不是实际每帧推力或阻力上限。未测行程之外不推断能力。合成例只验证解析与拟合链路，不作实物标定。
