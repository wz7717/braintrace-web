# PsychENCODE / Sousa2017 adult rhesus input

This adapter reuses the completed adult analysis rules and saved correspondence. It does not fit a new model,
rebuild lower references, discover homologs, rescue gene symbols or estimate cohort accuracy.

## Web input

Choose Macaque. The two PsychENCODE examples provide counts for RMB160L.AMY (original reference branch) and
RMB160L.HIP (added beam_038). Saved mode reads pre-existing scores; live mode adapts that one raw-count profile
and uses the same frozen Network/Group/Exact scoring. The example selection does not choose a better model.

For an upload, supply a UTF-8 TSV or CSV with exactly two columns: `ID` and an `RMB...` sample name,
or `gene_id` and `count`. Include every one of the 26,514 frozen common-annotation IDs exactly once.
`ENSG...|symbol` rows are allowed; only the ID before `|` is used. Symbols are never used for matching.
Counts must be finite, nonnegative integers; the total must be positive. Input row order may vary.
Partial panels, changed gene universes, duplicate IDs, TPM, log2 values and multi-sample uploads are rejected.
Only adult rhesus profiles from the documented common-annotation matrix are in scope. IDs and numeric
validation cannot establish specimen age/species/provenance; the user must confirm the source.

## Extract from the existing public matrix

Run in an assembled runtime with the supplied mapping assets:

```text
python -X utf8 -B tools/prepare_psychencode_sample.py --matrix PATH_TO/simFiltered.HPR.compGene.count.txt --sample-id RMB160L.HIP --out NEW_SAMPLE_DIRECTORY
```

This reads one selected RMB column and preserves all original row count strings. It writes COMMON_COUNTS.tsv
for direct web upload and PREPARED_SINGLE_SAMPLE.npz for the shared web/CLI contract. It does not download,
train or infer; the output directory must be new. Do not upload the complete 247-column cross-species matrix.
For CLI inference, pass the resulting TSV/NPZ using braintrace_cli.py --input; for saved display use
`--example PsychENCODE_HIP --saved`. An ordinary upload never inherits example truth from its filename or sample ID.

## Frozen rules and metadata

Mapping: `PsychENCODE_Sousa2017_Ensembl91_XSAnno_existing_20261101`.
Contract: `braintrace.psychencode_common_annotation_input.v1`.
Normalization: `public_common_annotation_ln1p_CPM`; full_count_rows: 26514.

Source stable IDs use the previously resolved strict Ensembl Compara91 one-to-one human orthologs and XSAnno
common IDs. All source components are required; the saved within/between-feature collision exclusions remain.
For each covered feature, sum its mapped counts, divide by the total of ALL 26,514 public matrix rows,
multiply by 1e6, take natural log1p and cast to float32, in the original numerical order.
The model axis has 21,668 entries, 14,382 observed; the fixed 5,000-feature Network panel has 4,064 observed.
Missing Network values use the frozen training means; missing lower values use the original unweighted source raw mean.
Observed zero is not a missing value. Model parameters, reference arrays, scoring and tie rules are unchanged.

This common-annotation denominator differs from the original unfiltered sequencing library. The adaptation remains
exploratory and cannot be relabeled as either original full-library mapping.
Prepared NPZ: original x/genes/observed/samples fields, the distinct contract/mapping/normalization/count-row scalars,
and `public_common_annotation_counts_total` as a one-element array. `full_library_counts` is retained only as a
legacy numeric alias for backend compatibility and must equal that common-annotation total; it does NOT assert full raw-library coverage.
Prepared 21,668-row CSV can use the same metadata repeated on each row, including the explicit common-annotation total.
JSON and exported score CSV identify normalization_background and public_common_annotation_counts_total.

## Evidence and access

The input code is separated from the server mapping, row-ID universe and example assets. The full cohort matrix,
source training data, environment and 77-profile analysis outputs are not copied into this demo.
Existing manuscript results are preserved; two targeted integration examples are not a new estimate of accuracy.
The HIP example is parent-structure compatibility, not a claim of hippocampal subfield localization.
Source disclosure and component redistribution terms continue to apply. This private source repository does not publish runtime assets or deploy a web service.
