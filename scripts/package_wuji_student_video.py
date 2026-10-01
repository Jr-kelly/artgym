"""Rescore and label the preregistered four-column development videos."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np

from scripts.wuji_timed_command_metrics import score_timed_trace


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_video(path, frames=600):
    reader = imageio.get_reader(path)
    metadata = reader.get_meta_data()
    count = 0
    try:
        for frame in reader:
            assert frame.ndim == 3 and frame.shape[2] == 3
            count += 1
    finally:
        reader.close()
    assert count == frames and abs(metadata['duration'] - frames / 30) < .2
    return dict(decoded_frames=count, duration_seconds=metadata['duration'],
                dimensions=list(metadata['size']), sha256=sha(path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--role', choices=['teacher', 'student'], required=True)
    parser.add_argument('--paired-teacher', type=Path)
    args = parser.parse_args()
    plan = json.loads(Path('research/unified-student-20261001/video-plan.json').read_text())
    report = json.loads((args.input / 'report.json').read_text())
    assert report['initial_state_rows'] == plan['rows'] and len(report['records']) == 4
    assert report['protocol']['kind'] == 'S' and report['protocol']['stage_seconds'] == 2
    is_student = args.role == 'student'
    assert bool(report['unified_student_sha256']) == is_student
    assert report['control_mode'] == ('initial_calibration_conditional_student' if is_student else 'privileged_teacher')
    with np.load(args.input / 'trace.npz') as archive:
        trace = {key: archive[key] for key in archive.files}
    assert len(trace['active']) == 600
    score = score_timed_trace(trace, report['protocol']['stage_steps'], 9, 600)
    valid = trace['active'] & ~trace['fall'] & ~trace['invalid']
    body = valid.all(0) & (trace['drift'] < .01).all(0) & (trace['rotation'] < .25).all(0)
    for index, row in enumerate(score['records']):
        row['body_stable'] = bool(body[index])
    assert score['records'] == report['records']
    raw = verify_video(args.input / 'policy.mp4')
    assert raw['dimensions'] == [2048, 384], 'Requires the registered four-column render'
    assert not args.output.exists()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    model_hash = report['unified_student_sha256'] if is_student else report['checkpoint_sha256']
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title = ('Initial-calibration-conditional STUDENT' if is_student else 'Eagg6100 privileged TEACHER')
    header = f'{title} | one weight set | S2, 20 seconds | SHA {model_hash[:12]}'
    filters = ["pad=2048:512:0:64:color=black",
               f"drawtext=fontfile={font}:text='{header}':x=14:y=8:fontsize=23:fontcolor=white",
               f"drawtext=fontfile={font}:text='RTX4090 rendered resimulation, four fixed development states. H200 batch statistics are separate. No hardware result.':x=14:y=38:fontsize=18:fontcolor=white"]
    for source, row in enumerate(score['records']):
        strict = 'PASS' if row['stable_full_all_endpoints'] else 'FAIL'
        body = 'PASS' if row['body_stable'] else 'FAIL'
        color = 'lime' if strict == 'PASS' else 'red'
        filters += [f"drawtext=fontfile={font}:text='Source {source} | STRICT {strict}':x={source*512+14}:y=452:fontsize=22:fontcolor={color}",
                    f"drawtext=fontfile={font}:text='20s body {body} | fixed row {plan['rows'][source]}':x={source*512+14}:y=483:fontsize=19:fontcolor=white"]
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    codec = ['-an', '-c:v', 'libx264', '-crf', '20', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(args.input / 'policy.mp4'), '-vf', ','.join(filters), *codec, str(args.output)], check=True)
    result = dict(video=str(args.output), role=args.role, model_sha256=model_hash,
                  teacher_sha256=report['checkpoint_sha256'], initial_states_sha256=report['initial_states_sha256'],
                  rows=plan['rows'], trace_sha256=sha(args.input / 'trace.npz'), raw_video=raw,
                  video_verification=verify_video(args.output), records=score['records'],
                  independent_rescore=True, scope='Rendered development examples; same states repeated, never added to statistical denominators')
    result['conditions'] = {key: report[key] for key in [
        'task', 'hand', 'object', 'protocol', 'effective_randomize',
        'effective_joint_noise', 'effective_force_scale', 'source_sha256', 'scorer_sha256']}
    identity_path = args.input.parent / 'jobs' / args.input.name / 'identity.json'
    identity = json.loads(identity_path.read_text())
    assert identity['local'], 'This packaging plan requires the registered local render condition'
    result['render_job'] = dict(name=identity['name'], local=True,
                               start_utc=identity['start_utc'], source_sha256=identity['pinned_source_sha256'])
    if args.paired_teacher:
        assert is_student
        teacher = json.loads(args.paired_teacher.with_suffix('.json').read_text())
        assert teacher['role'] == 'teacher' and teacher['rows'] == result['rows']
        assert teacher['teacher_sha256'] == result['teacher_sha256']
        assert teacher['initial_states_sha256'] == result['initial_states_sha256']
        assert teacher['conditions'] == result['conditions']
        assert teacher['video_verification']['sha256'] == sha(args.paired_teacher)
        paired = args.output.with_name('teacher-student-fixed-comparison.mp4')
        assert not paired.exists()
        subprocess.run([ffmpeg, '-v', 'error', '-i', str(args.paired_teacher), '-i', str(args.output),
                        '-filter_complex', '[0:v][1:v]vstack=inputs=2[out]', '-map', '[out]', *codec, str(paired)], check=True)
        result['paired_video'] = dict(path=str(paired), teacher_video=str(args.paired_teacher), **verify_video(paired))
    args.output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))


if __name__ == '__main__':
    main()
