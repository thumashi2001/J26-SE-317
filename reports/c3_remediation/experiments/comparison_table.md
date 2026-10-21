| candidate | val nMAE | test nMAE [95 % CI, question bootstrap] | test MAE (marks) | test QWK | test r | within 0.10 | runtime s |
|---|---|---|---|---|---|---|---|
| C_roberta_base_finetuned | 0.0377 | 0.0382 [0.0303, 0.0466] | 0.706 | 0.980 | 0.984 | 0.900 | 1997.32 |
| A1_tfidf_ridge | 0.0839 | 0.0812 [0.0744, 0.0880] | 1.296 | 0.934 | 0.938 | 0.689 | 0.4 |
| B1_sbert_features_ridge | 0.0927 | 0.0840 [0.0769, 0.0917] | 1.406 | 0.935 | 0.936 | 0.689 | 33.27 |
| R1_lexical_token_recall_baseline | 0.1059 | 0.1117 [0.0997, 0.1256] | 1.939 | 0.879 | 0.951 | 0.511 | 0.0 |
| B0_sbert_cosine_isotonic | 0.1317 | 0.1354 [0.1213, 0.1524] | 2.267 | 0.764 | 0.854 | 0.478 | 33.27 |
| A2_tfidf_cosine_overlap_gbr | 0.2524 | 0.2478 [0.2355, 0.2583] | 4.156 | 0.000 | None | 0.167 | 0.4 |
| R2_condition_E_binary_rubric | 0.2953 | 0.2094 [0.1774, 0.2443] | 3.544 | 0.682 | 0.733 | 0.333 | 0.0 |

Validation-selected learned candidate: **C_roberta_base_finetuned**
