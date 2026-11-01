# Output and API

Both website and CLI share three_tier_backend.py. JSON float values and CSV decimal values retain round-trip precision. English/Chinese changes presentation only; stable class IDs, original labels, fields and values remain unchanged.

GET /api/bootstrap: runtime readiness, current scheme and four macaque examples (two original, two PsychENCODE), alongside the existing human example.
POST /api/uploads?species=macaque&sample_id=ID&filename=NAME: raw bytes; summary includes input_type, lower_input_status, missing requirements and observation counts. Human CEL validation remains separate.
POST /api/jobs: existing JSON fields species, configurations, source, sample_id, upload_id, contract_confirmed, request_key; optional example_id GSE128537, GSE179328, PsychENCODE_AMY or PsychENCODE_HIP. Current macaque configuration must be ["floor_clip"]. The local session token from bootstrap is required for mutations.
GET /api/jobs/ID: actual queued/running/succeeded/failed state; no simulated progress.
GET /api/jobs/ID/scores.csv: complete result CSV after success.
GET /api/examples?species=macaque&configurations=floor_clip&example_id=GSE128537: saved result without inference; append &format=csv for CSV.
GET /api/files/KEY: allowlisted local resource downloads only.

Each macaque result has tiers.Network, tiers.Group and tiers.Exact. Every tier has status, reason, classes, ranking, scores and score_type where available. Group additionally contains members and member_counts in class order; Exact contains corr50/corr100/corr200 in candidate-class order. Top3 is an inspection view, not all output. reference_id scopes Group IDs to their exact candidate combination.

Adult raw-count uploads use input_type=psychencode_common_annotation_counts. Their input_summary and exported CSV identify normalization_background=public_common_annotation_26514 and public_common_annotation_counts_total. The legacy full_library_counts numeric alias contains that same total; it does not assert an original unfiltered sequencing library. The HIP example_context uses parent compatibility, not unique subfield truth.

Statuses: succeeded; input_insufficient (Network panel only); input_incompatible (readable full axis but incompatible/missing contract information); reference_unavailable (exact Top3 combination absent); not_evaluable (original scientific signal guard rejected); failed (runtime error). Lower failures preserve Network; a Network failure does not fabricate a result. Session job status succeeded means processing completed; inspect each tier's state.

Saved examples use mode=saved_example; real inference uses live_frozen_inference. Only explicitly selected built-in examples receive example_context and saved_output_comparison. Unknown uploads/CLI --input do not receive truth or a successful-reproduction mark.
Files/results expire after 30 minutes in the running server memory; active tasks continue. Export important results. No database, external upload, hosting, training or evaluation queue is used.

Deployment: the HTTP listener remains loopback-only. --public-origin explicitly permits one configured HTTPS proxy origin. Resources are allowlisted inside the assembled directory; full-package and manuscript downloads are absent. Reference coverage is 43 combinations; scheme_id retains the frozen scientific identity, with asset edition recorded in bootstrap.scheme.deployment_asset_version.

Current PsychENCODE interface: see PSYCHENCODE_INPUT.md. Two example paths cover old/new reference lookup; no full-cohort rerun, model fitting or performance estimation.
