# Single-sample input contract

Upload resource bounds: gzip CEL expansion is limited to 256 MiB in the timed worker. Macaque NPZ accepts only documented single-sample fields/shapes, non-object dtypes, bounded headers and at most 16 MiB declared array payload; CSV/TSV accepts at most 26,514 records, 12 unique columns and 1,024 characters per field. These checks precede scientific parsing and do not change accepted numerical values.

Human: adult bulk-tissue Human Exon 1.0 ST CEL or CEL.gz, nonempty, at most 80 MiB. The frozen PLM builds the full 16,295-coordinate axis, then the existing 200-feature RAW_FIXED / RANK_FIXED models. A filename cannot establish platform, adult eligibility or anatomy. Human inference and dependencies remain the existing frozen bundle.

Macaque files are at most 8 MiB; compressed NPZ expands to at most 16 MiB. Load with allow_pickle=False. Values must be finite and nonnegative at observed coordinates, measured zeros remain observed. Input values are converted to the original float32 representation before scoring. The original two mappings below use a positive complete-library total before mapping or panel selection. PsychENCODE uses a separate common-annotation denominator and contract, described in [PSYCHENCODE_INPUT](PSYCHENCODE_INPUT.md).

## Network-only legacy input

NPZ: `observed_logcpm` float shape (1,5000); `observed` Boolean (5000,); `genes` the exact supplied 5,000 strings in order; `samples` one string; `full_library_counts` shape (1,).
CSV: `gene_id,ln1p_cpm,observed,full_library_counts` with exactly 5,000 unique known genes; rows align by ID; observed is 0 or 1 and every row repeats the same library total.
These inputs return Network and explicit `input_insufficient` for Group and Exact. They never silently fill an unsubmitted lower panel.

## Original complete three-tier input: braintrace.three_tier_input.v1

NPZ uses the same orientation as the existing full-axis research files:

| Field | Required value |
|---|---|
| x | floating array (21668,1), raw natural ln(1+CPM), not Network-standardized |
| genes | 21668 strings exactly matching science/lower/genes.json in order |
| observed | Boolean (21668,), matches the declared frozen correspondence |
| samples | one nonempty string; user output ID may differ |
| full_library_counts | one finite positive full-library total |
| contract_version | scalar string braintrace.three_tier_input.v1 |
| normalization | scalar string full_library_ln1p_CPM |
| mapping_version | one of the two versions below |
| full_count_rows | scalar integer: 30807 or 22515 respectively |

CSV supports the same complete gene set in any order: `gene_id,ln1p_cpm,observed,full_library_counts,contract_version,mapping_version,normalization,full_count_rows`. Repeat every metadata field consistently on all 21,668 rows. Decimal float precision should be preserved; do not round values for display before export.

Supported mappings (engineering names for the existing correspondence files, not new biological mapping releases):

- `GSE128537_Ensembl91_existing_20261101`: complete 30,807-row rhesus count universe, original strict Ensembl 91 one-to-one mapping; full-axis 17,743 observed / 3,925 absent; Network 4,379 / 621.
- `GSE179328_Ensembl101_existing_20261101`: complete 22,515-row rhesus count universe, original strict Ensembl 101 one-to-one mapping; full-axis 16,019 observed / 5,649 absent; Network 4,377 / 623.

The package includes the full gene axis and both existing GENE_CORRESPONDENCE files, including source IDs, target IDs, covered flags and exclusion reasons. Exact axis, declared mapping and its observed mask are checked. A new assay with a different gene universe/mask or homology map is not established compatible by this demo. The declaration and numerical checks cannot prove the raw-data origin; the user must confirm it. Do not fill unsubmitted genes with zeros and label them absent to bypass this contract.

The first layer uses its saved training means, explicit standardized zero for missing coordinates, and the unchanged floor_clip transformation. The original lower tiers separately fill only contracted absent coordinates with the saved unweighted all819 raw logCPM mean, without first-layer standardization/floor/clip. Observed zero is never replaced by a missing-value mean.

If a full axis is structurally readable but required contract metadata is absent or incompatible, Network can run while Group/Exact return `input_incompatible` and explicit missing requirements. A partial full axis, duplicate gene IDs or malformed numeric data are rejected at upload. Unknown candidate combinations return `reference_unavailable`; numerical/signal failures remain distinct.

## Preparing another existing sample

The two included SINGLE_SAMPLE.npz files are direct column extractions from the existing prepared INPUT.npz files, with explicit metadata added; expression and masks were not recomputed.
For an already available compatible full prepared file, use:

The following extraction command applies to the separate local tools edition.

```text
python -X utf8 -B tools/extract_prepared_sample.py --input INPUT.npz --sample-id YOUR_SAMPLE --mapping GSE128537_Ensembl91_existing_20261101 --output new_sample.npz
```

This only extracts and validates a column. It does not map genes, normalize counts, guess homologs or construct new scientific inputs. Complete cohort matrices are deliberately not included. Their source and original preparation steps are in DATA_AND_LICENSES.md.

## PsychENCODE adult common-annotation input

Upload one complete 26,514-row count column as TSV/CSV, or use prepared NPZ/CSV carrying `braintrace.psychencode_common_annotation_input.v1` and `public_common_annotation_ln1p_CPM`. The adapter uses the saved Ensembl91-to-XSAnno correspondence and the sum of all public common-annotation rows. This is not the original unfiltered sequencing library and cannot be relabeled as either original mapping. Prepared inputs also require `public_common_annotation_counts_total`; the legacy `full_library_counts` field must equal it.

The [adult input guide](PSYCHENCODE_INPUT.md) gives the exact upload fields and explains how to select one input column. The AMY and HIP integration examples are retained in the local records. Their prior checks cover original and added reference lookup. For this delivery, submit your own compatible PsychENCODE input using the frozen contract in PSYCHENCODE_INPUT.md.
