# 功能抓姿与交接续轮

Goal仍active/incomplete。flat_table_pickup=true为保留v104与v123原生证据；continuous_pickup_to_extension=false。placement_generalization/geometry_load_generalization均未到，vision_validated=false/real_robot_ran=false。

11个新的原生连续物理试验均未接通B。三种关键新机制：改变A为index/middle夹持且thumb预置滑块；actualindex/thumbcap-to-rail步进+位姿/挠度闭环；刀尖仍tablesupported时引入middle或双指换位。其失败由native接触/状态证据记录，B从未成立。所有沿轨/模型预载/相同中指进入分支停止，不累积相同PPO。既有取物成功和旧24mm推动基线均保留。

有信息的新几何结果：实际heldupright刀底/滑块二指抓姿可达，点误差35/18µm、完整35mmthumbstroke IK可达。其flat-table入口不可行：midedge与corner/联合placement都有tableconflicts，不能初始化held来称连续任务成功。actual对向夹持的有效支持在腕/指运动时丢失，geometrypoint保持不能证明loadretention。

复现：实验根source runs/contact-transfer-20261006/env.sh；每项command.json包含原Python -m完整参数，将--output改新目录执行。prefix在reproduction/runs/...附原路径。source/scripts保留本轮源码；原依赖、actor、资产复用。成功A入口 python -m scripts.run_wuji_flat_table_pickup_selected --output <fresh>，仅A，不含B。各视频从整刀平放与机器人接近前开始，43/56/61/62s全程、不拼接。失败例全部保留。

所有native为开发例，使用sim_oracle与已保存actualA先验/材料点；不是未知视觉或独立冻结验证。主动伸出未执行，用null而非pickup意外slider位移成绩。内部惯量/摩擦为保留工程假设；original努力/关节/速度界不变。

下一项行动需要改变功能抓取接触拓扑或取得实际受载稳定的新支持，不能重复边角middle、窄cap/railwalk、forceprojection与相同PPO。保留完整目标：新flatpickup→连续B→有限generalization。当前report是具体失败交付，不是Goal完成。
