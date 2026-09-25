import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch
from rl_games.algos_torch import torch_ext
from rl_games.common.checkpoint_schedule import checkpoint_events, publish_checkpoint


class CheckpointTests(unittest.TestCase):
    def test_cadence_and_final(self):
        cfg = dict(save_frequency=50, evaluation_frequency=100)
        self.assertEqual(checkpoint_events(cfg, 10), (True, True, False))
        self.assertEqual(checkpoint_events(cfg, 50), (True, False, False))
        self.assertEqual(checkpoint_events(cfg, 100), (True, True, False))
        self.assertEqual(checkpoint_events(cfg, 500), (True, True, True))
        self.assertEqual(checkpoint_events(cfg, 51), (False, False, False))
        self.assertEqual(checkpoint_events(cfg, 51, True), (True, True, False))

    def test_failure_keeps_previous_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'latest.pth'
            torch_ext.safe_save({'epoch': 1}, path)
            def failed_write(state, stream):
                stream.write(b'incomplete')
                raise OSError('injected write failure')
            with patch.object(torch, 'save', side_effect=failed_write), patch.object(torch_ext.time, 'sleep'):
                with self.assertRaises(RuntimeError):
                    torch_ext.safe_save({'epoch': 2}, path)
            self.assertEqual(torch.load(path)['epoch'], 1)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_retention_and_policy_publication(self):
        cfg = dict(save_frequency=1, evaluation_frequency=2, checkpoint_milestone_frequency=3,
                   checkpoint_first_epoch=1, checkpoint_keep_recent=2)
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            for epoch in range(1, 8):
                state = {rank: dict(epoch=epoch, frame=epoch*640, model={'weight': torch.tensor([epoch])},
                                    optimizer={'rank': rank}) for rank in range(4)}
                publish_checkpoint(run, state, cfg, final=epoch == 7)
            self.assertEqual([p.name for p in sorted((run/'checkpoints').glob('epoch_*.pth'))],
                             ['epoch_000003.pth', 'epoch_000006.pth', 'epoch_000007.pth'])
            latest = torch.load(run/'checkpoints/latest.pth')
            self.assertEqual(len(latest), 4)
            self.assertEqual(latest[3]['epoch'], 7)
            for marker in (run/'evaluation/inbox').glob('*.json'):
                record = json.loads(marker.read_text())
                policy = torch.load(record['policy_checkpoint'])
                self.assertEqual(policy[0]['epoch'], record['epoch'])
                self.assertNotIn('optimizer', policy[0])


if __name__ == '__main__':
    unittest.main()
