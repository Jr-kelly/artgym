# Followup frozen results

|Continuation seed|Original 2s / 5s|Changed 2s / 5s|Original mean|Changed mean|Difference|
|---|---|---|---:|---:|---:|
|seed2901|57/128 / 65/128|109/128 / 120/128|47.66%|89.45%|+41.80 pp|
|seed2902|27/128 / 36/128|115/128 / 123/128|24.61%|92.97%|+68.36 pp|

|Source|Historical 2s / 5s|Parent 2s / 5s|Singleton 2s / 5s|Shared 2s / 5s|Both >=50%|
|---|---|---|---|---|---|
|0|126/128 / 124/128|0/128 / 0/128|0/128 / 0/128|0/128 / 0/128|False|
|1|127/128 / 128/128|0/128 / 0/128|0/128 / 0/128|0/128 / 0/128|False|
|2|126/128 / 127/128|0/128 / 0/128|0/128 / 0/128|0/128 / 0/128|False|
|3|0/128 / 0/128|112/128 / 117/128|109/128 / 122/128|118/128 / 124/128|True|

Fixed final checkpoints only. Replication changes continuation RNG, with the same parent and test cohort. Integration source3 reuses the tested cohort; originals0/1/2 represent two nearby clusters. No unseen-base or hardware claim.
