"""Browsable scientific delivery report with embedded frames and original videos."""
import argparse,base64,datetime,hashlib,html,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'runs/antirotation-grasp-20261004';D=R/'research/antirotation-grasp-20261004';TAG='wuji-g2-antirotation-grasp-20261004-v1';DOWNLOAD='https://github.com/Jr-kelly/artgym/releases/download/'+TAG+'/'
def read(path):return json.loads(path.read_text())
def embedded(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
def case_row(title,evaluation,role):
    ends=evaluation['slider_endpoints_m'];numbers=' / '.join('%.1f'%(1000*ends[k]) for k in ['extend1','return1','extend2','return2'])
    return '<tr><td>'+html.escape(title)+'</td><td>'+role+'</td><td>'+numbers+'</td><td>'+('功能通过' if evaluation['continuous_pickup_demo_pass'] else '未通过')+'</td><td>'+('通过' if evaluation['legacy_full_success'] else '未通过')+'</td><td>'+html.escape(', '.join(k for k,v in evaluation['checks'].items() if not v) or '全部预先判据通过')+'</td></tr>'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--final',action='store_true');a=p.parse_args();media=B/'presentation';assert media.exists();rows=[];scopes=[]
    for label,name in [('V17 主刀 .2/.2','actual-table-projected-grasp-frozen750-load2-v17'),('V18 主刀 .5/.5','actual-table-projected-grasp-frozen750-load5-v18'),('V24 薄刀柄 .2/.2','actual-table-thin-allcontact-frozen750-load2-v24')]:rows.append(case_row(label,read(B/'continuous'/name/'functional-evaluation.json'),'开发'))
    for row in read(B/'height-development-four-v1/outcomes.json'):rows.append(case_row('高度变体 '+str(row['case']),row['result'],'已知训练形态开发；未按结果挑样本'))
    for row in read(D/'RING-SUPPORT-DEVELOPMENT.json')['rows']:rows.append(case_row(row['case']+' 无名指支点',row['functional'],'新接触开发；两候选均停止，非匹配消融'))
    for label,versions in [('range04',['v32','v33']),('range12',['v34','v35'])]:
        for kind,version in zip(['nominal','thin'],versions):
            path=B/'continuous'/('actual-table-'+kind+'-table-prior-'+label+'-frozen50-load2-'+version)/'functional-evaluation.json'
            if path.exists():rows.append(case_row('新5s接管 '+label+' '+kind,read(path),'新训练冻结50开发'))
    necessary=B/'necessary24-frozen25-development-v1/outcomes.json'
    if necessary.exists():
        for model in read(necessary)['rows']:
            for case in model['checks']:rows.append(case_row('保留750 '+model['kind']+' '+case['case'],case['result'],'必要24形态训练后冻结25开发；不是新联合独立验证'))
    fresh=B/'fresh-joint-validation4-v1/outcomes.json';freeze=D/'FRESH-JOINT-ACTOR-FREEZE.json';freshtext='新联合条件尚未执行；不得宣称独立验证完成。';freshrows=[]
    if fresh.exists():
        data=read(fresh);freshtext='冻结后四个预先登记的新联合条件：%d/%d 功能通过。四个样本不代表宽范围可靠性或真机能力。'%(sum(r['functional_pass'] for r in data['rows']),len(data['rows']))
        for row in data['rows']:
            if row.get('result'):freshrows.append(case_row('新联合条件 '+str(row['case']),row['result'],'本轮冻结后的首次联合条件；非跨模型/真机'))
            else:freshrows.append('<tr><td>新联合条件 '+str(row['case'])+'</td><td colspan="5">'+html.escape(row['status'])+'，作为失败保留</td></tr>')
    if a.final:
        assert fresh.exists() and len(read(fresh)['rows'])==4
        assert (B/'newprefix-recovery-v1/resume-receipt.json').exists(),'Material resume/replay evidence required before final report'
        assert necessary.exists() and len(read(necessary)['rows'])==2,'New necessary24 critical contrast must close before final delivery'
        assert datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime.fromisoformat(read(D/'STATE.json')['earliest_12h_utc'])
    sections=[];keyframes=[]
    for name,title,caption in [('v17-annotated','主刀完整功能连续例','135×16×12 mm刀柄，冻结750；桌面取刀后两轮40mm指令，实测行程并非字面40mm；.2/.2 N被动容量。'),('height4-annotated','滑块凸起与位置变化完整开发例','同一750与统一初始估计适配；4mm凸起、轴向−5mm和横向+1mm附近，名义刀柄，.2/.2。必要全范围仍未解决。'),('v18-annotated','较高阻力回缩失败','主刀.5/.5 N被动容量，压力与握持仍在而行程/回缩不足；容量不是实物阻力上限或瞬时推力。'),('previous-grasp-annotated','旧轮抓姿与真实接触形态对照','前一正式交付V138：.5/.5、手摩擦.65、新观察不同。本轮V18手摩擦.8。仅展示抓姿/接触差异，不是参数匹配的消融或成功率比较。')]:
        receipt=read(media/(name+'.json'));imagepath=media/(name+'-extension.png');keyframes.append({'name':name,'video_sha256':receipt['video_sha256'],'frames':receipt['frames']})
        sections.append('<article><h2>'+title+'</h2><p>'+caption+'</p><video controls preload="none" poster="'+embedded(imagepath)+'" src="'+DOWNLOAD+name+'.mp4" data-local="'+name+'.mp4"></video><p><a href="'+DOWNLOAD+name+'.mp4">完整双视角MP4</a> · 1080帧 / 36秒 / 30Hz，未经阶段拼接</p><img class="frame" src="'+embedded(imagepath)+'" alt="实际连续视频关键帧"></article>')
    selected=read(freeze) if freeze.exists() else None
    selectedtext=html.escape(json.dumps(selected,ensure_ascii=False,indent=2)) if selected else '尚未冻结新联合验证候选。当前最强名义功能例使用未变更750。'
    figure=embedded(B/'figures/contact-signatures-v1/contact-signatures.png')
    content='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>G2 + Wuji 抗转动抓姿本轮交付</title><style>body{font:16px/1.65 system-ui,sans-serif;max-width:1160px;margin:36px auto;padding:0 20px;color:#192535;background:#f5f7fa}article,section{background:white;padding:24px;margin:22px 0;border:1px solid #d7dde5;border-radius:10px}h1{font-size:28px}h2{font-size:21px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #d7dde5;text-align:left}video,.frame{width:100%;height:auto}pre{overflow:auto;font-size:12px;background:#eef2f6;padding:16px}.status{border-left:5px solid #cf8a1b;padding:16px;background:#fff5dc}a{color:#075eae}.scroll{overflow:auto}</style><h1>G2 + Wuji v1：抗转动功能抓姿与带阻力回缩</h1>'''
    content+='<p class="status">完整连续仿真功能例已做成：主刀及一个凸起/位置变化开发例。必要尺寸与高阻力泛化尚未解决；未运行真机动作。'+('本轮交付完成，研究目标未全部完成。' if a.final else '工作中预览，训练、冻结新联合验证与最终交付仍待完成。')+'</p>'
    content+='''<section><h2>改动与实际意义</h2><p>保留G2/Wuji原始执行器、重力和接触网格。围绕刀柄布置中指、小指下方承托、食指侧向支撑，并把拇指全行程参考与取刀/提升/支撑交接连接起来。统一适配只读一次带噪声的尺寸/滑块接触估计；不向策略输入当前刀姿、滑块位置、力、接触真值或资产ID。位置预压和关节偏置不等于恒力。</p><p>新增5秒接管分支用配置桌面与初始估计、实测机械臂FK建立相位正确的初始位姿。16秒只改变软件动作参考，物理、历史与RNN连续。旧16秒接管750结果保持不变。训练拟合、冻结开发、首次新联合验证和真机结果分别记录。</p><p>外部指令保持40mm。行为判据在实验前登记：两次伸出&gt;25mm、回缩&lt;8mm、两次回缩间位姿漂移有限、末次持稳、拇指接触持续。历史0.25rad判据单独保留，不把新的功能通过包装成旧判据通过或实物完全收起。</p></section>'''
    content+='<section><h2>实际行为证据</h2><p>位移列依次为伸出末1 / 回缩末1 / 伸出末2 / 回缩末2，均为距仿真导轨下限的位置，单位mm；回缩末的位置不是回缩移动距离或真实刀片完全收起的测量。</p><div class="scroll"><table><tr><th>条件</th><th>科学角色</th><th>实测行程</th><th>功能</th><th>旧判据</th><th>失败项</th></tr>'+''.join(rows+freshrows)+'</table></div><p>'+freshtext+'</p></section>'
    content+=''.join(sections)
    content+='<section><h2>新5秒接管实际完整伸出与剩余回缩失败</h2><p>V33 薄刀柄两次伸出约36mm，但第二次回缩末仍9.27mm、循环间转动0.185rad、末次持稳未通过。保持全部预先判据，未围绕9.27与8mm作增益微调。</p><video controls preload="none" src="'+DOWNLOAD+'newprefix-thin-failure-annotated.mp4" data-local="newprefix-thin-failure-annotated.mp4"></video><p><a href="'+DOWNLOAD+'newprefix-thin-failure-annotated.mp4">V33 完整实际取刀与两轮操作MP4</a>；失败不晋升为可运行成功候选。</p></section>'
    content+='<section><h2>无名指新支点与闭环承托的负结果</h2><p>V36 在提升后把无名指移到对侧下缘，原网格全行程几何检查通过，但实际刀柄接触仅约22%，未完成高阻力回缩。V37 在原关节范围内用实测关节与前次实际下发目标的滞后作有限接触搜索，提前结束支撑过渡；14.3秒冻结，随后保留50帧真实历史再执行原750策略。它是关节跟踪负载代理，不是牛顿力反馈或接触归属传感器。</p><p>V37 的搜索停止在+0.0195rad，操作中无名指刀柄接触约38%，下方承托法向均值约0.024N；拇指滑块法向均值反而约0.511N，零接触连续2.2秒。两次伸出22.74/11.56mm、回缩末10.61/8.75mm，循环间转动0.330rad。两条路线均作为失败停止，没有继续扫位置、阈值或增益。不同过渡时序意味着该比较不能证明反馈单一因素的因果效果。</p><p><a href="'+DOWNLOAD+'ring-tracking-failure-annotated.mp4">V37 完整双视角失败视频</a>；V36/V37 原始全景、近景、接触轨迹和配置均在视频/证据包。</p></section>'
    content+='<section><h2>接触与抗转动线索</h2><img class="frame" src="'+figure+'"><p>薄刀柄首次伸出时食指—刀柄法向贡献接近零，支撑长轴力矩随循环改变。只改善回缩的保留控制仍损失第二伸出并出现转动漂移；较高容量条件即使持续压住滑块也不能完成回缩。该观察是下一步承托/推进协同的可检验线索，不是单一因果证明。主刀.2/.2配置的实际沿程约束容量为0.20–0.51 N，.5/.5为0.50–1.29 N；拇指法向操作均值分别约0.77/0.74 N。这些是不同物理量，不能直接当作轴向牵引力、恒力或实物阻力上限。字幕与图中力来自已校验的仿真接触对法向贡献、240Hz采样汇总，未重建摩擦牵引力或实测卡槽阻力。</p></section>'
    content+='<section><h2>压紧、切向贡献与回缩过程</h2><img class="frame" src="'+embedded(B/'figures/loaded-return-evidence-v1/loaded-return-evidence.png')+'"><p>轴向曲线只为接触法向矢量的滑块局部z投影，摩擦牵引未重建。四例控制与几何不同，不把并列曲线当匹配因果消融；容量与法向力也不是同一种量。灰色为回缩/保持，右列把刀体相对手转动与主动转腕分别显示。</p></section>'
    content+='''<section><h2>恢复与首次真机缺项</h2><p>运行包含原750、匹配teacher/R800、必要配置与RUN-V17.sh；新学习包保留模型、Adam、CPU/CUDA/NumPy及新增场景随机流。续训开始新物理回合，不宣称按位恢复求解器状态。隔离源码/依赖恢复已实际重复V17完整36秒并得到同一轨迹哈希。离线桥仅允许四类记录：已知时钟、实测手/臂关节、已下发目标。新5秒回放从独立已知计划生成参考，不读取未来记录目标。</p><p>首次真机仍缺G2/Wuji实际SDK/固件与关节名称/符号/零位/单位、带时间戳测量和有限位置目标接口、执行器与重力响应、一次初始刀/滑块标定，以及真实双向起动力、沿程阻力、有效行程和完全收起端点。SDK effort未经核实不能当Nm/N；本轮没有自动连接设备或下发动作。CSV采集及被动阻力拟合入口已离线准备。</p><p><a href="https://github.com/Jr-kelly/artgym/releases/tag/'''+TAG+'''">本轮Release：运行、学习、原始视频、失败证据与运行命令</a> · <a href="https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-support-pressure-20261003-v1">前一正式交付</a></p></section>'''
    content+='<section><h2>冻结候选与选择依据</h2><pre>'+selectedtext+'</pre><p>只根据预先规定的名义与薄刀柄开发门槛选择候选，再打开四个新联合条件；不按新验证结果重选策略或反复运行以求通过。</p></section>'
    content+="<script>document.querySelectorAll('video').forEach(v=>v.addEventListener('error',()=>{if(!v.dataset.triedLocal){v.dataset.triedLocal='1';v.src=v.dataset.local;}}));</script></html>"
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(content);receipt=dict(final=a.final,generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit_at_generation=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),report_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),media=keyframes,scope='Embeddedactualframes plus standaloneuncutMP4 links; rawfullviews/traces inReleasearchive. Truthshown onlyfor evaluation. No currentobject/force actorinput or realrobotclaim.');a.output.with_suffix('.manifest.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='media'}))
if __name__=='__main__':main()
