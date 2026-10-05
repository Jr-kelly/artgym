"""Publish the authorized singlepush source tree; no force update or private media."""
import base64,json,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from scripts.publish_wuji_wrap_snapshot import api
from scripts.host_tool_environment import host_tool_environment
from scripts.record_wuji_contact_transfer_event import record
R=Path(__file__).resolve().parents[1];D=R/'research/contact-transfer-20261006'
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
def main():
    branch='feat/wuji-contact-transfer-20261006';sha=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
    mapping_path=D/'github-commit-map.json';mapping=json.loads(mapping_path.read_text()) if mapping_path.exists() else {}
    parent=mapping.get('last_local','df7a3240c92b2d2c771d3981b4be1d012190f4c9');remote_parent=mapping.get(parent,'cae68dbda71dcb31954d34bd669394e445a2ccc4')
    assert api('git/commits/'+remote_parent)['tree']['sha']==git('rev-parse',parent+'^{tree}').decode().strip()
    names=git('diff','--name-only','-z',parent,sha).split(b'\0')[:-1]
    def blob(name):
        path=name.decode();assert not any('private' in part.lower() for part in Path(path).parts) and not path.lower().endswith(('.mp4','.jpg','.jpeg','.png','.html'))
        metadata=git('ls-tree','HEAD','--',path).decode().split()
        if not metadata:return dict(path=path,mode='100644',type='blob',sha=None)
        mode,kind,expected=metadata[:3];assert kind=='blob'
        actual=api('git/blobs',dict(encoding='base64',content=base64.b64encode(git('show','HEAD:'+path)).decode()))['sha'];assert actual==expected
        return dict(path=path,mode=mode,type='blob',sha=actual)
    record('source_publication_started',evidence='research/contact-transfer-20261006/STATE.json',config={'local_commit':sha,'parent':parent,'remote_parent':remote_parent,'files':len(names)},next_step='Verify exact source tree and create/update authorized branch')
    with ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(blob,names))
    remote_tree=api('git/trees',dict(base_tree=git('rev-parse',parent+'^{tree}').decode().strip(),tree=entries))['sha'];assert remote_tree==tree
    values=git('show','-s','--format=%an%n%ae%n%aI%n%cn%n%ce%n%cI','HEAD').decode().strip().splitlines()
    commit=api('git/commits',dict(message=git('show','-s','--format=%B','HEAD').decode(),tree=tree,parents=[remote_parent],author=dict(name=values[0],email=values[1],date=values[2]),committer=dict(name=values[3],email=values[4],date=values[5])))['sha']
    try:existing=api('git/ref/heads/'+branch)['object']['sha']
    except RuntimeError as e:
        if '404' not in str(e):raise
        api('git/refs',dict(ref='refs/heads/'+branch,sha=commit))
    else:
        assert existing in [remote_parent,commit],'Independent remote changes; refuse force update'
        if existing!=commit:subprocess.run(['/home/agiuser/.local/bin/gh','api','repos/Jr-kelly/artgym/git/refs/heads/'+branch,'--method','PATCH','--input','-'],input=json.dumps(dict(sha=commit,force=False)).encode(),cwd='/tmp',env=host_tool_environment(),check=True,stdout=subprocess.PIPE)
    assert api('git/ref/heads/'+branch)['object']['sha']==commit
    mapping[sha]=commit;mapping['last_local']=sha;mapping_path.write_text(json.dumps(mapping,indent=2))
    record('source_branch_published',evidence=str(mapping_path.relative_to(R)),config={'local_commit':sha,'github_commit':commit,'tree':tree,'branch':branch},updates={'github_branch':branch,'github_commit':commit},next_step='Publish and verify prepared Release artifacts')
    print(json.dumps(dict(local_commit=sha,github_commit=commit,tree=tree,branch=branch)))
if __name__=='__main__':main()
