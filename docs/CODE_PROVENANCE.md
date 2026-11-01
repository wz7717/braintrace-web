# Reused implementation

The sole current scheme identity was read from current_three_tier_scheme_20261101_01/CURRENT_SCHEME.json. Its final model assets, existing external beams and raw source mean were used, not outer OOF models.

Web site_server.py and braintrace_cli.py both call three_tier_backend.py. The backend calls the retained science/macaque/inference.py transform_external / score and the existing lower functions in science/lower/scoring.py. Model parameters and all reference numeric arrays are copied without alteration.

scoring.py contains the verbatim function bodies of:
- macaque_external_lower_validation_20261101_01/old_lower.py: rank_metrics, lower_predict;
- core/models.py: trace_corr;
- core/scientific_validation.py: signal_reason;
- core/signal_evidence.py: _finite_standard_deviation, panel_signal_evidence, ranking_is_undifferentiated; same NUMERICAL_SIGNAL_TOLERANCE=1e-12;
- scripts/run_bo2023_leave_one_monkey_out_validation.py: zscore.

Only their module import context is made portable. Reference builders, train/evaluate commands, conditional lower models and research run logs are not part of the inference module. Exact/Group tie rules remain in the original lower_predict body. Group/Exact truth-derived fields returned internally by that historical function are not treated as unknown-sample truth and are not exported.

The human scientific code, frozen models, original 37 references and bound scientific files are copied unchanged.
Six additional INPUT.npz/RULES_AND_MEMBERS.json pairs are copied from the completed PsychENCODE adult lower-reference completion.
The previous synchronization edition extended the combination index to 43 entries. This edition retains those entries and reference files unchanged; no reference builder is executed.

This source edition changes the HTTP wrapper's explicit proxy-origin configuration, removes external local-file download routes,
updates resource-page text and adds a copy-only runtime assembly tool. demo_backend.py and scientific kernels
are unchanged. three_tier_backend.py adds explicit input-contract handling and output metadata; scoring calls are retained. Scientific scheme identity remains the same; the separate asset edition records 43-reference coverage.
The original two input mappings remain supported, alongside the separate PsychENCODE common-annotation contract.

science/macaque/psychencode_adapter.py reuses the saved GENE_CORRESPONDENCE.json and numerical operation order from the completed adult prepare_adult.py: mapped count sum / all 26,514-row total, multiplication by 1e6, natural log1p, float32. It validates one raw-count column and adds explicit background metadata. tools/prepare_psychencode_sample.py extracts one RMB column; it does not infer. The web upload/example routes then call the existing frozen scorers. Two selected profiles were actually inferred for integration comparison, with no model fitting, full-cohort rerun or accuracy estimation.

Historical verification results in the private runtime assets retain their original dates/scope. Newly performed checks concern
assembly, input conversion, HTTP routing and two selected adult profiles against saved evidence; they do not establish cohort performance or general scientific validity.

Current PsychENCODE interface: see PSYCHENCODE_INPUT.md. Two example paths cover old/new reference lookup; no full-cohort rerun, model fitting or performance estimation.

## Completed integration checks (2026-11-01)

Six focused adapter/structure checks passed. Two real HTTP single-profile jobs used RMB160L.AMY (beam_024) and RMB160L.HIP (beam_038), covering the example and raw-count upload paths. Both adapted float32 inputs matched the historical prepared inputs exactly. Class axes, rankings and Group members matched; Group and Exact score differences were zero. Maximum Network score differences were 2.220446049250313e-16 and 7.979727989493313e-17; decision-value differences were 4.884981308350689e-15 and 5.995204332975845e-15 (absolute tolerance 1e-10).

Two read-only HTTP/resource checks passed with inference blocked; one extraction CLI check matched the saved HIP input. Syntax checks and bilingual browser inspection passed. These checks used the original local frozen environment and do not establish a full-cohort, cross-OS or public-hosting validation. This repository upload reuses those completed checks and performs no new scientific computation.
