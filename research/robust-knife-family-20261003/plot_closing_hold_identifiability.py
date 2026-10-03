"""Plot fixed offline research predictions, never control input or selection."""
import pathlib,json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=pathlib.Path(__file__).resolve().parent;out=D/'closing-hold-identifiability-figure-v1';out.mkdir(exist_ok=False);mask=np.arange(512)%5==0
fig,ax=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
for t,c in [(8,'#237aad'),(16,'#bf6137')]:
 p=np.load(D/f'closing-hold-identifiability-{t}s-v1/predictions.npz');y=p['labels_mm'][mask,1];z=p['public134_history_stats_fresh'][mask,1];ax[0].scatter(y,z,s=18,alpha=.7,color=c,label=f'{t}s actual measured history');errors=np.sort(abs(z-y));ax[1].plot(errors,np.arange(1,len(errors)+1)/len(errors),color=c,label=f'{t}s; MAE {abs(z-y).mean():.3f} mm')
ax[0].plot([10,14],[10,14],'--',c='gray',lw=1);ax[0].set(xlabel='Scoring thickness label (mm)',ylabel='Offline predicted thickness (mm)',title='103 geometry-supervision heldout bodies');ax[0].legend(fontsize=8,loc='upper left');ax[1].set(xlabel='Absolute thickness error (mm)',ylabel='Fraction of all heldout cases',title='Fresh perturbations; fixed ridge=10');ax[1].legend(fontsize=8,loc='lower right');fig.suptitle('Pre-operation context diagnostic; training-family bodies, not policy validation',fontsize=10)
for ext in ['png','pdf']:fig.savefig(out/f'closing-hold-identifiability.{ext}',dpi=180)
print(str(out))
