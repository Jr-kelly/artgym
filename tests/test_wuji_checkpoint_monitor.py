import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from scripts.monitor_wuji_checkpoints import (Monitor, atomic_json, native_busy,
                                              policy_snapshot, source_candidates)


class CheckpointMonitorTests(unittest.TestCase):
    def test_gpu_pool_drains_old_worker_and_avoids_starvation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);specs=[]
            for name in ['slow','fast','draining']:
                specs.append(dict(name=name,run=str(root/name),profile='reference',gpu=4))
            cfg=dict(project=str(root),python='python',state_dir=str(root/'monitor'),
                     runs=specs,evaluation_gpus=[4,5],evaluation_queue_order='oldest_first')
            monitor=Monitor(cfg,root/'config.json')
            for name,epoch,discovered,status,gpu in [('slow',10,1, 'queued',7),
                       ('fast',200,2,'queued',7),('fast',250,3,'queued',7),
                       ('draining',150,0,'running',7)]:
                monitor.save_job(dict(name=name,run=str(root/name),epoch=epoch,status=status,
                    discovered_time=discovered,gpu=7,worker_pid=111,
                    result_path=str(root/name/f'{epoch}/result.json')))
            with patch('scripts.monitor_wuji_checkpoints.subprocess.Popen') as launch, \
                 patch('scripts.monitor_wuji_checkpoints.pid_alive',return_value=True):
                launch.return_value.pid=12345;launch.return_value.poll.return_value=None
                monitor.tick()
                self.assertEqual(launch.call_count,2)
                jobs=[json.loads(p.read_text()) for p in monitor.jobs_dir.glob('*.json')]
                running={j['name']+str(j['epoch']):j['gpu'] for j in jobs if j['status']=='running'}
                self.assertEqual(running,{'slow10':4,'fast200':5,'draining150':7})
                monitor.tick();self.assertEqual(launch.call_count,2)

    def test_checkpoints_queue_until_heldout_data_are_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run=root/'run';(run/'nn').mkdir(parents=True)
            torch.save({0:dict(epoch=10,frame=3200000,model={})},run/'nn/epoch_10.pth')
            gate=root/'test-ready.json'
            spec=dict(name='run',run=str(run),profile='reference',gpu=7,required_files=[str(gate)])
            cfg=dict(project=str(root),python='python',state_dir=str(root/'monitor'),runs=[spec])
            monitor=Monitor(cfg,root/'config.json');monitor.discover(spec)
            with patch('scripts.monitor_wuji_checkpoints.subprocess.Popen') as launch:
                monitor.tick();launch.assert_not_called()
                job=json.loads(next(monitor.jobs_dir.glob('*.json')).read_text())
                self.assertEqual(job['status'],'queued')
                gate.write_text('{}');launch.return_value.pid=12345
                monitor.tick();launch.assert_called_once()
                job=json.loads(next(monitor.jobs_dir.glob('*.json')).read_text())
                self.assertEqual(job['status'],'running')

    def test_snapshot_is_immutable_and_rejects_wrong_epoch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'last.pth'
            torch.save({0: dict(epoch=25, frame=256000, model={'weight':torch.tensor([3.0])},
                                optimizer={'unused':True})}, source)
            snapshot = policy_snapshot(source, root/'policies', 25)
            saved = torch.load(snapshot['policy_checkpoint'])
            self.assertNotIn('optimizer', saved[0])
            torch.save({0: dict(epoch=50, model={'weight':torch.tensor([9.0])})}, source)
            self.assertEqual(torch.load(snapshot['policy_checkpoint'])[0]['model']['weight'].item(),3.0)
            with self.assertRaises(ValueError):
                policy_snapshot(source, root/'policies',25)

    def test_native_reuse_keeps_and_recovers_independent_audit_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run=root/'run'
            full=run/'checkpoints/epoch_000050.pth';full.parent.mkdir(parents=True);full.write_bytes(b'full')
            policy=run/'evaluation/inbox/epoch_000050.pth';policy.parent.mkdir(parents=True)
            torch.save({0:dict(epoch=50,frame=5,model={'weight':torch.tensor([3.0])})},policy)
            atomic_json(full.with_suffix('.json'),dict(epoch=50,frame=5,checkpoint=str(full)))
            atomic_json(policy.with_suffix('.json'),dict(epoch=50,frame=5,policy_checkpoint=str(policy)))
            self.assertEqual(source_candidates(run)[0][0],policy)
            atomic_json(run/'evaluation/epoch_000050/result.json',
                        dict(epoch=50,status='completed',execution_success_rate=0,total_trials=5))
            cfg=dict(project=str(root),python='python',state_dir=str(root/'monitor'),
                     runs=[dict(name='run',run=str(run),profile='demo_aligned',gpu=0)])
            monitor=Monitor(cfg,root/'config.json')
            monitor.discover(cfg['runs'][0])
            snapshot=run/'evaluation/monitor/policies/epoch_000050.pth'
            self.assertEqual(torch.load(snapshot)[0]['model']['weight'].item(),3.0)
            original=snapshot.read_bytes()
            with patch('scripts.monitor_wuji_checkpoints.policy_snapshot') as capture:
                monitor.discover(cfg['runs'][0])
                capture.assert_not_called()
            # Simulate a native job recorded by an older monitor with no audit
            # snapshot: the existing job must not hide the missing artifact.
            snapshot.unlink()
            monitor.discover(cfg['runs'][0])
            self.assertEqual(snapshot.read_bytes(),original)
            jobs=list(monitor.jobs_dir.glob('*.json'))
            self.assertEqual(len(jobs),1)
            self.assertTrue(json.loads(jobs[0].read_text())['reused_native'])

    def test_all_new_epochs_queue_and_duplicate_legacy_files_do_not(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run=root/'run';(run/'nn').mkdir(parents=True);(run/'last').mkdir()
            for relative,epoch in [('nn/epoch_100.pth',100),('nn/epoch_200.pth',200),('last/model.pth',200)]:
                torch.save({0:dict(epoch=epoch,frame=epoch*16,model={})},run/relative)
            cfg=dict(project=str(root),python='python',state_dir=str(root/'monitor'),
                     runs=[dict(name='run',run=str(run),profile='paper',gpu=0)])
            monitor=Monitor(cfg,root/'config.json');monitor.discover(cfg['runs'][0])
            self.assertEqual(len(list(monitor.jobs_dir.glob('*.json'))),2)
            torch.save({0:dict(epoch=300,frame=4800,model={})},run/'last/model.pth')
            monitor.discover(cfg['runs'][0])
            self.assertEqual(len(list(monitor.jobs_dir.glob('*.json'))),3)
            self.assertTrue(all(json.loads(p.read_text())['status']=='queued' for p in monitor.jobs_dir.glob('*.json')))

    def test_active_native_deferred_and_skipped_native_can_be_evaluated(self):
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder)
            atomic_json(run/'pipeline-status.json',dict(status='teacher',evaluation_watcher_pid=123))
            atomic_json(run/'evaluation/status.json',dict(status='running',epoch=50))
            with patch('scripts.monitor_wuji_checkpoints.pid_alive',return_value=True):
                self.assertTrue(native_busy(run,50,0))
                atomic_json(run/'evaluation/epoch_000050/result.json',dict(status='skipped'))
                self.assertFalse(native_busy(run,50,0))


if __name__ == '__main__':
    unittest.main()
