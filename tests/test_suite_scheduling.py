import unittest
from scripts.suite_scheduling import training_ready,pending_data,choose_data_gpus,TRAINING_ARMS
from scripts.monitor_gpu_utilization import rolling_summary


class SuiteSchedulingTests(unittest.TestCase):
    def test_training_does_not_wait_for_missing_heldout_object(self):
        rows=[dict(status='completed',counts={'train':2}) for _ in range(30)]+[{}]*5
        self.assertTrue(training_ready(rows))
        rows[3]={};self.assertFalse(training_ready(rows))

    def test_remaining_sharpa_does_not_block_wuji(self):
        done=dict(status='completed')
        jobs=pending_data([done]*30+[{}]+[done]*4,[done]+[{}]*34)
        self.assertEqual(jobs[0],('knife_sharpa_official','sharpa','030'))
        self.assertEqual(len(jobs),35)
        self.assertEqual(jobs[1],('knife_wuji_official','wuji_artbot','001'))

    def test_sharing_waits_for_training_and_memory(self):
        states={name:{'status':'teacher'} for name in TRAINING_ARMS}
        states.update(wuji_single_upstream={'status':'completed'},wuji_single_corrected={'status':'completed'})
        free={i:65000 for i in range(8)};free[2]=55000
        self.assertEqual(choose_data_gpus({}, {4},free,states),[5,0,6,1,3,7])
        states[TRAINING_ARMS[0]]={'status':'preflight'}
        self.assertEqual(choose_data_gpus({},set(),free,states),[4,5])

    def test_window_uses_whole_resource(self):
        samples=[dict(time=10,gpus=[{'utilization':0},{'utilization':100}]),dict(time=20,gpus=[{'utilization':20},{'utilization':60}])]
        self.assertEqual(rolling_summary(samples,20,15)['mean_percent'],45)
        self.assertEqual(rolling_summary(samples,20,5)['mean_percent'],40)


if __name__=='__main__':unittest.main()
