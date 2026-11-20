# Current scheme and evidence boundaries

Scheme: BrainTrace_macaque_source_Ensembl97_floor_clip_20261120.
Manuscript edition: BrainTrace_R9_Ensembl97_Source_Fix_20261120. Final source-only model: 5,000-gene floor_clip balanced L2 multinomial logistic regression, C=0.1. No OOF-fold model is used for uploads.

Network Top3 screens candidates. Group uses original Top200 regional Pearson scores and ranks each saved group by its highest-scoring member. Exact independently ranks the same complete Network candidate set using 0.25*z(corr50)+0.75*z(corr100). Group never gates Exact; Network scores are not multiplied into the lower scores. Exact reverse numpy argsort and Group stable descending member-score ordering are unchanged.

This edition contains all 120 unordered Top3 combinations, each fitted on the revised nine-donor source reference. The complete inventory covers lookup for a valid Top3. Compatible input and evaluable signal are required for lower output. Candidate sets are matched exactly, unordered; no nearest combination, reselection, online fitting or fallback model is permitted. Group IDs and members depend on the beam and are not a mutually exclusive global dictionary. Every result includes reference_id to preserve that context.

Network scores are model scores within supported classes, not calibrated probabilities of correct anatomy. Group scores are Pearson coefficients; Exact scores are fused z scores and can be negative. They do not share a probability scale.

## Evaluation

The source cohort comprises 819 specimens from nine donors. Each outer holdout and each inner validation split applies the expression-detection filter to its own training donors. The final deployable model uses all nine source donors. GSE128537 and GSE179328 have 208 and 350 specimens in their primary Network evaluations and 40 and 177 in their unique fine-region evaluations. Adult PsychENCODE contributes 34 primary Network specimens and 15 unique fine-region specimens. In the endpoint table, `corrected_*` identifies this edition. The external evaluations revisit previously studied cohorts.

The human route supports nine classes for adult bulk Human Exon 1.0 ST CEL. Human lower-tier inference, cfRNA mixtures and patient diagnosis are outside the evaluated tasks.

[Ensembl 97 mapping coverage](https://github.com/wz7717/braintrace-analysis/blob/main/analysis/research/macaque_ensembl97/aggregates/coverage.csv) · [Donor-equal and pooled endpoints](https://github.com/wz7717/braintrace-analysis/blob/main/analysis/research/macaque_ensembl97/aggregates/FROZEN_ENDPOINTS.csv)
