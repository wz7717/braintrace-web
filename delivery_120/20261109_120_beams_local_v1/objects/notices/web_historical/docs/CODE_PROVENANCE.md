# Upload audit edition, 2026-11-01

The upload candidate adds bounded untrusted-container checks around both Python backends and the Linux human adapter. It rejects excessive gzip expansion, malformed/oversized NPY declarations and excessive text records before scientific parsing. No `science/` code, model, reference, mapping or example asset was changed. All 147 runtime assets match the preceding candidate byte for byte.

The UI/install dependencies were updated to close current advisories, including Streamlit 1.66.1, Pillow 13.0.0, PyArrow 23.0.1, uv 0.13.4, pip 26.2 and setuptools 84.1.0. The tested Linux/Python 3.11 closure is constrained in `requirements-lock.txt`. pip-audit found no known advisories in that closure or in the unchanged scientific worker's Python packages. Static analysis reported no high-severity finding; two medium test-only URL findings and low-severity findings were reviewed in context. See `SECURITY.md` for scope and remaining hosting boundaries.

Fifty targeted checks passed on Linux: eight hostile-container cases, fourteen queue/session/process checks, six adapter/input checks, four Streamlit bridge checks, twelve three-tier contract/saved-output checks and six assembly/resource checks. The original human gzip also passed the expansion preflight. Existing input values remain identical. This audit ran no scientific inference, fitting, training, tuning, cohort evaluation or performance re-estimation; the scientific portability evidence below is reused.

The new local Streamlit page loaded both supported input routes and its resource controls. The browser tool explicitly reported that Blob downloads in embedded frames are unsupported; no completed file-save event was established. CSV payload/ownership checks passed, but actual file-save behavior remains a deployment acceptance item. The repository synchronization does not deploy the app or establish a public Cloud URL.

## Previous Streamlit/Linux compatibility edition (historical evidence)

New source lives beside the retained anonymous HTTP edition. Streamlit 1.55.0 is the UI entry; its scientific jobs run in a separate pinned Python 3.11.9 worker. The Linux human adapter is explicitly separate from the original frozen Windows driver. All original `science/` files, both original Python scoring backends, model parameters, references and mappings are unchanged.

Linux qualification used an isolated Debian 12 / WSL2 x86_64 environment with R 4.6.1 and the original four R package versions. One GSM755211 CEL produced all 16,295 features with maximum absolute difference 5.329070518200751e-15 from the saved Windows features. RAW_FIXED score difference was at most 2.220446049250313e-16; RANK_FIXED scores were identical. Class axes and rankings were unchanged. The predeclared absolute comparison tolerance was 1e-10, relative tolerance zero.

One PsychENCODE RMB160L.HIP input passed the unchanged adapter and all three tiers. All class axes, rankings and Group members matched. Network maximum score difference was 7.979727989493313e-17; Group/Exact scores and Exact correlations were identical. No training, tuning, bootstrap, cohort rerun or cohort performance calculation was performed.

Four focused synthetic Streamlit bridge checks passed: session separation and route controls, private task/CSV access, expiry, active-job restriction with released upload reservations, client-contained downloads, and preservation of the single service across Streamlit cache clearing. Three previously existing process-lifetime tests were executed specifically on Linux: descendant timeout/crash cleanup, next-job recovery, and shutdown cancellation. The prior Windows HTTP test results below are reused rather than represented as new Linux HTTP checks.

The native result view uses small Markdown tables. PyArrow is pinned to 17.0.0 because an unconstrained 26.0.0 install rejected the frozen NumPy 1.26.4 during an initial display check; this was a UI dependency error, not a change in model output.

The local Linux Streamlit page completed an adult HIP upload with all three result tables and a human GSM755211 live example with both RAW_FIXED/RANK_FIXED. The human page's saved-output comparison passed. Original human class names are displayed alongside their IDs. The Next task control clears the previous result. Across direct and browser integration checks there were five single-profile executions of two existing profiles: two direct portability jobs, two adult upload jobs (the first exposed the display dependency failure), and one human page job. There was no cohort rerun.

The owning human page contained the complete CSV payload, which was read and retained locally. The generated client-side Blob link was present; browser automation did not return a completed download event in the tested browsers. File-save behavior therefore remains an explicit deployment acceptance item, not a claimed passed browser-download test. No shared result-serving endpoint was added to bypass session isolation. Actual Community Cloud startup, remote anonymous access, cloud memory limits and load behavior also remain to be checked after deployment. This local edition has not been uploaded or deployed.

## Prior anonymous queue edition: reused evidence

This edition only changes the HTTP/session/queue/process lifecycle, frontend status handling,
configuration templates, relevant tests and documentation. demo_backend.py, three_tier_backend.py
and all existing science/ source files are unchanged relative to the previous GitHub checkout.
The separate `20261101_43_beams_psychencode_v1` runtime assets are reused without changes.
This edition has not been uploaded or deployed.

Fourteen focused checks passed: session ownership for uploads/tasks/CSV, cookie/CSRF and origin checks,
session/IP/global quotas, idempotency, FIFO, input reservations including interrupted/slow uploads,
expiry, queue deadlines, process-tree timeout/crash recovery, next-task execution and orderly shutdown.
These use synthetic inputs/workers and make no scientific calls.

Two real HTTP upload jobs passed through the new queue and child-process entry point on the existing
Windows/frozen environment: PsychENCODE RMB160L.HIP and human GSM755211 (RAW_FIXED plus RANK_FIXED).
Class axes and rankings matched saved outputs. Adult Group/Exact scores and Exact correlations matched
exactly; maximum Network score difference was 7.979727989493313e-17, within the original 1e-10 tolerance.
Both human configurations had maximum score difference zero. CSV matched the unchanged exporter,
cross-session reads/downloads were rejected, and unknown-upload results acquired no truth annotations.
Job work directories were empty after completion. Existing cohort results were not recalculated.

English/Chinese queue notices and saved-output mode were inspected locally. No public-domain,
cross-OS, load or full-cohort validation is claimed. Test evidence remains in the local private delivery folder.

## Historical implementation and adapter evidence (reused)

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
