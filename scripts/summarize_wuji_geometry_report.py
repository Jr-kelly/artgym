"""Generate complete source-stratified Markdown tables from independent scoring."""
import argparse,json
from pathlib import Path
def interval(x):return f'{100*x[0]:.1f}–{100*x[1]:.1f}%'
def main():
 p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--title',required=True);p.add_argument('--static-suffix',required=True);a=p.parse_args();result=json.loads((a.analysis/'report.json').read_text());assets=json.loads(Path('research/geometry-generalization-20261002/ASSETS.json').read_text());rows=result['rows'];pairs=result['paired'];lines=['# '+a.title,'','统计单位为 episode；S 为全程严格端点及稳定性，F 功能与全程持握稳定性分别报告。条件成功率以静态有效初态为前提，无有效抓姿的来源为覆盖缺口。95% 区间采用 Wilson；配对差异使用保留同初态配对的 bootstrap。','','## 抓姿适配覆盖','','|条件|L/W/T mm|来源|尝试|生成|几何有效|静态有效|评测分母|','|---|---|---:|---:|---:|---:|---:|---:|']
 labels=list(dict.fromkeys(r['geometry'] for r in rows))
 for label in labels:
  name=label+'-'+a.static_suffix
  if a.static_suffix=='static-fixed' and label=='baseline':name='baseline-static-screen-v2'
  path=Path('runs/geometry-generalization-20261002')/name/'selection.json'
  if not path.exists():continue
  for s in json.loads(path.read_text())['sources']:
   dims='/'.join(f'{x:g}' for x in assets[label]['dimensions_mm_LWT']);lines.append(f"|{label}|{dims}|{s['source']}|{s['attempted']}|{s['generated']}|{s['geometry_accepted']}|{s['static_valid']}|{s['selected']}|")
 lines+=['','## 每条件、来源与协议','','|条件|来源|协议|模型|成功 n/N|成功 Wilson95|全程稳定 n/N|稳定 Wilson95|成功且稳定 n/N|','|---|---:|---|---|---|---|---|---|---|']
 for r in rows:lines.append(f"|{r['geometry']}|{r['source']}|{r['protocol']}|{r['model']}|{r['success']}/{r['n']}|{interval(r['wilson95'])}|{r['body_stable']}/{r['n']}|{interval(r['body_wilson95'])}|{r['success_and_full_stability']}/{r['n']}|")
 lines+=['','## Teacher/student 同初态配对','','成功指标四格依次为：两者成功、仅 teacher、仅 student、两者失败。差值为 teacher − student，百分点。','','|条件|来源|协议|N|成功四格|成功差值 pp [95%]|持握四格|持握差值 pp [95%]|','|---|---:|---|---:|---|---|---|---|']
 for r in pairs:
  formatted=[]
  for metric in ['success','body_stable']:
   v=r[metric];four='/'.join(str(v[k]) for k in ['both_success','teacher_only','student_only','both_fail']);ci=v['paired_bootstrap95'];formatted.extend([four,f"{100*v['teacher_minus_student']:.1f} [{100*ci[0]:.1f}, {100*ci[1]:.1f}]"])
  lines.append('|'+ '|'.join([r['geometry'],str(r['source']),r['protocol'],str(r['n']),*formatted])+'|')
 lines+=['','完整原始 episode 与连续误差、行程、首次到位/失稳等字段见同目录分析 CSV/JSON。几何等权汇总分为完整四来源覆盖与仅可用来源两类；后者不能解释为总体尺寸覆盖。未评测条件及零覆盖不加入条件成功率分母。','']
 a.output.write_text('\n'.join(lines));print(a.output)
if __name__=='__main__':main()
