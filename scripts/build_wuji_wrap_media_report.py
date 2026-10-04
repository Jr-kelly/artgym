"""Self-contained public simulation report; embeds no user/private media."""
import argparse,base64,html,json
from pathlib import Path

R=Path(__file__).resolve().parents[1]
B=R/'runs/wrap-force-20261004'
D=R/'research/wrap-force-20261004'


def uri(path,mime):
    return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--results',type=Path,required=True)
    a=p.parse_args();result=json.loads(a.results.read_text())
    rows=[]
    for row in result['continuous_trials']:
        evaluation=row['evaluation'];ends=evaluation['slider_endpoints_m']
        values=[row['label']]+[f'{ends[k]*1000:.2f}' for k in ['extend1','return1','extend2','return2']]
        values+=['通过' if evaluation['continuous_pickup_demo_pass'] else '失败',
                 '、'.join(k for k,v in evaluation['checks'].items() if not v) or '全部满足']
        rows.append('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in values)+'</tr>')
    heading=['条件','伸出1 mm','缩回1剩余 mm','伸出2 mm','缩回2剩余 mm','连续功能','未满足项']
    force=result['force_scope'];force_rows=''.join('<tr><th>'+html.escape(k)+'</th><td>'+html.escape(v)+'</td></tr>' for k,v in force.items())
    panels=[]
    for name,title in [('new-wrap-corner-nominal-v20.mp4','原刀：完整36秒连续取刀与两轮操作'),
                        ('new-wrap-corner-highload-failure-v20.mp4','原刀：0.5 N基础容量代表性失败'),
                        ('paired-original-wrap-held-v31.mp4','原／新布局近景：两个独立持刀诊断，不计连续取刀demo')]:
        path=B/'media'/name
        caption=('两条独立持刀reset诊断，同权重和压力模型档位；每条36秒记录完整。' if name.startswith('paired-') else '单个未剪接物理回合，双视角同步。')
        panels.append('<article><h3>'+title+'</h3><video controls preload="metadata" src="'+uri(path,'video/mp4')+'"></video><p>'+caption+'字幕中的真实状态只用于评估。<a href="'+ 'https://github.com/Jr-kelly/artgym/releases/download/wuji-g2-wrap-force-20261005-v1/'+name+'">原始MP4</a></p></article>')
    for path,title in [(B/'figures/paired-continuous-v14/continuous-common-geometry.png','一次带误差估计与共同规则：四个留出尺寸的实际连续结果'),
                       (B/'figures/paired-continuous-v14/paired-held-actual-support.png','同权重、同压力档、匹配参考：实际承托分布（持刀诊断）'),
                       (B/'measurement/index-wrap-pressure080-series-v8/diagnostic-axial-curves.png','修改测力装置：轴向力、法向压力及有效区间'),
                       (B/'figures/paired-series-repeat-v26/paired-series-repeat.png','每抓姿两次独立串联装置测量：无效B缺测区间不填零'),
                       (B/'figures/recorded-wrap-geometry-v32/recorded-wrap-geometry.png','原碰撞几何与同步真实法向接触：不是实际接触面积或全接触力'),
                       (B/'media/paired-original-wrap-held-v31-frame780.png','原／新布局近景关键帧：两条独立持刀诊断'),
                       (B/'figures/directional-tracking-v22/directional-tracking.png','两轮切向目标追踪与实际接触')]:
        panels.append('<article><h3>'+title+'</h3><img loading="lazy" alt="'+html.escape(title)+'" src="'+uri(path,'image/png')+'"></article>')
    release='https://github.com/Jr-kelly/artgym/releases/tag/wuji-g2-wrap-force-20261005-v1'
    body='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wuji 包覆抓姿与双向测力交付</title><style>
body{font:17px/1.65 system-ui,sans-serif;background:#f3f5f7;color:#172331;margin:0}main{max-width:1180px;margin:auto;padding:28px}h1{font-size:30px}h2{margin-top:36px}article,.summary{background:white;padding:22px;margin:22px 0;border:1px solid #d8dfe6;border-radius:8px}video,img{display:block;width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:15px;background:white}th,td{padding:10px;border:1px solid #d8dfe6;text-align:left}a{color:#175cab}code{background:#eef1f4;padding:2px 5px}li{margin:8px 0}.scroll{overflow-x:auto}.muted{color:#526575}details{background:white;padding:16px;margin:16px 0}pre{white-space:pre-wrap;word-break:break-word;font-size:13px}
</style><main><h1>G2 + Wuji：包覆抓姿、连续伸缩与双向测力</h1>'''
    body+='<div class="summary"><p><strong>'+html.escape(result['demo_status'])+'</strong></p><p>'+html.escape(result['generalization_status'])+'</p><p>'+html.escape(result['remaining_blockers'])+'</p></div>'
    body+='<h2>完整连续行为与失败边界</h2><p>位置从导轨下限计起；缩回2.92 mm表示还剩2.92 mm。40 mm是任务命令，不是已实现的实际全行程。功能阈值为两次伸出&gt;25 mm、缩回剩余&lt;8 mm，并同时检查承托、跨轮漂移、接触和停留。</p><div class="scroll"><table><thead><tr>'+''.join('<th>'+v+'</th>' for v in heading)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    body+=''.join(panels[:3])
    body+='<h2>压力、实际推拉力、反力与能力边界</h2><table>'+force_rows+'</table><p>原刀轴向力与真机测量仍未完成。法向压力、设置容量、瞬时碰撞峰值和已知附加载荷不能互相替代。</p>'
    body+=''.join(panels[3:])
    body+='<h2>抓姿及策略对照</h2><p>'+html.escape(result['grasp_comparison'])+'</p><p>'+html.escape(result['training_selection'])+'</p><h2>恢复与真机准备</h2><p>'+html.escape(result['recovery_status'])+'</p><p>'+html.escape(result['hardware_status'])+'</p>'
    body+='<p><a href="'+release+'">新的 GitHub Release：代码、学习状态、配置、原始证据与视频</a></p><details><summary>机器、时间与利用率证据</summary><pre>'+html.escape(json.dumps(result.get('work_and_resources',{}),ensure_ascii=False,indent=2))+'</pre></details><details><summary>完整结果与证据路径</summary><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre></details><p class="muted">本HTML只嵌入本轮公开仿真视频和数据图，不包含用户原始照片或操作视频。仿真、训练拟合、冻结评估、独立恢复及真机结果分别标注。</p></main></html>'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(body);print(a.output,a.output.stat().st_size)


if __name__=='__main__':main()
