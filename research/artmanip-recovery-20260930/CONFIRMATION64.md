# confirmation: per-source physical evaluation

Each cell is successes/64 with a 95% Wilson interval. Sources 0/1 are nearby records; 0/1, 2 and 3 form three base-configuration clusters. These episodes test the fixed simulated knife in trained grasp neighborhoods.

All policies are privileged teachers. Each named unified model uses one weight set for all sources. Historical/source3 expert rows are references; their responsible sources are 0–2/3 respectively. No student or hardware result is represented.

S2/S5: separate 20-second fixed-clock episodes, every stage’s last nine samples within 2 mm, full survival/validity and body displacement <10 mm/rotation <0.25 rad. F: separate 40-second episodes, 10 mm tolerance with 1.5-second arrival hold before switching; at least one full open-close cycle. F success alone does not imply full-episode body stability.

## Strict S success or functional F cycles

| Model | Protocol | Source 0 | Source 1 | Source 2 | Source 3 |
|---|---|---|---|---|---|
| E4100 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 62/64 [0.893, 0.991] | 46/64 [0.599, 0.814] |
| E4100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 28/64 [0.323, 0.559] |
| E4100 | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| E5700 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 46/64 [0.599, 0.814] |
| E5700 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 29/64 [0.337, 0.574] |
| E5700 | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |

## Body stable over the full declared episode

| Model | Protocol | Source 0 | Source 1 | Source 2 | Source 3 |
|---|---|---|---|---|---|
| E4100 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 62/64 [0.893, 0.991] | 64/64 [0.943, 1.000] |
| E4100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| E4100 | F | 64/64 [0.943, 1.000] | 56/64 [0.772, 0.935] | 51/64 [0.683, 0.877] | 58/64 [0.810, 0.956] |
| E5700 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] |
| E5700 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] |
| E5700 | F | 64/64 [0.943, 1.000] | 55/64 [0.754, 0.924] | 52/64 [0.700, 0.889] | 60/64 [0.850, 0.975] |

## Valid and alive over the full declared episode

| Model | Protocol | Source 0 | Source 1 | Source 2 | Source 3 |
|---|---|---|---|---|---|
| E4100 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 62/64 [0.893, 0.991] | 64/64 [0.943, 1.000] |
| E4100 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] |
| E4100 | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 51/64 [0.683, 0.877] | 58/64 [0.810, 0.956] |
| E5700 | S2 | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] |
| E5700 | S5 | 63/64 [0.917, 0.997] | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 63/64 [0.917, 0.997] |
| E5700 | F | 64/64 [0.943, 1.000] | 64/64 [0.943, 1.000] | 52/64 [0.700, 0.889] | 60/64 [0.850, 0.975] |

## Phase holding and first body breach

The four values in each cell follow source order 0/1/2/3. Phase fractions are descriptive repeated stages, not independent episode counts. Breach time is capped at observed duration when no breach occurs.

| Model | Protocol | Endpoint hold fraction / F mean cycles | Mean first body breach (s) |
|---|---|---|---|
| E4100 | S2 | 1.000, 1.000, 0.980, 0.931 | 20.00, 20.00, 19.68, 20.00 |
| E4100 | S5 | 0.988, 1.000, 1.000, 0.797 | 19.81, 20.00, 20.00, 20.00 |
| E4100 | F | 10.000, 9.047, 8.719, 9.000 | 40.00, 39.30, 38.64, 38.23 |
| E5700 | S2 | 1.000, 1.000, 1.000, 0.923 | 20.00, 20.00, 20.00, 19.76 |
| E5700 | S5 | 0.988, 1.000, 1.000, 0.789 | 19.82, 20.00, 20.00, 19.77 |
| E5700 | F | 9.984, 9.078, 8.734, 9.500 | 40.00, 38.77, 38.70, 39.11 |

## Evidence

Per-episode CSVs and cluster summaries accompany each report. Reports also retain open/close arrival, holding, overshoot/retreat, saturation, joint limits, full drift/rotation, early termination and raw trace hashes.

- `research/artmanip-recovery-20260930/bc44800-confirmation64-analysis/report.json` — SHA256 `b22bf061e99fb092076fe896146fe0278fd74cb14ea54baf737b75f7856f2821`
