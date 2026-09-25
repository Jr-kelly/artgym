"""Schedule real dataset work independently of training/evaluation readiness."""

TRAINING_ARMS=('sharpa_paper_reference','sharpa_reward_corrected','sharpa_reward_upstream')


def training_ready(rows):
    return len(rows)>=30 and all(row.get('status')=='completed' and row.get('counts',{}).get('train',0)>0 for row in rows[:30])


def pending_data(sharpa,wuji):
    pending=[]
    for dataset,robot,rows in [('knife_sharpa_official','sharpa',sharpa),('knife_wuji_official','wuji_artbot',wuji)]:
        # A complete pilot proves each robot adapter before expanding it.
        warm=any(row.get('status')=='completed' for row in rows)
        for i,row in enumerate(rows):
            if not row and (warm or i==0):pending.append((dataset,robot,f'{i:03d}'))
    return pending


def choose_data_gpus(config,busy,free_memory_mb,training_states):
    result=[]
    for gpu in config.get('data_gpu_order',[4,5,0,2,6,1,3,7]):
        if gpu in busy:continue
        if free_memory_mb.get(gpu,0)<config.get('data_min_free_memory_mb',60000):continue
        if gpu in (4,5):
            name='wuji_single_upstream' if gpu==4 else 'wuji_single_corrected'
            if training_states.get(name,{}).get('status') not in ('completed','failed'):continue
        else:
            # Wait until full-size training has allocated its steady-state buffers.
            if not all(training_states.get(name,{}).get('status') in ('teacher','completed','failed') for name in TRAINING_ARMS):continue
            if not config.get('share_training_gpus',True):continue
        result.append(gpu)
    return result
