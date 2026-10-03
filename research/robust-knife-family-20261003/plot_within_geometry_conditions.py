"""Descriptive post-primary conditional stability; not primary validation score."""
import pathlib,json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=pathlib.Path(__file__).resolve().parent;R=D.parents[1];j=json.loads((D/'exploratory-within-geometry-conditions-summary.json').read_text());out=D/'within-geometry-conditions-figure-v1';out.mkdir(exist_ok=False);ids=[f'h{i:04d}' for i in range(128)];thickness=np.array([json.loads((R/'assets/objects/knife_wuji_dense_under_20261003'/name/'parameters.json').read_text())['handle_size'][1]*1000 for name in ids]);fig,ax=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
for condition,color,marker in [('core','#2876a3','o'),('capacity','#b75936','x')]:
 s=j['conditions'][condition];counts=np.array([s['per_body'][name]['complete'] for name in ids]);assert counts.sum()==s['complete'];ax[0].scatter(thickness,counts,s=20,alpha=.75,c=color,marker=marker,label=f'{condition}: same128 bodies,32 conditions each');zero=np.array([sum((counts==0)&(thickness>=lower)&(thickness<lower+1)) for lower in [10,11,12,13]]);offset=-.15 if condition=='core' else .15;bars=ax[1].bar(np.arange(4)+offset,zero,width=.3,color=color,label=condition)
 for bar,value in zip(bars,zero):ax[1].text(bar.get_x()+bar.get_width()/2,value+.35,str(value),ha='center',fontsize=9)
ax[0].set(xlabel='Physical thickness (mm)',ylabel='Completed actual episodes out of32',title='Conditional stability per physical body',ylim=(-1,34));ax[0].legend(fontsize=7,loc='lower left');ax[1].set(xticks=np.arange(4),xticklabels=['10–11','11–12','12–13','13–14'],xlabel='Thickness grouping (mm)',ylabel='Bodies with zero completed episodes out of32',title='Persistent failure, all cases retained',ylim=(0,34));ax[1].legend(fontsize=8,loc='upper left');fig.suptitle('Exploratory after frozen332: correlated geometry/contact changes; no causal isolation',fontsize=10)
for ext in ['png','pdf']:fig.savefig(out/f'within-geometry-conditions.{ext}',dpi=180)
print(out)
