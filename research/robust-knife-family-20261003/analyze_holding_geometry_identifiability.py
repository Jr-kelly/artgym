"""Exploratory pre-operation geometry identifiability; labels never actor inputs."""
import pathlib,json,zipfile,hashlib,collections
import numpy as np
R=pathlib.Path(__file__).resolve().parents[2];D=R/"research/robust-knife-family-20261003";out=D/"holding-geometry-identifiability-v1";out.mkdir(exist_ok=False)
def first_rows(path,key,n=512):
 with zipfile.ZipFile(path) as z, z.open(key+".npy") as f:
  version=np.lib.format.read_magic(f);shape,fortran,dtype=np.lib.format._read_array_header(f,version);assert not fortran and shape[0]>=n
  count=n*int(np.prod(shape[1:]));data=f.read(count*dtype.itemsize);assert len(data)==count*dtype.itemsize
  return np.frombuffer(data,dtype=dtype).reshape((n,*shape[1:])).copy()
def load(name):
 folder=R/"runs/robust-knife-family-20261003/estimator"/name;path=folder/"data.npz";j=json.loads((folder/"report.json").read_text());pack=first_rows(path,"packets");public=first_rows(path,"features")[:,:134];groups=first_rows(path,"groups");times=first_rows(path,"times");assert pack.shape==(512,2076) and public.shape==(512,134) and np.array_equal(groups,np.arange(512)) and np.all(times==16)
 hist=pack[:,:2000].reshape(512,50,40);q=hist[:,:,:20];targets=pack[:,2055:2075]
 X={"current_q_targets":np.concatenate([q[:,-1],targets],1),"public134":public,"public134_holding_stats":np.concatenate([public,q.mean(1),q.std(1),q[:,-1]-q[:,0]],1)}
 return X,j,[json.loads(x) for x in (folder/"episodes.jsonl").read_text().splitlines()],pack,public
X,train_report,train_episodes,pack,public=load("temporal-capacity-train-v1");fresh,fresh_report,fresh_episodes,fpack,fpublic=load("temporal-capacity-fresh-v1")
params=[json.loads((R/"assets/objects/knife_wuji_dense_under_20261003"/f"t{i:04d}"/"parameters.json").read_text()) for i in range(512)];y=np.array([[*p["handle_size"],p["slider_origin"][0],p["slider_origin"][2]] for p in params])*1000;train=np.arange(512)%5!=0;valid=~train;assert train.sum()==409 and valid.sum()==103
labels=["W_mm","T_mm","L_mm","slider_joint_origin_x_mm","slider_joint_origin_z_mm"];models={};predictions={};summary={"scope":"Exploratory pre-operation geometry identifiability on512 RLtraining-family bodies. Geometry supervision heldout103 groups, not independent whole-policy/generalization/force evidence. All initial episodes included, no success filtering. Fresh perturbations for same training-family bodies, no h or012–015. Not deployed, no primary P50 change.","labels":labels,"fit_n":409,"geometry_supervision_heldout_n":103,"packet_time_s":16,"train_data_sha256":train_report["data_sha256"],"fresh_data_sha256":fresh_report["data_sha256"],"fixed_ridge_lambda":10,"models":{}}
def metric(pred,truth,rows):
 pickup=np.array([row["pickup_valid"] for row in rows]);err=abs(pred-truth)
 return {"n":len(pred),"mae_mm":dict(zip(labels,err.mean(0).tolist())),"T_p90_abs_error_mm":float(np.quantile(err[:,1],.9)),"T_error_gt1mm_count":int((err[:,1]>1).sum()),"T_mae_pickup_valid_mm":float(err[pickup,1].mean()) if pickup.any() else None,"T_mae_pickup_invalid_mm":float(err[~pickup,1].mean()) if (~pickup).any() else None}
ym=y[train].mean(0);ys=y[train].std(0);constant=np.tile(ym,(512,1));names=["constant_mean",*X.keys()]
for name in names:
 if name=="constant_mean":pred=constant;fpred=constant
 else:
  mean=X[name][train].mean(0);std=np.maximum(X[name][train].std(0),.02);xx=(X[name]-mean)/std;fx=(fresh[name]-mean)/std;yt=(y[train]-ym)/ys;weight=np.linalg.solve(xx[train].T@xx[train]+10*np.eye(xx.shape[1]),xx[train].T@yt);pred=xx@weight*ys+ym;fpred=fx@weight*ys+ym
  models[name+"_weight"]=weight;models[name+"_input_mean"]=mean;models[name+"_input_std"]=std
 predictions[name]=pred;predictions[name+"_fresh"]=fpred;summary["models"][name]={"input_dim":0 if name=="constant_mean" else X[name].shape[1],"fit_train":metric(pred[train],y[train],[train_episodes[i] for i in np.flatnonzero(train)]),"geometry_heldout_original_errors":metric(pred[valid],y[valid],[train_episodes[i] for i in np.flatnonzero(valid)]),"geometry_heldout_fresh_errors":metric(fpred[valid],y[valid],[fresh_episodes[i] for i in np.flatnonzero(valid)]),"seen_geometry_fresh_errors":metric(fpred[train],y[train],[fresh_episodes[i] for i in np.flatnonzero(train)])}
models.update(label_mean_mm=ym,label_std_mm=ys,train_groups=np.flatnonzero(train),validation_groups=np.flatnonzero(valid));np.savez_compressed(out/"ridge-models.npz",**models);np.savez_compressed(out/"predictions.npz",labels_mm=y,**predictions);np.savez_compressed(out/"actual-initial-legal-packets.npz",train_packets=pack,fresh_packets=fpack,train_public134=public,fresh_public134=fpublic)
summary["model_sha256"]=hashlib.sha256((out/"ridge-models.npz").read_bytes()).hexdigest();(out/"report.json").write_text(json.dumps(summary,indent=2));print(json.dumps({name:item["geometry_heldout_fresh_errors"] for name,item in summary["models"].items()}))
