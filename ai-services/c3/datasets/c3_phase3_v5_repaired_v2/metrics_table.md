Recomputed offline on 2026-10-21 by `datasets/repair/evaluate_repaired.py` (no LLM, nothing tuned). Numbers quoted in older documents are 'reported by documentation, not recomputed here' unless listed in the last section.

### repaired eligible test

| set / method | n | MAE | RMSE | Pearson r | within +-2 marks | within 10% of max | MAE 95% CI (answer bootstrap) |
|---|---|---|---|---|---|---|---|
| baseline overall | 90 | 1.939 | 2.616 | 0.9740 | 56/90 (62.2%) | 46/90 (51.1%) | [1.583, 2.306] |
| baseline FULL | 15 | 4.152 | 4.711 | 0.9926 | 2/15 (13.3%) | 0/15 (0.0%) | [3.061, 5.278] |
| baseline MOSTLY_CORRECT | 15 | 1.949 | 2.276 | 0.9941 | 8/15 (53.3%) | 7/15 (46.7%) | [1.376, 2.559] |
| baseline PARTIAL | 15 | 1.281 | 1.885 | 0.9547 | 12/15 (80.0%) | 13/15 (86.7%) | [0.663, 2.050] |
| baseline MISSING_CONCEPT | 15 | 1.000 | 1.336 | 0.9943 | 12/15 (80.0%) | 13/15 (86.7%) | [0.585, 1.458] |
| baseline MISCONCEPTION | 15 | 0.855 | 1.229 | 0.9905 | 13/15 (86.7%) | 13/15 (86.7%) | [0.461, 1.337] |
| baseline IRRELEVANT | 15 | 2.395 | 2.614 | n/a | 9/15 (60.0%) | 0/15 (0.0%) | [1.891, 2.969] |
| condition_e overall | 90 | 3.544 | 5.885 | 0.8010 | 52/90 (57.8%) | 30/90 (33.3%) | [2.633, 4.583] |
| condition_e FULL | 15 | 0.000 | 0.000 | 1.0000 | 15/15 (100.0%) | 15/15 (100.0%) | [0.000, 0.000] |
| condition_e MOSTLY_CORRECT | 15 | 7.700 | 10.765 | 0.2379 | 6/15 (40.0%) | 0/15 (0.0%) | [4.066, 11.733] |
| condition_e PARTIAL | 15 | 7.233 | 8.239 | 0.5960 | 0/15 (0.0%) | 0/15 (0.0%) | [5.367, 9.401] |
| condition_e MISSING_CONCEPT | 15 | 3.167 | 3.467 | 0.9961 | 8/15 (53.3%) | 0/15 (0.0%) | [2.467, 3.933] |
| condition_e MISCONCEPTION | 15 | 3.167 | 3.467 | 0.9961 | 8/15 (53.3%) | 0/15 (0.0%) | [2.467, 3.933] |
| condition_e IRRELEVANT | 15 | 0.000 | 0.000 | n/a | 15/15 (100.0%) | 15/15 (100.0%) | [0.000, 0.000] |

failed marking calls: 0 (excluded and counted, not scored)

not_evaluable answers: 0

### repaired eligible validation

| set / method | n | MAE | RMSE | Pearson r | within +-2 marks | within 10% of max | MAE 95% CI (answer bootstrap) |
|---|---|---|---|---|---|---|---|
| baseline overall | 66 | 3.099 | 6.885 | 0.9782 | 44/66 (66.7%) | 39/66 (59.1%) | [1.826, 4.802] |
| baseline FULL | 11 | 5.255 | 7.655 | 0.9993 | 2/11 (18.2%) | 0/11 (0.0%) | [2.529, 9.102] |
| baseline MOSTLY_CORRECT | 11 | 3.718 | 8.361 | 0.9918 | 9/11 (81.8%) | 8/11 (72.7%) | [0.846, 8.842] |
| baseline PARTIAL | 11 | 4.280 | 11.340 | 0.9496 | 8/11 (72.7%) | 9/11 (81.8%) | [0.555, 11.152] |
| baseline MISSING_CONCEPT | 11 | 1.257 | 2.871 | 0.9994 | 9/11 (81.8%) | 11/11 (100.0%) | [0.198, 3.000] |
| baseline MISCONCEPTION | 11 | 1.234 | 2.125 | 0.9985 | 9/11 (81.8%) | 10/11 (90.9%) | [0.502, 2.408] |
| baseline IRRELEVANT | 11 | 2.847 | 3.820 | n/a | 7/11 (63.6%) | 1/11 (9.1%) | [1.759, 4.547] |
| condition_e overall | 66 | 10.955 | 26.559 | 0.1985 | 38/66 (57.6%) | 21/66 (31.8%) | [5.642, 17.372] |
| condition_e FULL | 11 | 9.091 | 30.151 | 0.2108 | 10/11 (90.9%) | 10/11 (90.9%) | [0.000, 27.273] |
| condition_e MOSTLY_CORRECT | 11 | 18.682 | 31.871 | -0.3031 | 3/11 (27.3%) | 0/11 (0.0%) | [6.455, 37.228] |
| condition_e PARTIAL | 11 | 14.955 | 28.162 | 0.0519 | 0/11 (0.0%) | 0/11 (0.0%) | [5.441, 31.318] |
| condition_e MISSING_CONCEPT | 11 | 11.500 | 27.516 | 0.1528 | 7/11 (63.6%) | 0/11 (0.0%) | [2.452, 28.049] |
| condition_e MISCONCEPTION | 11 | 11.500 | 27.516 | 0.1528 | 7/11 (63.6%) | 0/11 (0.0%) | [2.452, 28.049] |
| condition_e IRRELEVANT | 11 | 0.000 | 0.000 | n/a | 11/11 (100.0%) | 11/11 (100.0%) | [0.000, 0.000] |

failed marking calls: 0 (excluded and counted, not scored)

not_evaluable answers: 0

### repaired eligible train

| set / method | n | MAE | RMSE | Pearson r | within +-2 marks | within 10% of max | MAE 95% CI (answer bootstrap) |
|---|---|---|---|---|---|---|---|
| baseline overall | 420 | 3.011 | 5.286 | 0.9574 | 242/420 (57.6%) | 199/420 (47.4%) | [2.595, 3.470] |
| baseline FULL | 70 | 5.304 | 7.069 | 0.9842 | 12/70 (17.1%) | 0/70 (0.0%) | [4.235, 6.506] |
| baseline MOSTLY_CORRECT | 70 | 3.304 | 5.796 | 0.9455 | 44/70 (62.9%) | 39/70 (55.7%) | [2.241, 4.542] |
| baseline PARTIAL | 70 | 2.750 | 6.892 | 0.9439 | 48/70 (68.6%) | 47/70 (67.1%) | [1.502, 4.439] |
| baseline MISSING_CONCEPT | 70 | 2.072 | 3.781 | 0.9747 | 48/70 (68.6%) | 52/70 (74.3%) | [1.336, 2.879] |
| baseline MISCONCEPTION | 70 | 1.971 | 3.493 | 0.9739 | 51/70 (72.9%) | 52/70 (74.3%) | [1.328, 2.739] |
| baseline IRRELEVANT | 70 | 2.663 | 3.179 | n/a | 39/70 (55.7%) | 9/70 (12.9%) | [2.288, 3.098] |
| condition_e overall | 420 | 4.144 | 6.871 | 0.9358 | 236/420 (56.2%) | 148/420 (35.2%) | [3.632, 4.664] |
| condition_e FULL | 70 | 0.143 | 1.195 | 0.9978 | 69/70 (98.6%) | 69/70 (98.6%) | [0.000, 0.429] |
| condition_e MOSTLY_CORRECT | 70 | 7.493 | 9.977 | 0.8828 | 24/70 (34.3%) | 2/70 (2.9%) | [6.064, 9.193] |
| condition_e PARTIAL | 70 | 8.557 | 10.641 | 0.8535 | 1/70 (1.4%) | 1/70 (1.4%) | [7.143, 10.100] |
| condition_e MISSING_CONCEPT | 70 | 4.336 | 5.876 | 0.9820 | 36/70 (51.4%) | 3/70 (4.3%) | [3.493, 5.329] |
| condition_e MISCONCEPTION | 70 | 4.336 | 5.876 | 0.9820 | 36/70 (51.4%) | 3/70 (4.3%) | [3.493, 5.329] |
| condition_e IRRELEVANT | 70 | 0.000 | 0.000 | n/a | 70/70 (100.0%) | 70/70 (100.0%) | [0.000, 0.000] |

failed marking calls: 0 (excluded and counted, not scored)

not_evaluable answers: 0

### original test (legacy reproduction: max=answers.marks column, fallback rubric, failed calls scored 0)

| set / method | n | MAE | RMSE | Pearson r | within +-2 marks | within 10% of max | MAE 95% CI (answer bootstrap) |
|---|---|---|---|---|---|---|---|
| baseline overall | 150 | 5.369 | 6.478 | 0.8194 | 37/150 (24.7%) | 19/150 (12.7%) | [4.778, 5.955] |
| baseline FULL | 25 | 5.691 | 6.732 | 0.8681 | 4/25 (16.0%) | 2/25 (8.0%) | [4.278, 7.084] |
| baseline MOSTLY_CORRECT | 25 | 5.484 | 6.398 | 0.8082 | 3/25 (12.0%) | 2/25 (8.0%) | [4.210, 6.720] |
| baseline PARTIAL | 25 | 6.340 | 7.083 | 0.6634 | 1/25 (4.0%) | 0/25 (0.0%) | [5.142, 7.587] |
| baseline MISSING_CONCEPT | 25 | 5.689 | 6.518 | 0.8439 | 7/25 (28.0%) | 0/25 (0.0%) | [4.411, 6.952] |
| baseline MISCONCEPTION | 25 | 5.490 | 6.435 | 0.8294 | 7/25 (28.0%) | 0/25 (0.0%) | [4.170, 6.838] |
| baseline IRRELEVANT | 25 | 3.523 | 5.608 | 0.6710 | 15/25 (60.0%) | 15/25 (60.0%) | [1.798, 5.240] |
| condition_e overall | 150 | 4.640 | 7.220 | 0.7243 | 84/150 (56.0%) | 84/150 (56.0%) | [3.727, 5.553] |
| condition_e FULL | 25 | 4.000 | 6.325 | 0.9041 | 15/25 (60.0%) | 15/25 (60.0%) | [2.000, 6.000] |
| condition_e MOSTLY_CORRECT | 25 | 7.600 | 10.296 | 0.3627 | 9/25 (36.0%) | 9/25 (36.0%) | [5.000, 10.520] |
| condition_e PARTIAL | 25 | 5.040 | 7.403 | 0.5135 | 13/25 (52.0%) | 13/25 (52.0%) | [2.999, 7.240] |
| condition_e MISSING_CONCEPT | 25 | 3.200 | 5.657 | 0.8222 | 17/25 (68.0%) | 17/25 (68.0%) | [1.600, 5.200] |
| condition_e MISCONCEPTION | 25 | 4.000 | 6.325 | 0.8263 | 15/25 (60.0%) | 15/25 (60.0%) | [2.000, 6.000] |
| condition_e IRRELEVANT | 25 | 4.000 | 6.325 | n/a | 15/25 (60.0%) | 15/25 (60.0%) | [2.000, 6.000] |

failed marking calls: 15 (scored 0.0 as the legacy script did: 15)

not_evaluable answers: 0

### original test (like-for-like: max=question marks, fallback rubric, failures excluded)

| set / method | n | MAE | RMSE | Pearson r | within +-2 marks | within 10% of max | MAE 95% CI (answer bootstrap) |
|---|---|---|---|---|---|---|---|
| baseline overall | 150 | 4.637 | 6.050 | 0.7587 | 60/150 (40.0%) | 50/150 (33.3%) | [4.026, 5.290] |
| baseline FULL | 25 | 5.691 | 6.732 | 0.8681 | 4/25 (16.0%) | 2/25 (8.0%) | [4.278, 7.084] |
| baseline MOSTLY_CORRECT | 25 | 4.182 | 5.612 | 0.8202 | 10/25 (40.0%) | 9/25 (36.0%) | [2.752, 5.654] |
| baseline PARTIAL | 25 | 4.510 | 6.100 | 0.6103 | 12/25 (48.0%) | 13/25 (52.0%) | [2.979, 6.155] |
| baseline MISSING_CONCEPT | 25 | 4.280 | 5.922 | 0.8338 | 12/25 (48.0%) | 13/25 (52.0%) | [2.682, 5.887] |
| baseline MISCONCEPTION | 25 | 4.201 | 5.913 | 0.8165 | 13/25 (52.0%) | 13/25 (52.0%) | [2.595, 5.859] |
| baseline IRRELEVANT | 25 | 4.960 | 5.962 | -0.4940 | 9/25 (36.0%) | 0/25 (0.0%) | [3.699, 6.297] |
| condition_e overall | 150 | 5.993 | 7.710 | 0.6847 | 54/150 (36.0%) | 32/150 (21.3%) | [5.216, 6.763] |
| condition_e FULL | 25 | 4.000 | 6.325 | 0.9041 | 15/25 (60.0%) | 15/25 (60.0%) | [2.000, 6.000] |
| condition_e MOSTLY_CORRECT | 25 | 8.620 | 10.466 | 0.3619 | 6/25 (24.0%) | 0/25 (0.0%) | [6.420, 11.160] |
| condition_e PARTIAL | 25 | 8.340 | 8.985 | 0.4565 | 0/25 (0.0%) | 0/25 (0.0%) | [7.100, 9.640] |
| condition_e MISSING_CONCEPT | 25 | 5.100 | 6.262 | 0.8199 | 10/25 (40.0%) | 2/25 (8.0%) | [3.680, 6.500] |
| condition_e MISCONCEPTION | 25 | 5.900 | 6.871 | 0.8157 | 8/25 (32.0%) | 0/25 (0.0%) | [4.540, 7.320] |
| condition_e IRRELEVANT | 25 | 4.000 | 6.325 | n/a | 15/25 (60.0%) | 15/25 (60.0%) | [2.000, 6.000] |

failed marking calls: 0 (excluded and counted, not scored)

not_evaluable answers: 0

### Documentation claims vs recomputation

| quantity | reported by documentation (not recomputed here) | recomputed here on the original test split (legacy settings) | reproduced |
|---|---|---|---|
| Condition E MAE | 4.64 | 4.640 | True |
| Condition E RMSE | 7.22 | 7.220 | True |
| Condition E Pearson r | 0.7243 | 0.7243 | True |
| Condition E within +-2 marks | 56.0% (84/150) | 56.0% (84/150) |  |
| Lexical baseline MAE | 5.609 | 5.369 | False |
| Lexical baseline within +-2 marks | 20.7% | 24.7% (37/150) |  |

Reproduced: Condition E MAE, Condition E RMSE, Condition E Pearson r. Not reproduced: Lexical baseline MAE. In the legacy reproduction 15 of 150 marking calls raised an exception (the overloaded `marks` column is 0 for IRRELEVANT answers, so the legacy rubric had max_marks 0) and were scored 0.0, which equals their label: the documented Condition E figures are therefore flattered on IRRELEVANT answers. The like-for-like row above uses max=question marks and excludes no answer.
