"""Public browsable results; embed only simulation media, never user media."""
import base64,html,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'research/traction-20261005';B=R/'runs/traction-20261005'
RELEASE='https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-traction-20261005-v1'
def uri(path,mime):return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
def main():
    r=json.loads((D/'DELIVERY-RESULTS.json').read_text());assert not r['missing'],r['missing']
    rows=[];travels=[]
    for row in r['trials']:
        e=row['evaluation'];ends=[f'{v*1000:.2f}' for v in e['slider_endpoints_m'].values()]
        outcome='通过' if e['continuous_pickup_demo_pass'] else '失败：'+', '.join(k for k,v in e['checks'].items() if not v)
        rows.append([row['label']]+ends+[outcome])
        travels.append([row['label']]+[f"{w['actual_signed_travel_mm']:+.2f}" for w in row['physical_stages']]+[f"{e['return_to_return_rotation_rad']:.4f}",f"{100*e['thumb_contact_substep_fraction']:.2f}%"])
    heading=['条件','伸1 mm','回1剩余 mm','伸2 mm','回2剩余 mm','原验收结果']
    def md_table(head,items):return '| '+' | '.join(head)+' |\n| '+' | '.join(['---']*len(head))+' |\n'+''.join('| '+' | '.join(v)+' |\n' for v in items)
    text='''# G2 + Wuji 双向牵引交付 · 2026-10-05

**冻结 V13 已改善主刀 0.35 档的两轮双向操作，连续取刀、本地录像、远端和空目录恢复均通过原功能验收；0.5 档及必要联合泛化仍未解决。** 本轮没有追加训练，没有改变物理力矩／速度约束、40 mm命令、两轮连续流程或验收阈值，没有发送真机命令。

## 机制、实现与证据

较高阻力下，旧控制的方向反转和第二轮初态失配参与了衰减。禁用 S120 的拇指残差、保留其承托残差，在任务换向时用已测关节与初始静态偏差重新锚定下一条完整40 mm参考；用初始估计几何的 FK 轴向雅可比把关节误差转换成米，保留12 mm等效／0.15 rad限幅和0.5 s混合。它不是滑块位置反馈或力控制，在线不读取物体、接触、负载真值。

V9消融表明“只关拇指残差”不足，配合切向重锚才有收益。欧氏关节投影低估了运动点轴向误差；V12改用FK后，0.35档回缩裕量改善。最终保持原默认抓姿和S120权重，因此改进来自控制改动组合，不能单独归因于接触面积。`THUMB-RESIDUAL-ABLATION-V9.json`和`CARTESIAN-CONTROLLER-V12.json`保留了对照。

宽面方案在高阻下仍丢失接触；虚拟运动点居中并未让实际接触居中，居中／中线候选反而恶化。全关节重锚、承托位置保持和缩短运动时长没有稳定收益，均未选用。30 Hz采样的驱动力矩未呈现饱和证据，但不能排除未记录的子步峰值，也不能证明只缺推力。

0.5档额外轴向追踪补偿可达29.36／2.00／29.23／3.70 mm，接触约99.92%，但相对转角0.757 rad超过0.6 rad，仍失败。移除或加大承托残差仍超转角，后者还破坏漂移和停留。这是当前承托与轴向运动协调的具体未解边界；不是物理不可能的证明。没有据此盲目增加训练更新数。

## 冻结连续结果

位置从原资产导轨下限计起，端点为原验收规定的末一秒中位数。>25 mm伸出、<8 mm回缩之外，还同时检查抬起、相对位姿包络、跨轮漂移、最终停留和持续接触。历史world-pose评分保留，不能替代functional-criterion-v1。40 mm命令、约50 mm机械行程、实际分段运动和实物完全收刀是不同量。

'''+md_table(heading,rows)+'''
本地和远端是两个环境复跑；空目录恢复在同一台本地机器上得到同样轨迹，属于恢复验证，不增加随机重复样本数。以上数量不足以给出成功率置信区间。

## 每段实际有符号位移

以下是16–21／21–26／26–31／31–36 s中真实首末样本的差，故不等于上表中位端点相减。轨迹、240 Hz接触原始记录及30 Hz汇总分别保存。

'''+md_table(['条件','伸1位移 mm','回1位移 mm','伸2位移 mm','回2位移 mm','跨轮转角 rad','拇指接触'],travels)+'''
## 泛化与证据边界

薄刀130×14×10、滑块轴向+5 mm、012/015旧留出实例均作为开发回归，不伪装成新留出。主刀和这些回归仍使用相同的带误差初始几何适配机制；000–011训练划分未改，也未训练012–015。

fresh01–04在V13冻结后预先固定，联合尺寸／滑块位置、非零初始估计误差、摩擦、关节噪声、延迟或变化容量。结果不用于调参。fresh04首次因把对称随机偏差的“幅值”写成负数，在物理运行前报错；只改为同绝对幅值，保持种子、几何和控制器不变，重跑证据为v15r1。原失败保留。只有fresh04通过；其余分别受第二轮伸出／姿态包络、第二回缩和跨轮漂移限制。必要联合泛化仍为false。

## A／B／C／D与真机

V13本地0.35原刀拇指法向A均值约0.764 N，匹配基线约0.733 N；这不是恒压力承诺。原刀总轴向接触力B和实际导轨反力C都缺测，JSON为null。D仅是指定完整连续任务在模拟容量配置下通过的有限证据。0.35／0.5是基础容量参数，沿程还有起动／卡槽调制，不是实测阻力或最大推拉力；没有把旧修改串联装置±0.2 N替代原刀或真机测量。

硬件仍缺实际SDK／固件／关节映射和带时间戳接口、执行器响应、同一刀的有效全行程与双向阻力、一次初始几何标定。直接复用上一轮[REAL-MEASUREMENT.md](../wrap-force-20261004/REAL-MEASUREMENT.md)和[HARDWARE-PREPARATION.md](../wrap-force-20261004/HARDWARE-PREPARATION.md)，旧离线回放时序不作为新V13的SDK结果。没有自动下发真机动作。

## 代码、视频与恢复

默认入口：`python -m scripts.run_wuji_traction_selected --output <新目录>`，默认0.35档。S120 SHA256为`ad16a153c27eb01567c14422ca8ed23e5bebfc6e1c901683031f245631944d2a`。原R800和teacher／normalizer保持匹配；本轮只有源码／资产适配和冻结仿真，没有新训练拟合，也没有真机结果。

新Release提供小增量恢复包、选定原始证据、三条未剪接36秒MP4及嵌入媒体的HTML。恢复依赖上一Release的两个有固定SHA256的包，licensed Isaac Gym不分发。一次全新目录解包、逐项校验并运行单入口已通过，见RESTORE-RESULT-V17.json和REPRODUCE.md。公开包不含用户原始私人照片／视频；本地private目录保留。

下一步应从高阻完整取刀末态出发，针对支撑迁移与刀体转动重新设计／学习协调；在出现几何或行为收益后再短训。fresh01–04已消耗为验证证据，后续选择须另留新条件。取得实际阻力与SDK后再收紧真机模型，不能将此次仿真交付称为真机就绪。

## 资源与状态

两台机器只运行有用工作，远端实际为4张H200。监测从本轮启动后才有覆盖，不足完整四小时；远端均值低于26%门槛、未达40%目标。没有用填充作业弥补，也不声称利用率合规。精确时间、样本覆盖、每卡记录见DELIVERY-RESULTS.json/resources和证据包。

`functional_demo_ready=true`；`necessary_generalization_resolved=false`、`axial_force_measurement_resolved=false`、`hardware_ready=false`、`real_robot_ran=false`、`goal_complete=false`。交付状态只由PUBLIC-DELIVERY-RECEIPT.json中的实际发布回执确认；归档STATE可能是制作时快照。
'''
    (D/'FINAL-REPORT.md').write_text(text)
    def table(head,items):return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(v)+'</th>' for v in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in row)+'</tr>' for row in items)+'</table></div>'
    body='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wuji 双向牵引结果</title><style>body{font:17px/1.65 system-ui;margin:0;background:#f2f5f7;color:#152536}main{max-width:1200px;margin:auto;padding:28px}article{background:white;padding:20px;margin:24px 0;border:1px solid #ccd6df;border-radius:8px}video,img{width:100%;height:auto}table{border-collapse:collapse;background:white;font-size:14px}th,td{padding:9px;border:1px solid #cbd5df;text-align:left}.scroll{overflow:auto}pre{white-space:pre-wrap;word-break:break-word;font-size:14px}a{color:#125f9d}</style><main><h1>G2 + Wuji：0.35 档双向牵引改进</h1><article><p><strong>冻结V13的完整连续取刀和两轮操作在主刀0.35档通过；0.5档和必要联合泛化仍失败。</strong></p><p>原默认抓姿、S120承托策略、真实尺寸和物理限制保留。禁用拇指残差，并以合法关节测量及初始FK轴向误差在换向时重锚完整40 mm参考。未追加训练、未发送真机动作。</p><p>0.35是模拟被动制动容量配置，不是实测推力。端点为距原导轨下限的位置，回缩剩余不是实物完全收刀。</p></article>'''
    body+=table(heading,rows)
    for name,title in [('traction035-continuous.mp4','V13：完整36秒连续取刀、两轮伸出—保持—缩回—保持'),('baseline-v13-035-comparison.mp4','相同0.35容量：旧基线与V13近景逐帧对照'),('traction050-failure.mp4','V13：0.5档代表性失败，原始判据未变')]:
        body+='<article><h2>'+title+'</h2><video controls preload="metadata" src="'+uri(B/'media'/name,'video/mp4')+'"></video><p>每个源均为完整未剪接物理回合。字幕真值仅用于评估。<a href="https://github.com/Jr-kelly/artgym/releases/download/wuji-g2-traction-20261005-v1/'+name+'">原始MP4</a></p></article>'
    body+='<article><h2>真实运动、接触、法向力和相对转动</h2><img src="'+uri(B/'media/behavior-comparison.png','image/png')+'"><p>A法向约0.764 N；原刀B轴向总接触力、C实际导轨反力均未测得，不填零。</p></article>'
    body+='<h2>每段真实有符号位移</h2>'+table(['条件','伸1 mm','回1 mm','伸2 mm','回2 mm','跨轮rad','接触'],travels)
    body+='<article><h2>完整说明与证据边界</h2><pre>'+html.escape(text)+'</pre></article><p><a href="'+RELEASE+'">代码、恢复包、证据与原始MP4 Release</a></p><details><summary>资源记录与完整JSON</summary><pre>'+html.escape(json.dumps(r,ensure_ascii=False,indent=2))+'</pre></details></main></html>'
    out=B/'release/Wuji-Traction-Report.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(body);print(out)
if __name__=='__main__':main()
