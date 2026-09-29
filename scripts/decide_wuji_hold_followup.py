"""Apply the recorded followup thresholds to primary equal-budget results only."""
import argparse
import datetime
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=json.loads(a.analysis.read_text());assert result['status']=='independently_rescored'
    rows=result['summaries'];sources=[];eligible=[];replicate=[]
    def values(source,model):
        selected=[next(x for x in rows if x['source']==source and x['model']==model and x['protocol']==protocol)
                  for protocol in ['fixed2','fixed5']]
        return dict(strict_mean_pct=sum(100*x['success']/x['n'] for x in selected)/2,
                    body_mean_pct=sum(100*x['body_stable']/x['n'] for x in selected)/2,
                    strict_counts={x['protocol']:[x['success'],x['n']] for x in selected})
    for source in [3,11]:
        metrics={model:values(source,model) for model in ['parent','original-final','dense1-final']}
        original=metrics['original-final'];changed=metrics['dense1-final']
        benefit=changed['strict_mean_pct']-original['strict_mean_pct']
        body=changed['body_mean_pct']-original['body_mean_pct']
        replication=benefit>=10 and body>=-5
        if replication:replicate.append(dict(source=source,benefit_pp=benefit,body_change_pp=body))
        # Equal success ties favor unchanged reward, then lower source index for
        # a starting expert. Never consult development-selected final tests.
        best=max(['original-final','dense1-final'],key=lambda model:(metrics[model]['strict_mean_pct'],model=='original-final'))
        qualifies=metrics[best]['strict_mean_pct']>=50 and metrics[best]['strict_mean_pct']>metrics['parent']['strict_mean_pct']
        if qualifies:eligible.append(dict(source=source,model=best,**metrics[best]))
        sources.append(dict(source=source,metrics=metrics,changed_minus_original_pp=benefit,
                            body_change_pp=body,replication_trigger=replication,integration_trigger=qualifies))
    eligible.sort(key=lambda x:(-x['strict_mean_pct'],x['source']))
    replicate.sort(key=lambda x:(-x['benefit_pp'],x['source']))
    decision=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,
        replication_priority=replicate,integration_sources=[0,1,2]+sorted(x['source'] for x in eligible) if eligible else [],
        integration_starting_expert=eligible[0] if eligible else None,
        excluded_additional_sources=[source for source in [3,11] if not any(x['source']==source for x in eligible)],
        scope='Thresholds from preregistration: changed-original mean strict2/5>=10pp and body drop<=5pp for paired seed replication; expert mean>=50% and above parent for integration. Primary CP2000 only. Triggers are budget-conditional experimental priorities, not statistical proof or a launch instruction.')
    a.output.write_text(json.dumps(decision,indent=2)+'\n');print(json.dumps(decision,indent=2))


if __name__=='__main__':main()
