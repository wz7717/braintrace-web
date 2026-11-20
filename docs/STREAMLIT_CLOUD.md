# Streamlit Community Cloud edition

This entry point runs fixed human CEL inference and macaque Network/Group/Exact inference with 120 frozen reference combinations. The PsychENCODE common-annotation adapter accepts matching user-supplied input.

## Repository layout

The GitHub source directory is the repository root. Entry point: `streamlit_app.py`. Keep `requirements.txt`, `packages.txt` and `.streamlit/config.toml` at that root. Add the separately supplied `runtime_assets/` directory at the root on the deployment branch, or set the administrator-controlled `BRAINTRACE_ASSETS_DIR` to an existing assets directory. Source and assets must retain their current relative paths and edition identity.

The application deployment ZIP supplies the matching `runtime_assets/` directory. A source-only checkout requires the asset bundle for the same edition. Instance settings such as `runtime.local.json`, visitor uploads, results and build logs belong to the individual deployment.

## Hosting configuration

1. Select the intended GitHub repository and deployment branch in Streamlit Community Cloud. Use `streamlit_app.py`, Python **3.11**, and an available app subdomain.
2. Keep the GitHub repository private if appropriate for the assets. Configure the app's viewer setting to **public** for anonymous visitors. Repository access and app viewer access are separate choices.
3. Community Cloud reads `requirements.txt` and `packages.txt`. For Linux x86-64 on Python 3.11, the requirements include the [fixed app wheels](../deployment/linux-app-requirements.txt) with SHA-256 URL fragments. The managed host supplies its Python interpreter and system packages. The UI uses Streamlit 1.66.1, Pillow 13.0.0 and PyArrow 23.0.1.
4. First startup builds a private R 4.6.1 and installs an isolated CPython 3.11.9 worker **in a shared background startup task**. The page remains responsive, including its language switch. It shows the current stage, elapsed time, age of the latest output and the last 160 installation-log lines; full installation output also reaches the cloud console. The main Streamlit Python patch version is not substituted for the scientific worker. Exact NumPy/SciPy/scikit-learn and R package versions remain enforced.
5. After startup, verify the human CEL and the two macaque GEO cases on the deployed app and check their CSV exports. Obtain GSM755211.CEL.gz from [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM755211), using the identity in ../GEO_CEL_SOURCE.json. A local run and a deployed run are recorded separately.

## Pinned local Linux installation

Use the Linux x86-64 glibc runtime on a host with the prerequisites in [packages.txt](../packages.txt). The [Debian 12.15 package table](../deployment/debian-12.15-amd64-packages.tsv) identifies the 106 audited additions to the base system, with their versions, URLs and SHA-256 values. The application installer uses the operating system supplied by the host.

From the application directory, select a private ASCII absolute path for the runtime. `--with-app` prepares the Streamlit app environment in addition to R and the scientific worker.

~~~bash
export BRAINTRACE_CLOUD_HOME="$HOME/.cache/braintrace-streamlit-r461"
bash deployment/setup_linux.sh "$BRAINTRACE_CLOUD_HOME/dependencies" --with-app
"$BRAINTRACE_CLOUD_HOME/dependencies/app/bin/streamlit" run streamlit_app.py
~~~

The [Linux artifact table](../deployment/linux-artifacts.tsv) lists the R source, four R package sources, one CPython 3.11.9 archive and 42 wheels. Each entry gives the fixed URL, byte count and SHA-256. The installer checks cached files before reuse and checks a replacement download before placing it in the cache. Python packages install from the checked wheels using hash-required, index-free installation. The default installer invocation sets up the scientific worker and its R environment for the Streamlit startup path.

Keep matching `runtime_assets/` beside the source or set `BRAINTRACE_ASSETS_DIR`. Both the separately sourced CEL and the fixed research assets retain their published identities.


## Startup cache and recovery

- Keep the same `BRAINTRACE_CLOUD_HOME` (default `~/.cache/braintrace-streamlit-r461`). Each archive needed for this invocation is checked even when its installed component is available. A mismatched cache file is reacquired from its fixed URL. Components built or installed from the locked artifacts carry their source identity alongside the version check. The R build tree is kept under its source digest so interrupted builds can resume from the same archive.
- Only one startup task runs per application process. A filesystem lock also serializes dependency installers sharing this cache. Additional visitors, UI reruns and language switches observe the current startup rather than starting another build. Clearing Streamlit's resource cache does not reset the queue or initializer.
- A failed initialization stays failed until the explicit **Retry with cached components** button is used. A shared 60-second cooldown prevents repeated visitor retries. The installer has a 30-minute wall-clock limit; timed-out Linux process groups, including compiler descendants, are stopped. Previously completed components are retained. Retry is for a resolved/transient installation failure, not a substitute for reading the error.
- Progress represents stages, not an estimated percentage of compilation or time remaining. Compiler/download output can pause temporarily. Installation logs are plain text, bounded in the UI and credential/home-path redacted; they do not contain inference jobs, uploaded files or visitor results. The private `dependency-build.log` also retains installation output. Original technical errors and English technical guides remain available even when Chinese is selected.
- Community Cloud may discard the container filesystem during a rebuild. No persistent cache across container replacement is promised. A completely empty environment still compiles the pinned R version; the page cannot show application startup progress until the platform has installed the top-level requirements and started Streamlit. Select **Python 3.11** in deployment Advanced settings.
- The workbench has Chinese/English controls and separate input, job, result and resource panels, with the prior white/teal visual style. Widget keys and machine-readable route/program IDs are language-independent; switching language preserves the current page session and does not submit another job.

## Human Linux adapter

`portability/human_linux.py` invokes the original `validate_bundle`, input materialization and classifier helpers. `portability/predict_linux.R` retains all original numeric statements and asset, training-identity and gene-axis checks. It explicitly accepts the source R 4.6.1 Windows/ucrt provenance and requires R 4.6.1 Linux with the same four package versions. The original R driver remains in the bundle and remains hash-checked. Its code, the RDS reference, protocol and model metadata are not rewritten. The new adapter records its own identity and actual Linux R version; it does not impersonate the original Windows runtime.

R packages: preprocessCore 1.74.0, affxparser 1.84.0, digest 0.6.39, jsonlite 2.0.0. Scientific worker: CPython 3.11.9, NumPy 1.26.4, SciPy 1.13.1, scikit-learn 1.5.2. A compatible dependency installation alone is not evidence that scientific portability tests passed.

## Anonymous queue and privacy

- Each Streamlit page/WebSocket session gets a server-generated owner. The owner and CSRF value are never exposed as editable widgets or URL parameters. Separate tabs may create separate sessions; this is not natural-person identification.
- One FIFO worker process at a time. Each page session has at most one active job and four submissions per 30 minutes. Whole app: eight active jobs and 24 submissions per 30 minutes. A shared conservative bucket replaces the old trusted-proxy IP bucket because Streamlit's client IP is not a reliable security identity.
- One pending input per session, 96 MiB application input budget globally. Streamlit's native uploader receives bytes before the application reservation. The widget/server upload caps are 80 MiB for human and 8 MiB for macaque; these do not create a strict global bound on concurrent upload intake.
- Queue timeout: 15 minutes. Inference: 240 seconds human / 120 seconds macaque; human R processing also retains its 180-second inner limit. A failed or timed-out process group is terminated and its private directory is removed before the next job.
- Results expire after 30 minutes; sessions after 30 idle minutes or 2 hours total. Refresh/disconnect/restart may lose access. There is no automatic replay of uploads or jobs.
- CSV downloads are embedded only in the owning session as client-side data, without a shared server result URL. No arbitrary uploaded file is used as code, a model, or a filesystem path. Gzip CEL expansion is capped at 256 MiB inside the timed worker; NPZ header/array declarations and CSV/TSV row/column/field bounds are checked before numerical parsing. See `../SECURITY.md`.
- This free single-instance app has limited memory and compute. Queueing bounds computation, but does not provide high availability, strong anti-abuse identity, persistent jobs, or unlimited concurrent uploads. Cloud sleep/restart/OOM can interrupt work. Do not submit confidential or personally identifying data to this public research demonstration.

## Local Linux acceptance on 17 November 2026

The test used Debian 12.15 x86-64 under WSL2 with glibc 2.36 and the recorded 194 system packages. R, its four packages, CPython and the two application environments were installed in a fresh directory. The installer checked 46 previously obtained archives and two fresh PyPI downloads. It also detected a deliberately modified cached wheel and reacquired the matching bytes.

Streamlit 1.66.1 served its landing page and health endpoint on local HTTP. Streamlit AppTest exercised the application startup and example buttons through the same inference queue. The absolute score tolerance was 1e-10.

| Example | Result against the frozen reference |
| --- | --- |
| Human GSM755211 | RAW_FIXED and RANK_FIXED class axes and rankings matched. Top1 was 4132 for both. Maximum score differences were 2.22e-16 and 0, respectively. |
| Macaque GSE128537 / 10_10 | Reference beam_015, all three ranks and Group members matched. The maximum Network score difference was 2.08e-17. Group and Exact scores and the three correlation vectors matched exactly. |

The result applies to the installed Linux environment and these two single-sample routes. Managed Community Cloud installation, wider platform compatibility and cohort performance each have separate acceptance evidence.


## Targeted checks

For this edition, use GSM755211 (both frozen programs), GSE128537/10_10 and GSE179328/LID_100660 against their saved outputs. Check ordered class axes, rankings, scores and CSV export. Files under tests/ are inherited historical checks from ca445528. The fixture-based 43-reference and built-in PsychENCODE tests require their corresponding historical asset edition.

The original Windows HTTP/CLI entry points remain in the source for their existing use. The Streamlit/Linux entry point is `streamlit_app.py`; the old loopback HTTP server is not the Community Cloud application entry.

Official references: [app dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [context/IP caveat](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.context).
