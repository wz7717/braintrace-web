# Security scope

The 2026-11-01 deployment review covered the supplied Python/R/JavaScript application and helper code, launch/deployment configuration and runtime-asset inventory. Automated Python static analysis and dependency-advisory scanning were combined with manual review of upload parsing, session ownership, subprocess invocation, downloads and file access. This is a bounded review, not a guarantee that all vulnerabilities are absent.

## Changes from the previous candidate

`bounded_uploads.py` checks gzip expansion in the timed worker (256 MiB), validates NPZ members and NPY header lengths/shapes/dtypes/payload sizes before NumPy allocation, and caps CSV/TSV records, columns and fields before materialization. The scientific kernels and runtime assets remain unchanged. Copy-only assembly excludes Streamlit secrets as well as local runtime configuration.

Known Python-package advisories in the previous UI/install environment were addressed with Streamlit 1.66.1, Pillow 13.0.0, PyArrow 23.0.1, uv 0.13.4, pip 26.2 and setuptools 84.1.0. The exact tested Linux/Python 3.11 dependency closure is retained in `requirements-lock.txt`. At review time, pip-audit reported no known advisories for that installed closure or the unchanged scientific worker's Python packages. This result does not audit the operating system, R/native libraries or future advisories.

Bandit reported no high-severity finding. Its two medium findings concern fixed-localhost `urlopen` calls in test code; they do not accept arbitrary user URLs. Low-severity subprocess/import/assert findings were reviewed in context: production commands use argument lists without a shell, and uploaded files cannot select a command, model or asset path.

## Controls and limits

Task, upload and CSV access require the owning server-generated session. Computation runs one job at a time in a disposable child process. Deadline, crash, cancellation and session-expiry handling kill the process group and clean its owned working directory. Downloads contain only the requesting session's data. Assets and executable paths are administrator-controlled; user data is never loaded as a pickle/model or executed.

Process separation is a lifetime boundary, not an operating-system security sandbox. Native CEL readers remain part of the trusted scientific environment. Anonymous sessions can be recreated, and Streamlit receives upload bytes before application-level global reservations. Per-file caps, queue limits and quotas mitigate ordinary misuse but are not protection against a determined distributed denial-of-service attack. Do not add credentials or confidential datasets to the deployment environment.

Repository upload does not certify Community Cloud capacity or availability. Actual hosted startup, public viewer access, a human and macaque example, CSV save behavior and memory use must be checked at deployment. Keep the repository private until the component redistribution permissions are settled. Do not post uploaded data or credentials in a public issue when reporting a problem.

## Focused regression checks

Run from an assembled runtime in the documented environment:

```text
python -B tests/check_upload_bounds.py
python -B tests/check_anonymous_queue.py
python -B tests/check_psychencode_adapter.py
python -B tests/check_streamlit_bridge.py
```

These suites exercise hostile small containers, session separation/expiry/limits, timeout recovery and original input compatibility without cohort inference or model fitting. The separate Linux scientific portability results are documented in `docs/CODE_PROVENANCE.md`; they are not replaced by security checks.
