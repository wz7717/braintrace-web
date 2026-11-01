"""Streamlit session bridge to the existing single-worker job service."""
from pathlib import Path
from types import SimpleNamespace
import atexit
import json
import os
import subprocess
import sys
import tempfile
import threading

_SERVICE = None
_SERVICE_LOCK = threading.Lock()
_STARTUP = None
_STARTUP_LOCK = threading.Lock()


def get_service(source, report=None):
    # Streamlit's Clear Cache must not create a second worker or reset global quotas.
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = bootstrap(source, report=report)
        return _SERVICE


def get_startup(source):
    global _STARTUP
    from startup_runtime import StartupManager
    with _STARTUP_LOCK:
        if _STARTUP is None:
            _STARTUP = StartupManager(lambda report: get_service(source, report))
        _STARTUP.start()
        return _STARTUP


def bootstrap(source, report=None):
    from startup_runtime import run_logged
    report = report or (lambda stage=None, line='': None)
    report('cache', 'Checking the existing fixed environment; completed components will be reused.')
    source = Path(source).resolve()
    assets = Path(os.environ.get('BRAINTRACE_ASSETS_DIR', source/'runtime_assets')).resolve()
    if not assets.is_dir() and (source.parent/'runtime_assets').is_dir():
        assets = source.parent/'runtime_assets'
    if not (assets/'ASSET_EDITION.json').is_file():
        raise RuntimeError('Missing separate runtime_assets directory. See docs/STREAMLIT_CLOUD.md.')
    runtime_home = Path(os.environ.get('BRAINTRACE_CLOUD_HOME', Path.home()/'.cache/braintrace-streamlit-r461'))
    runtime_home.mkdir(parents=True, exist_ok=True)
    prefix = runtime_home/'dependencies'
    worker = prefix/'worker/bin/python'
    rscript = prefix/'R/bin/Rscript'
    rlib = prefix/'rlib'
    if sys.platform.startswith('linux'):
        # Component probes also recover partial installations. The shell lock
        # prevents another process from compiling into the same dependency cache.
        run_logged(['bash', str(source/'deployment/setup_linux.sh'), str(prefix)],
                   runtime_home/'dependency-build.log', report, timeout=1800)
        report('verify', 'Verifying the pinned scientific Python and R package versions.')
        check = subprocess.run([str(worker), '-c',
            'import platform,numpy,scipy,sklearn; assert (platform.python_version(),numpy.__version__,scipy.__version__,sklearn.__version__)==("3.11.9","1.26.4","1.13.1","1.5.2")'], capture_output=True, timeout=30)
        if check.returncode:
            raise RuntimeError('Pinned scientific Python is incomplete.')
        rcheck=subprocess.run([str(rscript),'--vanilla','-e',
            'stopifnot(getRversion()=="4.6.1"); expected <- c(preprocessCore="1.74.0",affxparser="1.84.0",digest="0.6.39",jsonlite="2.0.0"); for(p in names(expected)) stopifnot(as.character(packageVersion(p))==expected[[p]])'],
            env={**os.environ,'R_LIBS_USER':str(rlib)},capture_output=True,timeout=30)
        if rcheck.returncode:
            raise RuntimeError('Pinned R packages are incomplete; see docs/STREAMLIT_CLOUD.md.')
        os.environ.update(BRAINTRACE_PYTHON=str(worker), BRAINTRACE_RSCRIPT=str(rscript),
                          BRAINTRACE_RLIB=str(rlib), BRAINTRACE_RLIB_SITE=str(rlib))
    else:
        worker = Path(os.environ.get('BRAINTRACE_PYTHON', sys.executable))
    from tools.prepare_runtime import prepare
    report('assets', 'Preparing the application with the existing frozen assets; no inference.')
    assembled = Path(tempfile.mkdtemp(prefix='braintrace_app_', dir=runtime_home))/'runtime'
    prepare(source, assets, assembled)
    sys.path.insert(0, str(assembled))
    work = assembled.parent/'jobs'; work.mkdir()
    os.environ['BRAINTRACE_TEMP_ROOT'] = str(work)
    service = CloudService(assembled, worker, work)
    report('ready', 'Both routes are ready. No samples were run during startup.')
    return service


class CloudService:
    # All clients share this conservative bucket. Cloud client IP is not trusted.
    BUCKET = 'community-cloud-all-visitors'

    def __init__(self, root, worker, work, runner=None):
        import site_server as original
        from anonymous_sessions import AnonymousSessions, QueuePolicy
        from queued_jobs import JobStore
        from process_jobs import ProcessRunner
        self.api = SimpleNamespace(**{k:getattr(original,k) for k in (
            'now','validate_input','require_species','configurations','require_sample_id','FILES','ROOT','backend')})
        self.api.scientific_runtime_ready = lambda: Path(worker).is_file()
        self.policy = QueuePolicy(active_jobs_per_ip=8, jobs_per_ip_half_hour=24,
                                  new_sessions_per_ip_hour=60, uploads_per_session=1,
                                  uploads_global=8, input_bytes_global=96*1024**2)
        self.sessions = AnonymousSessions(self.policy)
        self.store = JobStore(self.api,self.sessions,self.policy,runner or ProcessRunner(root,work,python=str(worker)))
        self.backend = original.backend
        atexit.register(self.store.close)

    def session(self, cookie=None):
        # Cookie text never leaves Python session_state or enters a widget/query string.
        owner, csrf, new_cookie = self.sessions.resolve(cookie,self.BUCKET,create=cookie is None)
        return owner, csrf, new_cookie or cookie

    def submit_upload(self, owner, csrf, species, sample_id, filename, data, configurations, request_key):
        # UI reruns must not reserve another upload for an already accepted request.
        with self.store.lock:
            previous=self.store.request_keys.get((owner,request_key))
            if previous:
                raise ValueError('此请求已提交，请查看现有任务。')
        self.sessions.mutation(owner,self.BUCKET,csrf)
        # Native Streamlit upload intake precedes this application quota; documented explicitly.
        with self.store.upload_slot(owner,self.BUCKET,len(data)) as slot:
            uploaded = self.store.upload(owner,species,sample_id,filename,data,slot)
        try:
            return self.store.submit(owner,self.BUCKET,dict(species=species,sample_id=sample_id,
                configurations=configurations,source='upload',upload_id=uploaded['upload_id'],
                contract_confirmed=True,request_key=request_key))
        except Exception:
            self.store.remove_upload(owner,uploaded['upload_id'])
            raise

    def submit_example(self,owner,csrf,species,example,configurations,request_key):
        self.sessions.mutation(owner,self.BUCKET,csrf)
        return self.store.submit(owner,self.BUCKET,dict(species=species,sample_id='example',
            configurations=configurations,source='example',example_id=example,request_key=request_key))

    def result(self,owner,job_id):
        from anonymous_sessions import APIError
        if not self.sessions.alive(owner):
            raise APIError('匿名会话已过期。','session_expired',401)
        return self.store.snapshot(owner,job_id)

    def csv(self,owner,job_id):
        job = self.result(owner,job_id)
        if job['status'] != 'succeeded':
            raise ValueError('Result is not complete.')
        return self.backend.result_csv(job['result'])
