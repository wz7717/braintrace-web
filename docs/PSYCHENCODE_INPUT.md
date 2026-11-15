# PsychENCODE / Sousa2017 adult rhesus input

This adapter reuses the completed adult analysis rules and saved correspondence. It does not fit a new model,
rebuild lower references, discover homologs, rescue gene symbols or estimate cohort accuracy.

## Web input

Choose Macaque and Upload sample. The application adapts your own compatible raw-count profile
and applies the frozen Network, Group and Exact scorers under the original reference and input contracts.
The RMB160L.AMY and RMB160L.HIP demonstration files stay with the local application records.

For an upload, supply a UTF-8 TSV or CSV with exactly two columns: `ID` and an `RMB...` sample name,
or `gene_id` and `count`. Include every one of the 26,514 frozen common-annotation IDs exactly once.
`ENSG...|symbol` rows are allowed; only the ID before `|` is used. Symbols are never used for matching.
Counts must be finite, nonnegative integers; the total must be positive. Input row order may vary.
Partial panels, changed gene universes, duplicate IDs, TPM, log2 values and multi-sample uploads are rejected.
Only adult rhesus profiles from the documented common-annotation matrix are in scope. IDs and numeric
validation cannot establish specimen age/species/provenance; the user must confirm the source.

## Prepare one profile

From the documented common-annotation matrix that you have obtained under its applicable terms, select
the ID column and one compatible adult rhesus RMB column. Keep all 26,514 rows and the original count
strings. Save the two columns as UTF-8 TSV or CSV and upload that file. Keep the complete 247-column
matrix in the source records. A compatible prepared NPZ or CSV may also be submitted under the contract
below. An ordinary upload never inherits example truth from its filename or sample ID.

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

The source-only references and frozen mapping are reused for user uploads. The historical AMY example
covered the original reference branch, and the HIP example covered beam_038. These local integration
examples remain separate from the full cohort analysis. The HIP result supports parent-structure
compatibility and leaves hippocampal subfield localization unresolved.

## Attribution

Adapted for the outward Streamlit example scope from BrainTrace, *PsychENCODE / Sousa2017 adult rhesus input*,
at commit ca445528eb396c2ebe8ce0951099b82d579e0e74. The original is also in the published
MACAQUE_FIXED_ASSET_SET_v1. This version revises the web example and input-preparation instructions.
The frozen upload contract and source attribution are retained. The eligible project contributions
use [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Applicable source conditions
and third-party notices retain their original scope.
