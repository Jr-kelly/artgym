import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.wuji_training_launch import training_plan,teacher_command


class LaunchTests(unittest.TestCase):
    def test_four_gpu_preserves_global_budget(self):
        one=training_plan();four=training_plan(gpus=4)
        self.assertEqual(one['total_steps'],four['total_steps'])
        self.assertEqual(four['max_epochs'],12500)
        self.assertEqual(four['total_envs'],10240)
        self.assertEqual(four['global_steps_per_epoch'],163840)
        self.assertEqual(four['actual_max_steps'],2048000000)
        self.assertEqual(four['curriculum_total_epochs'],500)
        self.assertEqual(four['envs_per_gpu']//four['expl_coef_block_size'],5)

    def test_explicit_budget_and_validation(self):
        self.assertEqual(training_plan(gpus=4,epochs=100)['total_steps'],16384000)
        plan=training_plan(gpus=4,total_steps=200000)
        self.assertGreaterEqual(plan['actual_max_steps'],200000)
        self.assertLess(plan['actual_max_steps']-200000,plan['global_steps_per_epoch'])
        for kwargs in [dict(gpus=0),dict(envs_per_gpu=2561),dict(total_steps=-1),dict(epochs=1,total_steps=2)]:
            with self.assertRaises(ValueError):training_plan(**kwargs)

    def test_torchrun_and_checkpoint_modes(self):
        cmd=teacher_command('python','knife_wuji_fingertip','new_run',training_plan(gpus=4),Path('/tmp/model.pth'),True)
        self.assertIn('torch.distributed.run',cmd)
        self.assertIn('--nproc_per_node=4',cmd)
        self.assertIn('multi_gpu=True',cmd)
        self.assertIn('+train.params.config.checkpoint_weights_only=True',cmd)
        self.assertIn('+train.params.config.max_frames=2048000000',cmd)
        with self.assertRaises(ValueError):
            teacher_command('python','knife_wuji_fingertip','run',training_plan(),weights_only=True)

    def test_cuda_rank_and_rendezvous(self):
        from rl_games.common.distributed_utils import init_distributed
        config={'device':'cuda:0'}
        with patch.dict('os.environ',{'LOCAL_RANK':'2','RANK':'2','WORLD_SIZE':'4'}), \
             patch('torch.cuda.device_count',return_value=4), \
             patch('torch.cuda.set_device') as select, \
             patch('torch.distributed.is_initialized',return_value=False), \
             patch('torch.distributed.init_process_group') as init, \
             patch('torch.distributed.new_group',return_value='checkpoint'):
            self.assertEqual(init_distributed(config),(2,2,4,'checkpoint'))
            self.assertEqual(config['device'],'cuda:2')
            select.assert_called_once_with(2)
            self.assertEqual(init.call_args.args[0],'nccl')
            self.assertEqual(init.call_args.kwargs['init_method'],'env://')

    def test_cross_world_checkpoint_requires_explicit_warm_start(self):
        from rl_games.common.distributed_utils import select_checkpoint_state
        single={0:{'model':{},'frame':640}}
        for rank in range(4):
            with self.assertRaisesRegex(ValueError,'weights_only'):
                select_checkpoint_state(single,rank,4)
            self.assertIs(select_checkpoint_state(single,rank,4,True),single[0])
        four={i:{'model':{},'frame':2560} for i in range(4)}
        self.assertIs(select_checkpoint_state(four,3,4),four[3])


if __name__=='__main__':unittest.main()
