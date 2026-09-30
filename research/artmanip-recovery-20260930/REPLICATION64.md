# confirmation: per-source physical evaluation

Each cell is successes/64 with a 95% Wilson interval. Sources 0/1 are nearby records; 0/1, 2 and 3 form three base-configuration clusters. These episodes test the fixed simulated knife in trained grasp neighborhoods.

All policies are privileged teachers. Each named unified model uses one weight set for all sources. Historical/source3 expert rows are references; their responsible sources are 0–2/3 respectively. No student or hardware result is represented.

S2/S5: separate 20-second fixed-clock episodes, every stage’s last nine samples within 2 mm, full survival/validity and body displacement <10 mm/rotation <0.25 rad. F: separate 40-second episodes, 10 mm tolerance with 1.5-second arrival hold before switching; at least one full open-close cycle. F success alone does not imply full-episode body stability.

## Strict S success or functional F cycles

| Model | Protocol | Source 0 | Source 1 | Source 2 | Source 3 |
|---|---|---|---|---|---|
| Eagg6100 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 60/64 [0.850, 0.975] |
| Eagg6100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| Eagg6100 | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 63/64 [0.917, 0.997] |
| historical | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 0/64 [0.000, 0.057] |
| historical | S5 | 62/64 [0.893, 0.991] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 0/64 [0.000, 0.057] |
| historical | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 0/64 [0.000, 0.057] |
| seed2Eagg6100 | S2 | 64/64 [0.943, 1.000] | 62/64 [0.893, 0.991] | 63/64 [0.917, 0.997] | 58/64 [0.810, 0.956] |
| seed2Eagg6100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 60/64 [0.850, 0.975] |
| seed2Eagg6100 | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| source3 | S2 | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 57/64 [0.791, 0.946] |
| source3 | S5 | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 61/64 [0.871, 0.984] |
| source3 | F | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 64/64 [0.943, 1.000] |

## Body stable over the full declared episode

| Model | Protocol | Source 0 | Source 1 | Source 2 | Source 3 |
|---|---|---|---|---|---|
| Eagg6100 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| Eagg6100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| Eagg6100 | F | 64/64 [0.943, 1.000] | 57/64 [0.791, 0.946] | 53/64 [0.718, 0.901] | 63/64 [0.917, 0.997] |
| historical | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| historical | S5 | 62/64 [0.893, 0.991] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| historical | F | 64/64 [0.943, 1.000] | 59/64 [0.830, 0.966] | 48/64 [0.632, 0.840] | 64/64 [0.943, 1.000] |
| seed2Eagg6100 | S2 | 64/64 [0.943, 1.000] | 62/64 [0.893, 0.991] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| seed2Eagg6100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| seed2Eagg6100 | F | 63/64 [0.917, 0.997] | 53/64 [0.718, 0.901] | 51/64 [0.683, 0.877] | 64/64 [0.943, 1.000] |
| source3 | S2 | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 63/64 [0.917, 0.997] |
| source3 | S5 | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 63/64 [0.917, 0.997] |
| source3 | F | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 64/64 [0.943, 1.000] |

## Valid and alive over the full declared episode

| Model | Protocol | Source 0 | Source 1 | Source 2 | Source 3 |
|---|---|---|---|---|---|
| Eagg6100 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| Eagg6100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| Eagg6100 | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 53/64 [0.718, 0.901] | 63/64 [0.917, 0.997] |
| historical | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| historical | S5 | 62/64 [0.893, 0.991] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| historical | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 48/64 [0.632, 0.840] | 64/64 [0.943, 1.000] |
| seed2Eagg6100 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| seed2Eagg6100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] |
| seed2Eagg6100 | F | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 51/64 [0.683, 0.877] | 64/64 [0.943, 1.000] |
| source3 | S2 | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 2/64 [0.009, 0.107] | 63/64 [0.917, 0.997] |
| source3 | S5 | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 2/64 [0.009, 0.107] | 63/64 [0.917, 0.997] |
| source3 | F | 0/64 [0.000, 0.057] | 0/64 [0.000, 0.057] | 2/64 [0.009, 0.107] | 64/64 [0.943, 1.000] |

## Phase holding and first body breach

The four values in each cell follow source order 0/1/2/3. Phase fractions are descriptive repeated stages, not independent episode counts. Breach time is capped at observed duration when no breach occurs.

| Model | Protocol | Endpoint hold fraction / F mean cycles | Mean first body breach (s) |
|---|---|---|---|
| Eagg6100 | S2 | 1.000, 1.000, 0.984, 0.984 | 20.00, 20.00, 19.69, 20.00 |
| Eagg6100 | S5 | 0.988, 1.000, 0.984, 1.000 | 19.81, 20.00, 19.69, 20.00 |
| Eagg6100 | F | 10.000, 9.047, 8.719, 9.203 | 40.00, 38.94, 38.41, 39.41 |
| historical | S2 | 1.000, 1.000, 1.000, 0.500 | 20.00, 20.00, 20.00, 20.00 |
| historical | S5 | 0.984, 1.000, 1.000, 0.500 | 19.76, 20.00, 20.00, 20.00 |
| historical | F | 10.000, 9.016, 8.781, 0.000 | 40.00, 39.29, 38.52, 40.00 |
| seed2Eagg6100 | S2 | 1.000, 1.000, 0.986, 0.973 | 20.00, 19.89, 19.69, 20.00 |
| seed2Eagg6100 | S5 | 0.988, 1.000, 0.988, 0.984 | 19.81, 20.00, 19.69, 20.00 |
| seed2Eagg6100 | F | 9.922, 9.078, 8.625, 9.828 | 39.68, 38.04, 38.19, 40.00 |
| source3 | S2 | 0.000, 0.000, 0.008, 0.969 | 0.10, 0.41, 0.27, 19.76 |
| source3 | S5 | 0.000, 0.000, 0.008, 0.977 | 0.10, 0.41, 0.27, 19.77 |
| source3 | F | 0.000, 0.000, 0.000, 9.484 | 0.10, 0.41, 0.27, 40.00 |

## Evidence

Per-episode CSVs and cluster summaries accompany each report. Reports also retain open/close arrival, holding, overshoot/retreat, saturation, joint limits, full drift/rotation, early termination and raw trace hashes.

- `research/artmanip-recovery-20260930/aggregation1-promotion64-analysis/report.json` — SHA256 `82ed096691d54c562fe7ea346512b16d6c531bb472583fef86b059912fbc56bc`
- `research/artmanip-recovery-20260930/seed2-promotion64-analysis/report.json` — SHA256 `a22c3ebba1d633d4fc7c4c04ab1cf27b096e3099e4cc1194719de7402a21adea`
