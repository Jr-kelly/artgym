"""Authorized exact-tree Git Data transport; preserve existing branches and private local files."""
import base64,json,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scripts.publish_wuji_wrap_snapshot import api
from scripts.host_tool_environment import host_tool_environment
from scripts.record_wuji_rear_event import record
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'research/rear-sim2real-20261009';BRANCH='feat/wuji-rear-sim2real-20261009'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def main():
    target=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip();mp=D/'github-commit-map.json'
    mapping=json.loads(mp.read_text()) if mp.exists() else {}
    parent=mapping.get('last_local','a1ebb4c95315abb940a1f7c46cc12c4e1d894102');remote=mapping.get(parent,'d2124cb0d98db5c4c97a71d8492733c7cb4642c0')
    assert api('git/commits/'+remote)['tree']['sha']==git('rev-parse',parent+'^{tree}').decode().strip()
    protected=json.loads((D/'GITHUB-START-HEADS.json').read_text())
    for branch,expected in protected.items():
        if branch!=BRANCH:assert api('git/ref/heads/'+branch)['object']['sha']==expected,branch
    names=git('diff','--name-only','-z',parent,target).split(b'\0')[:-1]
    for n in names:
        path=n.decode();assert path.startswith('research/rear-sim2real-20261009/') or (path.startswith('scripts/') and 'wuji_rear' in path) or path=='scripts/g2_local_python.sh',path
        assert not any('private' in part.lower() for part in Path(path).parts),path
        assert not path.endswith('.mp4'), 'Videos belong in Release assets'
    record('rear_source_publication_started',evidence=[str(mp)],config=dict(local_commit=target,remote_parent=remote,files=len(names)),next_step='Verify exact source tree and create only authorized new branch')
    def blob(n):
        path=n.decode();mode,kind,expected=git('ls-tree','HEAD','--',path).decode().split()[:3];assert kind=='blob'
        actual=api('git/blobs',dict(encoding='base64',content=base64.b64encode(git('show','HEAD:'+path)).decode()))['sha'];assert actual==expected
        return dict(path=path,mode=mode,type='blob',sha=actual)
    with ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(blob,names))
    actualtree=api('git/trees',dict(base_tree=git('rev-parse',parent+'^{tree}').decode().strip(),tree=entries))['sha'];assert actualtree==tree
    a=git('show','-s','--format=%an%n%ae%n%aI%n%cn%n%ce%n%cI','HEAD').decode().strip().splitlines()
    commit=api('git/commits',dict(message=git('show','-s','--format=%B','HEAD').decode().rstrip('\n'),tree=tree,parents=[remote],author=dict(name=a[0],email=a[1],date=a[2]),committer=dict(name=a[3],email=a[4],date=a[5])))['sha']
    try:existing=api('git/ref/heads/'+BRANCH)['object']['sha']
    except RuntimeError as e:
        if '404' not in str(e):raise
        api('git/refs',dict(ref='refs/heads/'+BRANCH,sha=commit))
    else:
        assert existing in [remote,commit], 'Independent branch changes; refuse force update'
        if existing!=commit:subprocess.run(['/home/agiuser/.local/bin/gh','api','repos/Jr-kelly/artgym/git/refs/heads/'+BRANCH,'--method','PATCH','--input','-'],input=json.dumps(dict(sha=commit,force=False)).encode(),cwd='/tmp',env=host_tool_environment(),stdout=subprocess.PIPE,check=True)
    assert api('git/ref/heads/'+BRANCH)['object']['sha']==commit
    for branch,expected in protected.items():
        if branch!=BRANCH:assert api('git/ref/heads/'+branch)['object']['sha']==expected,branch
    mapping[target]=commit;mapping['last_local']=target;mp.write_text(json.dumps(mapping,indent=2))
    result=dict(local_commit=target,github_commit=commit,tree=tree,branch=BRANCH,protected_branch_heads_unchanged=True)
    (D/'SOURCE-PUBLICATION.json').write_text(json.dumps(result,indent=2));record('rear_source_branch_published',evidence=[str(D/'SOURCE-PUBLICATION.json')],config=result,next_step='Publish and hash-verify authorized evidence and video Release assets');print(json.dumps(result))
if __name__=='__main__':main()
