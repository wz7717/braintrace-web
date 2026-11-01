# BrainTrace web application source

Source repository: https://github.com/wz7717/braintrace-web (private at initial creation).
It contains source, configuration templates and documentation. Runtime assets are supplied separately;
a source checkout alone cannot run inference or display the bundled saved examples. Only application source and documentation are stored in this repository; no runtime assets or hosted service are published here.

## Assemble a local runtime

Use an existing Python 3.11.9 installation compatible with requirements.txt. From this source directory:

```text
python -X utf8 -B tools/prepare_runtime.py --assets ../runtime_assets --out ../assembled_runtime
cd ../assembled_runtime
python -X utf8 -B site_server.py --port 8766
```

The output directory must not exist. The helper copies code and assets, preserving their relative paths;
it does not download, install dependencies, train, infer or overwrite either input directory.
Open http://127.0.0.1:8766/ . Select saved-result mode to inspect the supplied evidence without inference.
Human live CEL additionally requires the exact R environment and personal runtime.local.json settings.
See [deployment instructions](docs/DEPLOYMENT_CN.md) and [human setup](docs/HUMAN_BUNDLE_SETUP.md).

## Scope and versions

The frozen scientific scheme identity is unchanged: floor_clip Network plus original Pearson Group/Exact.
The deployment asset edition is `20261101_43_beams_psychencode_v1`: 37 original references plus six copied from the completed
adult analysis. The two original web input mappings are retained; PsychENCODE has a separate [common-annotation input contract](docs/PSYCHENCODE_INPUT.md).
The current scientific manuscript edition is `psychencode_adult_revision_20261101`; manuscripts are not included here.
Two targeted single-profile integration checks passed in this edition. The cohort was not rerun; no training, tuning, bootstrap or performance recalculation was performed. See [code provenance and integration checks](docs/CODE_PROVENANCE.md) for the executed scope.

The web server and CLI share the original backends. For saved CLI output only:

```text
python -X utf8 -B braintrace_cli.py --example GSE128537 --saved --out results/saved_example
```

The output must be new. Omitting `--saved` requests real inference; that is not a packaging check.
Scientific input/output definitions are in [INPUT_FORMATS](docs/INPUT_FORMATS.md),
[MODEL_CARD](docs/MODEL_CARD.md), [COVERAGE](docs/COVERAGE.md) and [OUTPUTS_AND_API](docs/OUTPUTS_AND_API.md).

## Hosting and resource links

This is a Python application, not a standalone GitHub Pages site. The server stays on loopback.
An explicit `--public-origin https://YOUR_HOST` permits a same-host HTTPS reverse proxy;
see the Caddy template in deployment/. No domain, credentials or remote service is configured by this delivery.
The template describes a small research demo with one in-memory inference worker, not an isolated multi-tenant service.

All resource-page links target allowlisted files inside the assembled runtime. Old parent-directory ZIP,
manuscript and full-package download routes were removed. No replacement online URL is invented.

## What belongs in GitHub

Keep this repository limited to application source and documentation. Keep runtime_assets, assembled runtime directories, runtime.local.json,
uploaded data, results, environment binaries and full reproduction archives outside the repository.
The included .gitignore covers common local additions; the human scientific files must retain exact LF bytes.
The local runtime asset directory contains unchanged identity-bound provenance and model files;
do not redact or rebind them to publish a nominally equivalent bundle.

Existing component licence notices are retained. Their scope and the unresolved model/reference/example
redistribution arrangements are described in [DATA_AND_LICENSES](docs/DATA_AND_LICENSES.md).
This source-only preparation does not declare all new integration code or all assets covered by MIT.

Current PsychENCODE interface: see docs/PSYCHENCODE_INPUT.md. Two example paths cover old/new reference lookup; no full-cohort rerun, model fitting or performance estimation.
