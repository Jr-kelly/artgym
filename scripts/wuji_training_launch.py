"""Build a one-node Wuji SAPG launch with an explicit global sample budget."""
import math

DEFAULT_TOTAL_STEPS=2_048_000_000
HORIZON=16
REFERENCE_BATCH=2560*HORIZON


def training_plan(gpus=1,envs_per_gpu=2560,total_steps=None,epochs=None):
    if gpus not in (1,2,4):
        raise ValueError('Supported GPU counts are 1, 2 and 4 on one node')
    if envs_per_gpu<=0 or envs_per_gpu%5:
        raise ValueError('envs-per-gpu must be positive and divisible by five SAPG groups')
    if total_steps is not None and epochs is not None:
        raise ValueError('Choose --total-steps or --epochs, not both')
    global_batch=gpus*envs_per_gpu*HORIZON
    if epochs is not None:
        if epochs<=0:raise ValueError('epochs must be positive')
        total_steps=epochs*global_batch
    if total_steps is None:total_steps=DEFAULT_TOTAL_STEPS
    if total_steps<=0:raise ValueError('total-steps must be positive')
    epochs=math.ceil(total_steps/global_batch)
    return dict(gpus=gpus,envs_per_gpu=envs_per_gpu,total_envs=gpus*envs_per_gpu,
                sapg_groups_per_gpu=5,expl_coef_block_size=envs_per_gpu//5,
                horizon_length=HORIZON,minibatch_size=envs_per_gpu*HORIZON//5,
                global_steps_per_epoch=global_batch,total_steps=total_steps,max_epochs=epochs,
                actual_max_steps=epochs*global_batch,
                curriculum_warmup_epochs=math.ceil(200*REFERENCE_BATCH/global_batch),
                curriculum_total_epochs=math.ceil(2000*REFERENCE_BATCH/global_batch))


def teacher_command(python,dataset,run_name,plan,checkpoint=None,weights_only=False):
    if weights_only and checkpoint is None:
        raise ValueError('--weights-only requires --checkpoint')
    command=[str(python),'-m']
    if plan['gpus']>1:
        command+=['torch.distributed.run','--standalone','--nnodes=1',f"--nproc_per_node={plan['gpus']}",'-m']
    command+=['isaacgymenvs.train','hand=wuji_paper',f'object={dataset}','train=wujiKnifeSAPG',
              f"num_envs={plan['envs_per_gpu']}",'headless=True','pipeline=gpu',
              f'multi_gpu={plan["gpus"]>1}',f'experiment={run_name}','seed=20260920',
              f"max_iterations={plan['max_epochs']}",
              f"+train.params.config.max_frames={plan['total_steps']}",
              f"train.params.config.expl_coef_block_size={plan['expl_coef_block_size']}",
              f"train.params.config.minibatch_size={plan['minibatch_size']}",
              f"task.env.rewardWeightCurriculumSchedule.warmupSteps={plan['curriculum_warmup_epochs']}",
              f"task.env.rewardWeightCurriculumSchedule.totalSteps={plan['curriculum_total_epochs']}"]
    if checkpoint is not None:
        command+=[f'checkpoint={checkpoint}',f'+train.params.config.checkpoint_weights_only={weights_only}']
    return command
