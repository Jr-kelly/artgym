
多抓姿 2026-09-28T14:59:41.711893+00:00 启动请求 static-candidates-v1 GPU0 .93:30296；证据 runs/multigrasp-20260928/static-candidates-v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:00:33.221687+00:00 启动请求 scratch-small-preflight-v1 GPU1 .93:30296；证据 runs/multigrasp-20260928/scratch-small-preflight-v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:02:58.158814+00:00 启动请求 fresh-generation-v1 GPU2 .93:30296；证据 runs/multigrasp-20260928/fresh-generation-v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:03:03.023195+00:00 启动请求 mg_D_preflight_v1 GPU3 .93:30296；证据 runs/multigrasp-20260928/mg_D_preflight_v1，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

多抓姿 2026-09-28T15:04:06.476219+00:00 启动请求 mg_B_seed2801 GPU3 .93:30296；证据 runs/multigrasp-20260928/mg_B_seed2801，待核验实际PID/结果；权重 reference 4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac or scratch as command。

## 多抓姿2×2实查 2026-09-28T15:05:29.079713+00:00

A/C/B actual running, D preflight passed then queued after new test generation; 1000epochs x5120x32 each, same initial model bdf13bb...。24/24 alive20s; duplicate2 records; max drift2.36mm, max rotation.155rad; not operation success。新测试seed2026092803仅物理筛选，GPU2生成后D接续。实查任务/PID/初始模型哈希：`/data/research/artgym-experiments-20260921/multigrasp-20260928/research/multigrasp-20260928/receipts/latest-jobs.json`。总截止02:53:52 UTC，01:53:52 UTC留评估交付；不影响v2任务。下一项：verify D start and fresh candidates; finish fixed 1000epochs per arm; dev selects CP250/500/750/1000; new test remains unused。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_A_seed2801 running；远端PID 2449；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_C_seed2801 running；远端PID 2499；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 fresh-generation-v1 running；远端PID 2870；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 static-candidates-v1 completed；远端PID 1098；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 scratch-small-preflight-v1 completed；远端PID 1343；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_D_preflight_v1 completed；远端PID 2551；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。

多抓姿实查 2026-09-28T15:07:21.280934+00:00 mg_B_seed2801 running；远端PID 3149；证据 research/multigrasp-20260928/receipts/monitor-latest.json，命令/配置/权重路径及初始tensor哈希随收据。下一项收集结果/冻结评估。
