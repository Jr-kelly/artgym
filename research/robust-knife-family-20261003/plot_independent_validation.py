"""Publication artifacts from frozen outcomes only; never imported by controller."""
import json,pathlib,collections,hashlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
R=pathlib.Path(__file__).resolve().parents[2];D=R/"research/robust-knife-family-20261003";out=D/"independent-validation-figure-v1";out.mkdir(exist_ok=True)
j=json.loads((D/"independent-validation.json").read_text());assert j["total"]==332 and j["complete"]==204
names=list(j["conditions"]);labels=["Heldout core (8)","Heldout higher load (4)","Heldout core breadth (64)","Heldout higher-load breadth (32)","Slider height sensitivity (32)","Fresh 128 bodies, core (128)","Fresh first64, higher load (64)"]
colors={"Complete":"#148b76","Pickup / hold":"#d79a2b","Body unstable / drop":"#cb5260","Retraction":"#7070ab"}
fig,axes=plt.subplots(2,2,figsize=(13,9));ax=axes[0,0];left=np.zeros(7);categories=[("Complete",None),("Pickup / hold","pickup/hold"),("Body unstable / drop","body unstable/drop"),("Retraction","retraction")]
for label,key in categories:
 values=np.array([j["conditions"][n]["complete"] if key is None else j["conditions"][n]["failures"].get(key,0) for n in names]);ax.barh(np.arange(7),values,left=left,label=label,color=colors[label]);left+=values
for i,n in enumerate(names):
 c=j["conditions"][n];ax.text(c["n"]+1,i,f'{c["complete"]}/{c["n"]}',va="center",fontsize=9)
ax.set_yticks(np.arange(7));ax.set_yticklabels(labels,fontsize=9);ax.invert_yaxis();ax.set_xlim(0,148);ax.set_xlabel("All episodes (complete / total at right)");ax.set_title("A  All332 predeclared outcomes");ax.legend(fontsize=8,loc="upper right")
p=R/"runs/robust-knife-family-20261003/checks/independent-fresh-core-v1/report.json";report=json.loads(p.read_text());rows=report["episodes"];params=report["physical_asset_parameters"];T=np.array([x["handle_size"][1]*1000 for x in params]);W=np.array([x["handle_size"][0]*1000 for x in params]);complete=np.array([x["operation_complete"] for x in rows]);assert len(rows)==128
ax=axes[0,1]
for label,key in categories:
 mask=complete if key is None else np.array([r["failure"]==key for r in rows])
 if mask.any():ax.scatter(T[mask],W[mask],s=35,c=colors[label],label=label,alpha=.85,edgecolors="white",linewidths=.3)
ax.set_xlabel("Body thickness (mm), excludes slider");ax.set_ylabel("Body width (mm)");ax.set_xlim(10,14);ax.set_ylim(14,18);ax.set_title("B  128 fresh geometries, one core episode each")
ax=axes[1,0];counts=[]
for low in range(10,14):
 mask=(T>=low)&(T<low+1);n=int(mask.sum());c=int(complete[mask].sum());counts.append({"thickness_bin_mm":[low,low+1],"n":n,"complete":c});ax.bar(low+.5,c/n if n else 0,width=.72,color=colors["Complete"]);ax.text(low+.5,c/n+.04,f"{c}/{n}",ha="center",fontsize=11)
ax.set_ylim(0,1.15);ax.set_xticks([10.5,11.5,12.5,13.5]);ax.set_xticklabels(["10–11","11–12","12–13","13–14"]);ax.set_xlabel("Thickness bins (mm), fresh core only");ax.set_ylabel("Descriptive completion fraction");ax.set_title("C  Geometry gap persists; co-varying dimensions")
ax=axes[1,1];height=j["conditions"]["independent-height-sensitivity-v1"]["per_instance"]
for x,sid in enumerate(["sensitivity-height-minus1","sensitivity-height-plus1"]):
 c=height[sid];ax.bar(x,c["complete"]/c["n"],color=colors["Complete"],width=.55);ax.text(x,c["complete"]/c["n"]+.04,f'{c["complete"]}/{c["n"]}',ha="center",fontsize=11)
ax.set_xticks([0,1]);ax.set_xticklabels(["Slider −1 mm","Slider +1 mm"]);ax.set_ylim(0,1.15);ax.set_ylabel("Descriptive completion fraction");ax.set_title("D  Nominal body, joint perturbations retained")
for ax in axes.flat:ax.spines[["top","right"]].set_visible(False);ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
fig.suptitle("Frozen P50 TABLE workflow: 204 / 332 complete; necessary broad robustness remains blocked",fontsize=14)
fig.tight_layout(rect=[0,.065,1,.96]);fig.text(.02,.025,"Actual uninterrupted simulation; same nominal policy/controller throughout, all cases retained. Failure labels are priority categories, not chronological onsets.\nNearby engineering geometry/load/contact ranges only; repeated seeds are not new objects. No isolated thickness causality or real-robot reliability claim.",fontsize=9)
for suffix in ["png","pdf"]:fig.savefig(out/("independent-validation."+suffix),dpi=160)
summary={"source_report_sha256":hashlib.sha256((D/"independent-validation.json").read_bytes()).hexdigest(),"fresh_core_thickness_bins":counts,"height_sensitivity":height,"scope":"Descriptive frozen outcomes; no fitting/modelselection or causal/statisticalrealreliability claim"};(out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
