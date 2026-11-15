# Current scheme and evidence boundaries

Scheme: BrainTrace_macaque_floor_clip_original_lower_research_20261101_v1.
Manuscript edition: psychencode_adult_revision_20261101. Final source-only model: 5,000-gene floor_clip balanced L2 multinomial logistic regression, C=0.1. No OOF-fold model is used for uploads.

Network Top3 screens candidates. Group uses original Top200 regional Pearson scores and ranks each saved group by its highest-scoring member. Exact independently ranks the same complete Network candidate set using 0.25*z(corr50)+0.75*z(corr100). Group never gates Exact; Network scores are not multiplied into the lower scores. Exact reverse numpy argsort and Group stable descending member-score ordering are unchanged.

This local edition holds all 120 unordered Top3 reference keys, with 43 retained and 77 converted frozen pairs. The complete inventory covers lookup for a valid Top3. Compatible input and evaluable signal are required for lower output. Candidate sets are matched exactly, unordered; no nearest combination, reselection, online fitting or fallback model is permitted. Group IDs and members depend on the beam and are not a mutually exclusive global dictionary. Every result includes reference_id to preserve that context.

Network scores are model scores within supported classes, not calibrated probabilities of correct anatomy. Group scores are Pearson coefficients; Exact scores are fused z scores and can be negative. They do not share a probability scale.

## Saved evidence, not new performance estimation

The external Network evaluation sets contain 208 GSE128537 samples and 350 GSE179328 samples. Their operational unique fine-region sets contain 40 and 177 samples respectively. These are different evaluation sets, not a common-denominator funnel. The two unique fine-region sets cover only seven source fine-region labels, not all 110.

Original lower transfer is limited by this narrow anatomical coverage and domain shift. Source-developed per-Network 500-gene conditional logistic lower tiers did not transfer: donor-equal Exact Top1 fell from 55.00% to 10.00% in GSE128537 and from 62.22% to 22.64% in GSE179328, under the same frozen head. These comparisons are complete procedures, not isolated classifier effects. The no-head-multiplier ablation was overall negative; the F1 Top3 recovery of 19 did not improve F1 Top1. Neither development branch is used or offered as a fallback.

The scheme was selected after viewing source and external evidence. It is not a global optimum, an untouched external confirmation or evidence of universal exact localization. Detailed saved evidence is retained in the separate current manuscript and reproducibility deliveries.

GSE128537 sample10_10: frontal Network truth missed at Top1 and included in Top3; fine truth is an allowed F1–F7 set, not a unique label. GSE179328 LID_100660: amygdala operational label; Group Top1 is amy but Exact Top1 is HC and amy is Top2. Neither example is presented as universally correct.
An uploaded file never inherits an example's truth or comparison badge simply by matching its filename or sample ID.

Human route remains separate: nine supported classes, adult bulk Human Exon 1.0 ST only; no human Group/Exact implementation. Parietal cortex, insula and pons are unsupported. Medulla reference is inferior olivary nucleus. cfRNA mixtures and patient diagnosis are outside scope. HPA donor linkage, precise coordinates, expert anatomy review and UKBEC–GTEx donor nonoverlap remain unresolved. Local example agreement is not complete raw-to-training reproduction or cross-OS validation.

## Additional completed adult analysis

The adult PsychENCODE analysis reports 77 rhesus profiles from five donors. Its primary Network set is 34 samples,
with donor-equal Top1/Top3 76.19%/93.81%. The unique fine-label set is 15 samples covering amy/F1/V1:
Group 73.33%/80.00%, Exact 40.00%/66.67%. Parent compatibility and ambiguous-label sets are separate;
output availability for all 77 is not accuracy for all 77. These three labels do not expand the prior seven-label external union.
The source-only six missing combinations were built previously and are reused here. The PsychENCODE common-annotation
input adapter now uses its own contract on this webpage. Targeted checks do not recalculate cohort performance.

The AMY and HIP integration examples are retained in the local records. Their prior checks cover original and added reference lookup. For this delivery, submit your own compatible PsychENCODE input using the frozen contract in PSYCHENCODE_INPUT.md.
