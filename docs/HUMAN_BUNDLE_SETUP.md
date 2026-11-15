# Human runtime setup

The separate runtime_assets directory contains the complete unchanged scientific human bundle.
tools/prepare_runtime.py combines it with science/human/code from the source checkout.
The assembled science/human includes protocol/PROTOCOL.json, reference/FROZEN_UPSTREAM_STATE_INDEX.json,
models/final_RAW_FIXED.npz and models/final_RANK_FIXED.npz, plus the original manifest and upstream references.
No addon, search, reconstruction, training or download is needed to assemble this local delivery.

The original scientific code and binding files retain their exact bytes. Provenance contains historical
author paths and training identity metadata; runtime/query paths are supplied by explicit configuration.
Do not remove or redact identity-bound files, edit scientific code line endings, or replace model files with accession links.

Use Python3.11.9 and requirements.txt. Human live processing additionally needs R4.6.1 (2026-06-24 ucrt),
preprocessCore1.74.0, affxparser1.84.0, digest0.6.39, jsonlite2.0.0, as specified in the original PREDICTION_BUNDLE.json.
Copy runtime.example.json to runtime.local.json in the assembled directory, then set python, rscript, rlib,
optional rlib_site and an existing ASCII temp_root on the deployment host. This personal configuration is not source code.
These commands configure the Windows route. On Linux use the separate adapter and pinned environment in STREAMLIT_CLOUD.md.

Local completeness and public redistribution permission are separate; see DATA_AND_LICENSES.md.

For the live human example, obtain GSM755211.CEL.gz from GEO and match the identity in ../GEO_CEL_SOURCE.json. Place the file in runtime_assets/examples/human/ before assembly, or submit it as a CEL upload.
