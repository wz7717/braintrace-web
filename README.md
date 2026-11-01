# BrainTrace

The Streamlit entry point is `streamlit_app.py`. It supports live human Human Exon 1.0 ST CEL inference (RAW_FIXED/RANK_FIXED) and macaque Network/Group/Exact inference, including the adult PsychENCODE common-annotation adapter.

This deployment edition separates application source from `runtime_assets/`. Both are included in the authorized private-repository synchronization and are needed to run the app. Uploading GitHub does not start a hosted service or grant public redistribution rights. Models, mappings and all 43 lower-reference combinations retain their original bytes and identities. This is the web inference application, not the full research reproduction package.

## Streamlit Community Cloud

Choose branch `main`, entry point `streamlit_app.py` and Python **3.11**. Dependencies are pinned in `requirements.txt` and its audited `requirements-lock.txt` constraints. System packages are in `packages.txt`.

First startup builds a separate R 4.6.1 / CPython 3.11.9 scientific worker and may take several minutes. Actual Cloud startup, memory availability and viewer settings must be checked before sharing its assigned `*.streamlit.app` address. Read [deployment instructions](docs/STREAMLIT_CLOUD.md) and [security scope](SECURITY.md).

After installing the system packages, local Linux startup is:

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The anonymous interface has one FIFO worker, per-session and global limits, private task/result ownership and process-tree timeout recovery. Refresh, restart or Cloud sleep may lose access. This research demo has bounded capacity; it is not a confidential-data service.

## Inputs and interpretation

- Human: one compatible CEL/CEL.gz, at most 80 MiB input and 256 MiB after gzip expansion.
- Macaque: one documented 5,000/21,668-axis NPZ/CSV, or all 26,514 common-annotation count rows for one PsychENCODE profile. Maximum upload 8 MiB. Array declarations and text records are bounded before scientific parsing.
- A 5,000-gene input runs Network only. Group/Exact require the full supported contract and an available candidate combination. Forty-three references do not cover every possible combination.
- Scores rank candidates; they are not calibrated probabilities of anatomical correctness. Group membership and Exact single-label localization are distinct.

See [input formats](docs/INPUT_FORMATS.md), [PsychENCODE contract](docs/PSYCHENCODE_INPUT.md), [model card](docs/MODEL_CARD.md), [coverage](docs/COVERAGE.md) and [provenance](docs/CODE_PROVENANCE.md).

## Retained Windows HTTP/CLI tools

These use the original compatible scientific environment and local runtime settings. Assemble into a new directory:

```text
python -X utf8 -B tools/prepare_runtime.py --assets runtime_assets --out ../assembled_runtime
cd ../assembled_runtime
python -X utf8 -B site_server.py --port 8766
```

Open `http://127.0.0.1:8766/`. Assembly copies files without inference or overwriting either input. The Windows HTTP server is not the Community Cloud entry point. See [Windows deployment](docs/DEPLOYMENT_CN.md) and [human setup](docs/HUMAN_BUNDLE_SETUP.md).

## Repository contents

Keep user uploads/results, credentials, local configuration, logs, compiled environments, private editing records, PROJECT_MEMORY.md, AGENTS.md and full reproduction archives out of Git. `.gitignore` excludes assets by default; the supplied asset directory is an explicit addition for this private deployment. Do not redact or rebind frozen identity-bound files.

Resource-page downloads use allowlisted files inside the assembled runtime. Existing component licence notices remain in force; see [data and permissions](docs/DATA_AND_LICENSES.md). Repository access does not create a blanket MIT licence for models, references or third-party examples.
