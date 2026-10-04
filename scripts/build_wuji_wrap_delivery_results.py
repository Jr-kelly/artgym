"""Build public delivery facts from completed native evaluations only."""
import datetime, json
from pathlib import Path

B=Path('runs/wrap-force-20261004'); D=Path('research/wrap-force-20261004')


def main():
    state=json.loads((D/'STATE.json').read_text())
    start=datetime.datetime.fromisoformat(state['round_start_utc'])
    now=datetime.datetime.now(datetime.timezone.utc)
    cases=[('主刀，基础容量0.2 N',B/'continuous/index-wrap-v8-direct-corner-mass-corrected-v4')]
    cases += [('留出几何'+s,B/'validation'/('wrap-direct-corner-geometry'+s+'-v14')) for s in ['012','013','014','015']]
    cases += [(label,B/'validation'/name) for label,name in [
        ('主刀，基础容量0.35 N','wrap-frozen-v12-load035-v1'),
        ('主刀，基础容量0.5 N','wrap-frozen-v12-load050-v1'),
        ('联合关节扰动／延迟／脉冲负载','wrap-frozen-v12-joint-pulse-v1'),
        ('主刀，指节摩擦假设降至0.4','remote-wrap-proximal040-load020-v28')]]
    trials=[]
    for label,path in cases:
        ev=json.loads((path/'functional-evaluation.json').read_text())
        report=json.loads((path/'report.json').read_text())
        trials.append(dict(label=label,trial=str(path),evaluation=ev,
            physical_dimensions_WTL_m=report['physical_dimensions_WTL_m'],
            brake_capacity_parameter=report['integration_diagnostics'],
            actual_thumb_normal_mean_N=report['pair_pressure']['operation_thumb_pressure_mean_N']))
    result=dict(generated_utc=now.isoformat(),release_tag='wuji-g2-wrap-force-20261005-v1',
        demo_status='完整连续仿真已做成：G2＋Wuji从原桌角拿刀、持稳、两轮40 mm伸缩命令与保持；默认V12名义功能通过，无夹具、换握、定时位置锁存或中途重置。真机未运行。',
        generalization_status='同S120及统一一次带误差估计规则，012–015四个留出几何有实际连续通过记录；降低指节摩擦的一个假设条件也通过。未证明覆盖全部130–140×14–18×10–14 mm范围、全部滑块±5/±1/±1 mm组合或联合必要泛化。',
        remaining_blockers='0.35/0.5 N基础制动容量存在第二轮伸出及回缩不足；联合观测扰动／延迟／负载仍有失败。原刀总轴向力B及真实导轨反力C未校准；实物阻力、有效行程和SDK单位／接口缺失。新宽面拇指候选虽能形成长行程和多段真实承托，仍有跨轮转动／高负载失联，未替换默认。',
        force_scope={
            'A 法向压力':'默认V12原刀实际拇指—滑块法向均值约0.747 N；0.8 N是关节偏差模型的目标档位，不是恒力或测量值。提高到约1 N实际法向力没有改善高阻力双向操作。',
            'B 实际轴向推拉力':'原刀完整接触对力通道未完成。经过动基座校准的修改串联装置中，包覆布局两次记录的四段有效运动中值约+0.200/−0.202 N，有效归因比例>99.7%。质量、世界加速度、重力及实际弹簧力已计入；装置改变动力学，不能冒称原刀或真机测量。瞬时起动前峰值约0.75/0.86 N只是两次瞬态，不是可重复起动力上限。',
            'C 导轨实际反力与配置容量':'真实导轨反力尚未通过校准。原刀名义沿程配置容量约0.20–0.514 N、0.5档约0.50–1.285 N；是被动制动的有限容量，不是每刻实际反力或实物阻力上限。失败C校准残差约0.09 N，未输出有效C曲线。',
            'D 完整任务负载能力':'仅报告已测试配置：默认0.2基础容量profile完整通过，0.35/0.5已有失败；不是连续单调最大负载区间。已知平衡轴向附加载荷0.025/0.05/0.10 N使第二轮伸出不足，未建立正附加负载的完整任务下界，不把基础容量相加称推力。'},
        grasp_comparison='192缓存条目来自四个原始来源的各48附近扰动。四来源先与当前及包覆候选匹配G2映射、初始估计、闭合／取刀路径和双向参考；部分子场景可行、接回取刀失败，不作机械不可行结论。原source2与包覆布局在同S120/.8模型档、原刀及匹配参考的持刀对照中，第二轮伸出21.71→33.42 mm；这是抓姿和必要控制适配的共同收益，非纯几何独立归因。两布局均已有原食指link4真实接触，不能说首次启用指节。新布局另有中指、小指指腹承托；掌面未证明必要贡献。',
        training_selection='同750初始化、64环境×120更新×128步的单／多抓姿短训在共同012–015持刀留出条件均通过，未显示多抓姿分布扩展收益。选单抓姿S120，SHA256 ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a。连续及拇指头短训未改善、及时停训，失败44/12状态保留且不替换默认；修复冻结参数Adam保存问题。训练拟合、冻结评估、独立恢复、脚本取刀与真机分别标记。',
        recovery_status='代码／资产／配置、teacher＋2076维R800＋154维残差及模型／Adam／RNG可恢复。V20包在空目录独立解包，实际默认连续回合通过；学习状态实际恢复并保存更新121，该更新处于前缀、没有操作能力提升证据。最终包另给内容清单，SDK不分发。',
        hardware_status='Wuji原生块index/middle/pinky/ring/thumb各4关节，G2右臂idx61–idx67。离线600帧推理中位3.24ms、p95 5.54ms，与记录目标最大差0.01543rad，未证明SDK或逐位重放一致。首次真机仍需实际双向阻力／完全收刀／有效行程、一次刀位标定和SDK名称、单位、符号、有限位置接口及时间戳。本轮未连接动作传输。',
        continuous_trials=trials,
        flags=dict(delivery_complete=state.get('delivery_complete',False),functional_demo_ready=True,
            necessary_generalization_resolved=False,hardware_ready=False,real_robot_ran=False,
            axial_force_measurement_resolved=False,goal_complete=False),
        work_and_resources=dict(round_start_utc=state['round_start_utc'],generated_utc=now.isoformat(),
            elapsed_hours=(now-start).total_seconds()/3600,minimum_work_hours=12,
            minimum_finish_utc=state['minimum_finish_utc'],no_subagents=True,no_filler_or_hidden_jobs=True,
            inventory='Local4090＋authorized SSH4H200, not8GPUs',gpu_hour_cap=None,
            local_snapshot=json.loads((B/'resources/local-20261004/status.json').read_text()),
            development_last_fetched_snapshot=json.loads((B/'resources/development-reconnected-v15/status.json').read_text()),
            remote_rule_status='Remote whole-machine26% floor /40% target not demonstrated; sampling low and SSH unavailable15:00–18:34UTC, interruption cause unknown. Fresh timestamps/partial coverage retained, no hidden occupancy.'),
        evidence=dict(selected='FROZEN-WRAP-CONTINUOUS-CANDIDATE-V12.json',
            independent_geometry='DIRECT-CORNER-ONCE-ESTIMATE-CONTINUOUS-V14.json',
            actual_force_repeat='PAIRED-SERIAL-INDEPENDENT-REPEAT-V26.json',
            new_grip_negative='WIDE-FACE-PHYSICAL-COMPARISON-V24-V27.json',
            reverse_and_support='WIDE-FACE-REVERSE-AND-SUPPORT-V29-V30.json',
            material='PROXIMAL-MATERIAL-SENSITIVITY-V28.json',
            actual_recovery='EXTRACTED-RUNTIME-CONTINUOUS-RECOVERY-V20.json',
            actual_learning_resume='EXTRACTED-LEARNING-STATE-RESUME-V21.json'))
    (D/'DELIVERY-RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Wrote completed native results; elapsed %.2fh'%result['work_and_resources']['elapsed_hours'])


if __name__=='__main__':main()
