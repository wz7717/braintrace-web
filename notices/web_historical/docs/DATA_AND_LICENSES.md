# Data, code and component licences

The application source, documentation and `runtime_assets/` are included in the authorized private-repository synchronization to `wz7717/braintrace-web`. The source and runtime assets remain separate components and are both required to run the application. Uploading them to this private repository does not make them publicly available or grant public redistribution rights.
Existing research-code MIT text is retained at ../licenses/BrainTrace_existing_MIT.txt for its covered portions.
The supplied files do not establish a new blanket licence for all integration code, model arrays, reference matrices or inputs.
The author must state the intended licence scope of additions when publishing; this local preparation does not invent that grant.

Human frozen PLM references and models depend on their original source/annotation terms and contain bound provenance.
The exact four restored files are supplied to the server assets unchanged. They are not publicly downloadable from this resource page.
Macaque models and 43 reference combinations are derived from the author's processed Bo2023 source data.
PRJNA905082 public reads do not by themselves supply the processed matrices or confer a new licence on their derived references.
The three author-provided source count/VSD/metadata files are not included in this application delivery.

Public input records include human GSM755211 in GSE30453/GSE30483 and macaque GSE128537/GSM3679496,
GSE179328/GSM5414855. Prepared samples and saved outputs are in the local server assets. Public availability does not
automatically settle redistribution of a combined package. Existing notices in licenses/ remain applicable to their own components.
The resource page exposes these sample/mapping downloads in the assembled local app; decide their external distribution scope
before enabling access beyond the intended audience. Models and full reference bundles have no download route.

The original two web mappings use complete library count backgrounds:
GSE128537: GSE128537_Rhesus_RNA_gene_count.txt.gz, 30,807 rows / 408 columns;
GSE179328: original count background 22,515 rows / 527 columns. Full cohorts are not part of the demo.
tools/extract_prepared_sample.py only extracts from an already prepared compatible INPUT.npz; it does not build such a file.
The separate complete reproducibility delivery contains the analysis procedures; this source repository is not that archive.

PsychENCODE references were built from source data, not from external expression or truth. Their six saved numerical assets
are reused; the adult public-input adapter uses its own web contract and background label. No new legal or scientific conclusion follows from copying them.

The two added inputs, RMB160L.AMY and RMB160L.HIP, are single adult rhesus columns from the previously acquired Sousa2017/PsychENCODE `simFiltered.HPR.compGene.count.txt` matrix (26,514 rows and 247 cross-species columns). The saved strict one-to-one EnsemblCompara91/XSAnno correspondence is reused without a new mapping release. The application includes these two columns, their saved prepared inputs/results and the frozen row-ID universe; it excludes the full matrix and the 77-profile cohort outputs. Public access does not by itself grant a new combined-package licence.

Current PsychENCODE interface: see PSYCHENCODE_INPUT.md. Two example paths cover old/new reference lookup; no full-cohort rerun, model fitting or performance estimation.
