"""Text-free paired geometry replay, with failures and selection disclosed."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    out=base/'release-thickness-video-20260922';out.mkdir(exist_ok=False)
    evidence=out/'evidence';evidence.mkdir()
    prefix='wuji-knife-thickness-comparison-20260922'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    reports={};sources={};videos=[]
    for variant in ['nominal','body7']:
        folder=base/'verification'/('geometry-'+variant+'-rows0-4-7-video-timed2seconds')
        status=json.loads((folder/'status.json').read_text());assert status['status']=='completed' and status['returncode']==0
        report=json.loads((folder/'report.json').read_text());assert report['initial_state_rows']==[0,4,7]
        with np.load(folder/'trace.npz') as loaded:
            trace={k:loaded[k] for k in ['active','slider','goal','drift','rotation','fall','invalid']}
        scored=score_timed_trace(trace,60,9,600)
        assert all(report[k]==scored[k] for k in ['records','stable_full_all_endpoints','alive_full'])
        reader=imageio.get_reader(folder/'policy.mp4');count=sum(1 for frame in reader);reader.close();assert count==600
        for name in ['trace.npz','source.py','source_metrics.py','report.json','status.json','config.yaml','policy.mp4']:
            source=folder/name;sources[str(source.relative_to(root))]=sha(source)
            if name!='policy.mp4':shutil.copy2(source,evidence/(variant+'-'+name))
        reports[variant]=report;videos.append(folder/'policy.mp4')
    movie=out/(prefix+'-nominal-top-thin-bottom-no-text.mp4')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-hide_banner','-loglevel','error','-n','-i',str(videos[0]),'-i',str(videos[1]),
        '-filter_complex','[0:v][1:v]vstack=inputs=2[v]','-map','[v]','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p',str(movie)],check=True)
    reader=imageio.get_reader(movie);count=0
    for frame in reader:
        assert frame.shape==(768,1536,3)
        if count==300:imageio.imwrite(out/(prefix+'-frame-at-10seconds.png'),frame)
        count+=1
    reader.close();assert count==600
    protocol=json.loads((base/'geometry-thickness-video-proposal.json').read_text())
    protocol.update(video_sha256=sha(movie),frames=count,fps=30,text_overlays=False,reports=reports,source_sha256=sources,
        rerun_variation='Original full32 thin-geometry trials at selected rows: 1joint/3,2alive/3. Three-environment rendered rerun:2joint/3,3alive/3. Different batching changed the trajectory; video is illustrative and does not replace the32trial results.')
    assert [reports[v]['stable_full_all_endpoints'] for v in ['nominal','body7']]==[3,2]
    assert reports['body7']['alive_full']==3
    (out/(prefix+'-provenance.json')).write_text(json.dumps(protocol,indent=2)+'\n')
    shutil.copy2(Path(__file__),evidence/'package_wuji_thickness_video.py')
    shutil.copy2(base/'geometry-thickness-video-proposal.json',evidence/'selection-proposal.json')
    (out/(prefix+'-README.md')).write_text('''# 无文字刀身厚度对照视频

上排：147×19 mm、刀身厚8 mm（含滑块共11 mm）；下排：相同长宽、刀身厚7 mm（含滑块共10 mm）。左右三列是同一批扰动初态的第0、4、7行。每2秒切换开/关目标，共20秒；同一个冻结teacher，原导入惯量，无脚本关节轨迹，无文字叠加。

选行发生在32样本评估之后：第0行是第一个成功，第4行是7 mm组第一个联合失败，第7行是第一个掉落。它们是诊断示例，不增加独立评估分母。

32环境原评估中，这三行在薄刀组为1/3联合、2/3存活；改为3环境带渲染复跑后为2/3联合、3/3存活，原刀组3/3联合。这种批量/运行差异已保留，视频不能代替完整32样本报告，也不能声称严格重复了原来的掉落轨迹。

完整几何评估的薄刀组为25/32联合，名义尺寸32/32。视频未使用新训练的适应模型；仍为特权teacher的PhysX仿真，不是真机或可部署student。ZIP保存两次视频对应的全部评分轨迹、源码和配置。
''')
    with zipfile.ZipFile(out/(prefix+'-evidence.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(evidence.iterdir()):z.write(p,p.name)
    (out/(prefix+'-SHA256SUMS.txt')).write_text('\n'.join(sha(p)+'  '+p.name for p in sorted(out.iterdir()) if p.is_file())+'\n')
    print(json.dumps(dict(output=str(out),assets=6,frames=count,video=str(movie))))


if __name__=='__main__':main()
