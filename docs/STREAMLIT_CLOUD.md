# Streamlit Community Cloud edition

This entry point preserves live human CEL inference and macaque Network/Group/Exact inference, including the PsychENCODE common-annotation adapter and 43 existing lower references. No models, reference values, mappings, training identities or scientific kernels are changed.

## Repository layout

The GitHub source directory is the repository root. Entry point: `streamlit_app.py`. Keep `requirements.txt`, `packages.txt` and `.streamlit/config.toml` at that root. Add the separately supplied `runtime_assets/` directory at the root on the deployment branch, or set the administrator-controlled `BRAINTRACE_ASSETS_DIR` to an existing assets directory. Source and assets must retain their current relative paths and edition identity.

The source `.gitignore` excludes runtime assets to prevent accidental publication. This authorized private-deployment synchronization explicitly includes the supplied `runtime_assets/` subdirectory; future source-only checkouts still need those assets. Do not upload the full research reproduction package to run this app. Do not include private editing materials, PROJECT_MEMORY.md, AGENTS.md, runtime.local.json, user uploads, results, local logs, WSL disks or compiled local environments.

## Hosting configuration

1. Select the intended GitHub repository and deployment branch in Streamlit Community Cloud. Use `streamlit_app.py`, Python **3.11**, and an available app subdomain.
2. Keep the GitHub repository private if appropriate for the assets. Configure the app's viewer setting to **public** for anonymous visitors. Repository access and app viewer access are separate choices.
3. Community Cloud installs Python packages from `requirements.txt`, constrained by the audited Linux/Python 3.11 `requirements-lock.txt`, and Debian system libraries from `packages.txt`. The UI uses Streamlit 1.66.1, Pillow 13.0.0 and PyArrow 23.0.1; these do not change the isolated scientific worker.
4. First startup builds a private R 4.6.1 and installs an isolated CPython 3.11.9 worker. The main Streamlit Python patch version is not substituted for the scientific worker. Exact NumPy/SciPy/scikit-learn and R package versions remain enforced. Initial dependency construction can take several minutes and may repeat after a cloud rebuild.
5. After successful cloud startup, check one human CEL example and one macaque example through the deployed UI, verify the original saved-example comparison, and confirm that their CSV download links save usable files in the target browser. The local browser automation verified the embedded CSV payload but did not confirm the browser's download completion. This is a cloud deployment check, not a cohort rerun. Only then share the assigned `https://<name>.streamlit.app` address.

Local Linux preparation (no training or predictions):

```bash
python -m pip install -r requirements.txt
bash deployment/setup_linux.sh "$HOME/.cache/braintrace-streamlit-r461/dependencies"
streamlit run streamlit_app.py
```

The required system packages are listed in `packages.txt`. Install them into an isolated host/container before the manual setup command. The setup script needs network access to official CRAN, Bioconductor, Python/uv and Python-package sources. It does not download model assets. `BRAINTRACE_CLOUD_HOME` may select another private writable cache directory. It must be an ASCII absolute path. Do not change the original frozen bundle to make a platform check pass.

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

## Targeted checks

`tests/check_streamlit_bridge.py`: synthetic queue ownership, expiry, download isolation and native Streamlit route/session checks. `tests/check_anonymous_queue.py ProcessChecks`: Linux process timeout/descendant termination/recovery. `tests/check_linux_portability.py`: one existing human GSM755211 CEL (both frozen programs, all 16,295 features) and one adult PsychENCODE HIP sample against saved outputs, with absolute tolerance 1e-10 and unchanged rankings. These checks do not re-estimate cohort performance.

The original Windows HTTP/CLI entry points remain in the source for their existing use. The Streamlit/Linux entry point is `streamlit_app.py`; the old loopback HTTP server is not the Community Cloud application entry.

Official references: [app dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [context/IP caveat](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.context).
