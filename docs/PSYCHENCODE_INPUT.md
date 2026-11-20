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

## Command line

From the assembled runtime, run `python braintrace_cli.py --help` to list installed examples.
The public edition includes the GSE128537 and GSE179328 macaque examples. To score an adult
rhesus count column that you have prepared as above, give its file and sample ID directly.

```text
python braintrace_cli.py --species macaque --input adult_counts.tsv --sample-id RMB160L.A1C --out adult_result
```

Choose a new output directory. The two locally retained AMY and HIP examples appear under
`--example` only in an edition that includes them in its example manifest.

## Frozen rules and metadata

Mapping: `PsychENCODE_Sousa2017_Ensembl91_XSAnno_source97_20261120`.
Contract: `braintrace.psychencode_common_annotation_input.v1`.
Normalization: `public_common_annotation_ln1p_CPM`; full_count_rows: 26514.

Source stable IDs use the previously resolved strict Ensembl Compara91 one-to-one human orthologs and XSAnno
common IDs. All source components are required; the saved within/between-feature collision exclusions remain.
For each covered feature, sum its mapped counts, divide by the total of ALL 26,514 public matrix rows,
multiply by 1e6, take natural log1p and cast to float32, in the original numerical order.
The model axis has 21,668 entries, 14,375 observed; the fixed 5,000-feature Network panel has 4,065 observed.
Missing Network values use the frozen training means; missing lower values use the original unweighted source raw mean.
Observed zero is not a missing value. Model parameters, reference arrays, scoring and tie rules are unchanged.

This common-annotation denominator differs from the original unfiltered sequencing library. The adaptation remains
exploratory and cannot be relabeled as either original full-library mapping.
Prepared NPZ: original x/genes/observed/samples fields, the distinct contract/mapping/normalization/count-row scalars,
and `public_common_annotation_counts_total` as a one-element array. `full_library_counts` is retained only as a
legacy numeric alias for backend compatibility and must equal that common-annotation total; it does NOT assert full raw-library coverage.
For a prepared 21,668-row CSV, repeat the metadata and both count totals on each gene row.
The reader checks the declared common-annotation total before ranking. A missing or invalid total, or a
disagreement with its alias, stops inference for the specimen. For a valid input, JSON and the score CSV
report the validated `public_common_annotation_counts_total` and its normalization background.

## Evidence and access

The adult evaluation used 77 profiles from five donors, including 34 primary Network profiles and 15 unique fine-region profiles. Use the current endpoint table below for accuracy by evaluation set.

## Attribution

Adapted for the outward Streamlit example scope from BrainTrace, *PsychENCODE / Sousa2017 adult rhesus input*,
at commit ca445528eb396c2ebe8ce0951099b82d579e0e74. The original is also in the published
MACAQUE_FIXED_ASSET_SET_v1. This version revises the web example and input-preparation instructions.
The frozen upload contract and source attribution are retained. The eligible project contributions
use [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Applicable source conditions
and third-party notices retain their original scope.

[Ensembl 97 mapping coverage](https://github.com/wz7717/braintrace-analysis/blob/main/analysis/research/macaque_ensembl97/aggregates/coverage.csv) · [Donor-equal and pooled endpoints](https://github.com/wz7717/braintrace-analysis/blob/main/analysis/research/macaque_ensembl97/aggregates/FROZEN_ENDPOINTS.csv)
