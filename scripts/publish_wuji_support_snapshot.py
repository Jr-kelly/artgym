"""GitHub Git Data transport fallback for this explicitly authorized delivery.
Never force-updates a branch. Repository origin points to the local recovery clone; API blobs/tree preserve every staged byte and record commit mapping.
"""
import argparse,base64,json,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scripts.record_wuji_support_goal import R,D,record
from scripts.host_tool_environment import host_tool_environment

def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def api(path,payload=None):
    cmd=['/home/agiuser/.local/bin/gh','api','repos/Jr-kelly/artgym/'+path]
    if payload is not None:cmd+=['--method','POST','--input','-']
    result=subprocess.run(cmd,input=None if payload is None else json.dumps(payload).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd='/tmp',env=host_tool_environment())
    if result.returncode:raise RuntimeError(path+': '+result.stderr.decode()[:300])
    return json.loads(result.stdout)

def main():
    p=argparse.ArgumentParser();p.add_argument('--branch',default='feat/wuji-support-pressure-20261003');a=p.parse_args();assert a.branch.startswith('feat/wuji-support-pressure-20261003')
    sha=git('rev-parse','HEAD').decode().strip();parent='995f5acd72f4038b1b3ca3be921248620975d54a';tree=git('rev-parse','HEAD^{tree}').decode().strip();mapping_path=D/'github-commit-map.json';mapping=json.loads(mapping_path.read_text()) if mapping_path.exists() else {};parent=mapping.get('last_local',parent);remote_parent=mapping.get(parent,'6afe8270735abf91b86b001803150e542d720111')
    entries=[]
    for item in git('diff','--name-status','-z',parent,sha).split(b'\0')[:-1:2]:assert item in [b'A',b'M'], 'Fallback only handles actual addition/modification snapshot'
    names=git('diff','--name-only','-z',parent,sha).split(b'\0')[:-1]
    def blob(name):
        path=name.decode();metadata=git('ls-tree','HEAD','--',path).decode().split();mode,kind,expected=metadata[:3];assert kind=='blob'
        body=git('show','HEAD:'+path);actual=api('git/blobs',dict(encoding='base64',content=base64.b64encode(body).decode()))['sha'];assert actual==expected
        return dict(path=path,mode=mode,type='blob',sha=actual)
    record('github_snapshot_api_upload_started',local_commit=sha,local_tree=tree,parent=parent,remote_parent=remote_parent,files=len(names),reason='Repository origin is local recovery clone; use authorizedGitHub GitData API exact-tree transport',next='Verify server tree matches exact local tree, then non-force branch update')
    with ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(blob,names))
    newtree=api('git/trees',dict(base_tree=git('rev-parse',parent+'^{tree}').decode().strip(),tree=entries))['sha'];assert newtree==tree
    author=git('show','-s','--format=%an%n%ae%n%aI%n%cn%n%ce%n%cI','HEAD').decode().strip().splitlines();message=git('show','-s','--format=%B','HEAD').decode().rstrip('\n')
    commit=api('git/commits',dict(message=message,tree=newtree,parents=[remote_parent],author=dict(name=author[0],email=author[1],date=author[2]),committer=dict(name=author[3],email=author[4],date=author[5])))['sha']
    refpath='git/refs/heads/'+a.branch
    try:existing=api('git/ref/heads/'+a.branch)['object']['sha']
    except RuntimeError as e:
        if '404' not in str(e):raise
        api('git/refs',dict(ref='refs/heads/'+a.branch,sha=commit))
    else:
        assert existing in [remote_parent,commit], 'Remote branch changed independently; no forced update'
        if existing!=commit:
            cmd=['/home/agiuser/.local/bin/gh','api','repos/Jr-kelly/artgym/'+refpath,'--method','PATCH','--input','-'];subprocess.run(cmd,input=json.dumps(dict(sha=commit,force=False)).encode(),cwd='/tmp',env=host_tool_environment(),check=True,stdout=subprocess.PIPE)
    assert api('git/ref/heads/'+a.branch)['object']['sha']==commit
    mapping[sha]=commit;mapping['last_local']=sha;mapping_path.write_text(json.dumps(mapping,indent=2))
    record('github_snapshot_published',local_commit=sha,github_commit=commit,git_tree_sha1=tree,branch=a.branch,source='Exact identical Git tree; API commit metadata/parent mapping recorded',next='Continue experiments; this is an interim recoverable branch snapshot, not final Release',state_updates={'github_branch':a.branch,'github_commit':commit,'local_scientific_commit':sha})
    print(json.dumps(dict(local_commit=sha,github_commit=commit,tree=tree,branch=a.branch)))
if __name__=='__main__':main()
