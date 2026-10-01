# Frozen unified-student evaluation

Primary **SA-real-51200** does not pass the preregistered full gate. Worst S strict cell: **source 3 S2, 93/128 (72.7%)**. This is a simulation result under calibrated initial geometry/pose; no hardware validation is claimed.

All models were fixed before opening the new final cohort. Each source has 128 episodes per protocol; protocols share initial states. No teacher failures are removed. Intervals are Wilson 95% intervals, while gates use observed proportions. Stage holds and repeated checkpoints do not enlarge the denominator.

| Model | Protocol | Source | Strict / cycle success (95% CI) | Full-horizon body stability (95% CI) |
|---|---|---:|---|---|
| teacher | S2 | 0 | 128/128 (97.1–100.0%) | 128/128 (97.1–100.0%) |
| teacher | S2 | 1 | 127/128 (95.7–99.9%) | 127/128 (95.7–99.9%) |
| teacher | S2 | 2 | 126/128 (94.5–99.6%) | 128/128 (97.1–100.0%) |
| teacher | S2 | 3 | 105/128 (74.5–87.7%) | 125/128 (93.3–99.2%) |
| teacher | S5 | 0 | 125/128 (93.3–99.2%) | 125/128 (93.3–99.2%) |
| teacher | S5 | 1 | 128/128 (97.1–100.0%) | 128/128 (97.1–100.0%) |
| teacher | S5 | 2 | 127/128 (95.7–99.9%) | 127/128 (95.7–99.9%) |
| teacher | S5 | 3 | 112/128 (80.7–92.2%) | 127/128 (95.7–99.9%) |
| teacher | F | 0 | 128/128 (97.1–100.0%) | 128/128 (97.1–100.0%) |
| teacher | F | 1 | 128/128 (97.1–100.0%) | 108/128 (77.1–89.7%) |
| teacher | F | 2 | 128/128 (97.1–100.0%) | 109/128 (78.0–90.3%) |
| teacher | F | 3 | 127/128 (95.7–99.9%) | 125/128 (93.3–99.2%) |
| SA-real-51200 | S2 | 0 | 126/128 (94.5–99.6%) | 127/128 (95.7–99.9%) |
| SA-real-51200 | S2 | 1 | 120/128 (88.2–96.8%) | 127/128 (95.7–99.9%) |
| SA-real-51200 | S2 | 2 | 117/128 (85.3–95.1%) | 128/128 (97.1–100.0%) |
| SA-real-51200 | S2 | 3 | 93/128 (64.4–79.6%) | 121/128 (89.1–97.3%) |
| SA-real-51200 | S5 | 0 | 126/128 (94.5–99.6%) | 126/128 (94.5–99.6%) |
| SA-real-51200 | S5 | 1 | 121/128 (89.1–97.3%) | 127/128 (95.7–99.9%) |
| SA-real-51200 | S5 | 2 | 122/128 (90.2–97.8%) | 128/128 (97.1–100.0%) |
| SA-real-51200 | S5 | 3 | 97/128 (67.7–82.4%) | 124/128 (92.2–98.8%) |
| SA-real-51200 | F | 0 | 128/128 (97.1–100.0%) | 124/128 (92.2–98.8%) |
| SA-real-51200 | F | 1 | 128/128 (97.1–100.0%) | 106/128 (75.3–88.4%) |
| SA-real-51200 | F | 2 | 128/128 (97.1–100.0%) | 128/128 (97.1–100.0%) |
| SA-real-51200 | F | 3 | 126/128 (94.5–99.6%) | 110/128 (78.9–90.9%) |
| SA-real-70400 | S2 | 0 | 114/128 (82.5–93.4%) | 127/128 (95.7–99.9%) |
| SA-real-70400 | S2 | 1 | 108/128 (77.1–89.7%) | 125/128 (93.3–99.2%) |
| SA-real-70400 | S2 | 2 | 113/128 (81.6–92.8%) | 128/128 (97.1–100.0%) |
| SA-real-70400 | S2 | 3 | 94/128 (65.2–80.3%) | 120/128 (88.2–96.8%) |
| SA-real-70400 | S5 | 0 | 106/128 (75.3–88.4%) | 127/128 (95.7–99.9%) |
| SA-real-70400 | S5 | 1 | 97/128 (67.7–82.4%) | 128/128 (97.1–100.0%) |
| SA-real-70400 | S5 | 2 | 83/128 (56.2–72.6%) | 128/128 (97.1–100.0%) |
| SA-real-70400 | S5 | 3 | 84/128 (57.0–73.3%) | 122/128 (90.2–97.8%) |
| SA-real-70400 | F | 0 | 128/128 (97.1–100.0%) | 125/128 (93.3–99.2%) |
| SA-real-70400 | F | 1 | 128/128 (97.1–100.0%) | 93/128 (64.4–79.6%) |
| SA-real-70400 | F | 2 | 128/128 (97.1–100.0%) | 128/128 (97.1–100.0%) |
| SA-real-70400 | F | 3 | 126/128 (94.5–99.6%) | 117/128 (85.3–95.1%) |
| SC-real-51200 | S2 | 0 | 120/128 (88.2–96.8%) | 128/128 (97.1–100.0%) |
| SC-real-51200 | S2 | 1 | 119/128 (87.2–96.3%) | 127/128 (95.7–99.9%) |
| SC-real-51200 | S2 | 2 | 115/128 (83.4–94.0%) | 128/128 (97.1–100.0%) |
| SC-real-51200 | S2 | 3 | 77/128 (51.5–68.2%) | 124/128 (92.2–98.8%) |
| SC-real-51200 | S5 | 0 | 115/128 (83.4–94.0%) | 124/128 (92.2–98.8%) |
| SC-real-51200 | S5 | 1 | 123/128 (91.2–98.3%) | 128/128 (97.1–100.0%) |
| SC-real-51200 | S5 | 2 | 117/128 (85.3–95.1%) | 128/128 (97.1–100.0%) |
| SC-real-51200 | S5 | 3 | 62/128 (40.0–57.0%) | 124/128 (92.2–98.8%) |
| SC-real-51200 | F | 0 | 128/128 (97.1–100.0%) | 127/128 (95.7–99.9%) |
| SC-real-51200 | F | 1 | 128/128 (97.1–100.0%) | 113/128 (81.6–92.8%) |
| SC-real-51200 | F | 2 | 128/128 (97.1–100.0%) | 113/128 (81.6–92.8%) |
| SC-real-51200 | F | 3 | 126/128 (94.5–99.6%) | 118/128 (86.2–95.7%) |
| C1-3200 | S2 | 0 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | S2 | 1 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | S2 | 2 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | S2 | 3 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | S5 | 0 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | S5 | 1 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | S5 | 2 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | S5 | 3 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | F | 0 | 0/128 (0.0–2.9%) | 0/128 (0.0–2.9%) |
| C1-3200 | F | 1 | 4/128 (1.2–7.8%) | 0/128 (0.0–2.9%) |
| C1-3200 | F | 2 | 1/128 (0.1–4.3%) | 0/128 (0.0–2.9%) |
| C1-3200 | F | 3 | 19/128 (9.7–22.0%) | 0/128 (0.0–2.9%) |

S2/S5 are 20 seconds, with external commands every 2/5 seconds, error <2 mm for the final nine samples of every stage, and full validity/body stability. Body thresholds are <10 mm drift and <0.25 rad rotation. F is 40 seconds: at least one complete extension–retraction cycle is functional success; full-horizon stability is reported separately. The F scheduler uses true slider arrival to issue external commands, so it is not a sensor-free arrival detector.

Teacher cells below an absolute threshold: none. These episodes remain in every paired comparison; student absolute requirements are unchanged.

## Primary full-gate checks

| Protocol | Source | Full cell passes | Teacher minus student success (pp) | Teacher minus student body stability (pp) |
|---|---:|---|---:|---:|
| S2 | 0 | True | 1.56 | 0.78 |
| S2 | 1 | True | 5.47 | 0.00 |
| S2 | 2 | True | 7.03 | 0.00 |
| S2 | 3 | False | 9.38 | 3.12 |
| S5 | 0 | True | -0.78 | -0.78 |
| S5 | 1 | True | 5.47 | 0.78 |
| S5 | 2 | True | 3.91 | -0.78 |
| S5 | 3 | False | 11.72 | 2.34 |
| F | 0 | True | 0.00 | 3.12 |
| F | 1 | True | 0.00 | 1.56 |
| F | 2 | True | 0.00 | -14.84 |
| F | 3 | True | 0.78 | 11.72 |

S requires success ≥80%, body stability ≥95%, and paired losses ≤10/3 percentage points. F requires cycle success ≥80%; its body difference is descriptive. A negative difference favors the student.

## Paired teacher/student transitions

| Student | Protocol | Source | Both pass | Teacher only | Student only | Both fail |
|---|---|---:|---:|---:|---:|---:|
| C1-3200 | S2 | 0 | 0 | 128 | 0 | 0 |
| C1-3200 | S2 | 1 | 0 | 127 | 0 | 1 |
| C1-3200 | S2 | 2 | 0 | 126 | 0 | 2 |
| C1-3200 | S2 | 3 | 0 | 105 | 0 | 23 |
| C1-3200 | S5 | 0 | 0 | 125 | 0 | 3 |
| C1-3200 | S5 | 1 | 0 | 128 | 0 | 0 |
| C1-3200 | S5 | 2 | 0 | 127 | 0 | 1 |
| C1-3200 | S5 | 3 | 0 | 112 | 0 | 16 |
| C1-3200 | F | 0 | 0 | 128 | 0 | 0 |
| C1-3200 | F | 1 | 4 | 124 | 0 | 0 |
| C1-3200 | F | 2 | 1 | 127 | 0 | 0 |
| C1-3200 | F | 3 | 18 | 109 | 1 | 0 |
| SA-real-51200 | S2 | 0 | 126 | 2 | 0 | 0 |
| SA-real-51200 | S2 | 1 | 119 | 8 | 1 | 0 |
| SA-real-51200 | S2 | 2 | 116 | 10 | 1 | 1 |
| SA-real-51200 | S2 | 3 | 79 | 26 | 14 | 9 |
| SA-real-51200 | S5 | 0 | 124 | 1 | 2 | 1 |
| SA-real-51200 | S5 | 1 | 121 | 7 | 0 | 0 |
| SA-real-51200 | S5 | 2 | 121 | 6 | 1 | 0 |
| SA-real-51200 | S5 | 3 | 88 | 24 | 9 | 7 |
| SA-real-51200 | F | 0 | 128 | 0 | 0 | 0 |
| SA-real-51200 | F | 1 | 128 | 0 | 0 | 0 |
| SA-real-51200 | F | 2 | 128 | 0 | 0 | 0 |
| SA-real-51200 | F | 3 | 126 | 1 | 0 | 1 |
| SA-real-70400 | S2 | 0 | 114 | 14 | 0 | 0 |
| SA-real-70400 | S2 | 1 | 108 | 19 | 0 | 1 |
| SA-real-70400 | S2 | 2 | 111 | 15 | 2 | 0 |
| SA-real-70400 | S2 | 3 | 80 | 25 | 14 | 9 |
| SA-real-70400 | S5 | 0 | 103 | 22 | 3 | 0 |
| SA-real-70400 | S5 | 1 | 97 | 31 | 0 | 0 |
| SA-real-70400 | S5 | 2 | 82 | 45 | 1 | 0 |
| SA-real-70400 | S5 | 3 | 84 | 28 | 0 | 16 |
| SA-real-70400 | F | 0 | 128 | 0 | 0 | 0 |
| SA-real-70400 | F | 1 | 128 | 0 | 0 | 0 |
| SA-real-70400 | F | 2 | 128 | 0 | 0 | 0 |
| SA-real-70400 | F | 3 | 125 | 2 | 1 | 0 |
| SC-real-51200 | S2 | 0 | 120 | 8 | 0 | 0 |
| SC-real-51200 | S2 | 1 | 118 | 9 | 1 | 0 |
| SC-real-51200 | S2 | 2 | 114 | 12 | 1 | 1 |
| SC-real-51200 | S2 | 3 | 64 | 41 | 13 | 10 |
| SC-real-51200 | S5 | 0 | 114 | 11 | 1 | 2 |
| SC-real-51200 | S5 | 1 | 123 | 5 | 0 | 0 |
| SC-real-51200 | S5 | 2 | 116 | 11 | 1 | 0 |
| SC-real-51200 | S5 | 3 | 54 | 58 | 8 | 8 |
| SC-real-51200 | F | 0 | 128 | 0 | 0 | 0 |
| SC-real-51200 | F | 1 | 128 | 0 | 0 | 0 |
| SC-real-51200 | F | 2 | 128 | 0 | 0 | 0 |
| SC-real-51200 | F | 3 | 126 | 1 | 0 | 1 |

The underlying JSON also includes paired body-stability transitions and the three base-configuration clusters (nearby sources 0/1 pooled, source 2, source 3). These clusters are descriptive summaries, not new grasp or object types.

## Primary failure decomposition

| Protocol | Source | Strict successes | Stable body but missed endpoint | Body failure | Opening / closing misses among stable episodes |
|---|---:|---:|---:|---:|---|
| S2 | 0 | 126 | 1 | 1 | 1 / 0 |
| S2 | 1 | 120 | 7 | 1 | 7 / 0 |
| S2 | 2 | 117 | 11 | 0 | 11 / 0 |
| S2 | 3 | 93 | 28 | 7 | 28 / 1 |
| S5 | 0 | 126 | 0 | 2 | 0 / 0 |
| S5 | 1 | 121 | 6 | 1 | 6 / 0 |
| S5 | 2 | 122 | 6 | 0 | 6 / 0 |
| S5 | 3 | 97 | 27 | 4 | 27 / 0 |

Opening and closing misses can overlap. This partition describes failure location, not causality. The final cohort is closed after this assessment and must not be used for further tuning.

| Protocol | Source | Holds by stage, each /128 | Median first missed stage, stable failures | Median body breach time, body failures |
|---|---:|---|---:|---:|
| S2 | 0 | 128,128,128,128,128,128,128,128,127,128 | 9 | 12.833333333333334 |
| S2 | 1 | 123,128,128,128,126,128,126,128,123,128 | 1 | 18.133333333333333 |
| S2 | 2 | 123,128,127,128,126,128,127,128,123,128 | 3 | None |
| S2 | 3 | 123,124,112,122,108,123,103,122,98,121 | 5.0 | 5.366666666666666 |
| S5 | 0 | 128,128,128,126 | None | 18.316666666666666 |
| S5 | 1 | 122,128,128,128 | 1.0 | 5.133333333333334 |
| S5 | 2 | 123,128,126,128 | 1.0 | None |
| S5 | 3 | 106,125,105,124 | 1 | 3.1500000000000004 |

Stages are numbered from one, alternating opening and closing. These are repeated measurements within the same 128 episodes. Missing medians mean no corresponding failures.

## Frozen artifacts

Code SHA256: `6176b3d2219808b44be464fbffe0249d4a1445e28ef682456c280772cd79f8b5`.

Cohort SHA256: `a47be7464659f75e69ef6f7165a7b057a0fd433ed180af76723f9bb5e1576a82`.

| Role | Model | Checkpoint SHA256 |
|---|---|---|
| teacher | teacher | `2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8` |
| primary | SA-real-51200 | `16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9` |
| fixed_endpoint | SA-real-70400 | `c0b2321ece88442920b86302e8a7ef8c488892ce6c876de56f52f2f310981f87` |
| matched_latent_only_control | SC-real-51200 | `0a458863983e0cfb337c61aff94d025e0f9e0bd27c6f8f64c2d1c232a74105c8` |
| initial_only_reference | C1-3200 | `53612c29e084b83062ca2f19c514c6b27f1cc195de4ebb001db0523f44e42dc7` |
