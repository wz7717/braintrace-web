"""Loopback HTTP adapter; optional explicit HTTPS origin for a reverse proxy.

Shares three_tier_backend with the CLI; packaged scoring functions and models are frozen.
Run with the Python executable from runtime.local.json.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import mimetypes
import platform
import secrets
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

import three_tier_backend as backend

ROOT = backend.ROOT
MAX_UPLOADS_BYTES = 160 * 1024**2
RETENTION_SECONDS = 30 * 60
FILES = {
    'psychencode-amy': ROOT / 'examples/three_tier/PsychENCODE_AMY/COMMON_COUNTS.tsv',
    'psychencode-hip': ROOT / 'examples/three_tier/PsychENCODE_HIP/COMMON_COUNTS.tsv',
    'human-example': ROOT / 'examples/human/GSM755211.CEL.gz',
    'macaque-example': ROOT / 'examples/three_tier/GSE128537/SINGLE_SAMPLE.npz',
    'macaque-network-example': ROOT / 'examples/macaque/OBSERVED_ONE_SAMPLE.npz',
    'macaque-second-example': ROOT / 'examples/three_tier/GSE179328/SINGLE_SAMPLE.npz',
    'full-genes': ROOT / 'science/lower/genes.json',
    'macaque-csv': ROOT / 'examples/macaque/PREPARED_INPUT_EXAMPLE.csv',
    'macaque-genes': ROOT / 'science/macaque/baseline/genes.json',
}


def resource_files():
    index=ROOT/'resources/FILES.json'
    files = {}
    if index.exists():
        for key, rel in backend.read_json(index).items():
            target = (ROOT / rel).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise ValueError('Resource paths must remain inside the assembled runtime.')
            files[key] = target
    return files


def now():
    return datetime.now(timezone.utc).isoformat()


class APIError(Exception):
    def __init__(self, message, code='invalid_request', status=400, detail=None):
        super().__init__(message)
        self.code, self.status, self.detail = code, status, detail


def require_species(species):
    if species not in ('human', 'macaque'):
        raise APIError('请选择人类或猕猴参考模型。')
    return species


def require_sample_id(sample_id):
    if not isinstance(sample_id, str):
        raise APIError('样本 ID 必须为文本。')
    try:
        return backend.validate_id(sample_id)
    except ValueError as exc:
        raise APIError('样本 ID 需为 1–128 位英文字母、数字、下划线、点或短横线，并以字母或数字开头。') from exc


def configurations(species, values):
    allowed = ['RAW_FIXED', 'RANK_FIXED'] if species == 'human' else list(backend.ROUTES)
    if not isinstance(values, list) or not values or any(not isinstance(x, str) or x not in allowed for x in values):
        raise APIError('请选择有效的冻结配置。')
    if len(values) != len(set(values)):
        raise APIError('配置不可重复。')
    return [x for x in allowed if x in values]


def scientific_runtime_ready():
    import scipy
    import sklearn
    return (platform.python_version(), backend.np.__version__, scipy.__version__, sklearn.__version__) == (
        '3.11.9', '1.26.4', '1.13.1', '1.5.2')


def validate_input(species, sample_id, filename, data):
    require_species(species)
    require_sample_id(sample_id)
    if not isinstance(filename, str) or not filename or len(filename) > 255:
        raise APIError('文件名为空或过长。')
    filename = filename.replace('\\', '/').split('/')[-1]
    lower = filename.lower()
    suffix = '.cel.gz' if lower.endswith('.cel.gz') else '.' + lower.rsplit('.', 1)[-1]
    limit = (80 if species == 'human' else 8) * 1024**2
    if not data or len(data) > limit:
        raise APIError(f'文件须非空且不超过 {limit // 1024**2} MiB。', 'file_size', 413 if data else 400)
    summary = {'filename': filename, 'bytes': len(data), 'sample_id': sample_id, 'species': species,
               'suffix': suffix, 'validation_level': 'container_only' if species == 'human' else 'prepared_input'}
    if species == 'human':
        if suffix not in ('.cel', '.cel.gz'):
            raise APIError('人类参考仅接受 .CEL 或 .CEL.gz，不接受任意 .gz 文件。', 'input_format')
        if suffix == '.cel.gz' and data[:2] != b'\x1f\x8b':
            raise APIError('文件不是有效的 gzip 容器，请检查 CEL.gz 文件完整性。', 'input_format')
        summary['message'] = '扩展名与大小检查通过；CEL 内容、平台及模型绑定将在真实推断中校验。成人组织适用性需依据样本元数据确认。'
    else:
        try:
            prepared = backend.read_input(data, suffix, sample_id)
        except (ValueError, KeyError, TypeError, IndexError, UnicodeError, csv.Error, zipfile.BadZipFile, EOFError, OSError) as exc:
            detail = str(exc)[:350] if isinstance(exc, ValueError) else None
            raise APIError('输入校验未通过。请检查原有模型输入，或完整 26,514 行 PsychENCODE 单样本计数及对应基因标识。', 'input_format', detail=detail) from exc
        summary.update(backend.input_summary(prepared))
        summary['message'] = ('PsychENCODE 共同注释输入检查通过；分母为全部 26,514 行计数，不是原始未过滤测序文库。' if summary.get('normalization_background')=='public_common_annotation_26514' and prepared['lower_status']=='compatible' else
                              '完整三层输入契约检查通过。原始数据及归一化来源仍需由你确认。' if prepared['lower_status']=='compatible'
                              else 'Network 输入检查通过；下层输入不足或不兼容，仍可运行第一层。请查看缺项。')
    return summary


class JobStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='frozen-inference')
        self.uploads, self.jobs, self.request_keys = {}, {}, {}
        self.stop_cleanup = threading.Event()
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True, name='cache-cleanup')
        self.cleanup_thread.start()

    def _cleanup_loop(self):
        while not self.stop_cleanup.wait(30):
            self.cleanup()

    def cleanup(self):
        cutoff = time.time() - RETENTION_SECONDS
        with self.lock:
            self.uploads = {k: v for k, v in self.uploads.items() if v['stored_at'] > cutoff}
            self.jobs = {k: v for k, v in self.jobs.items() if v['status'] in ('queued', 'running') or v['finished_epoch'] > cutoff}
            self.request_keys = {k: v for k, v in self.request_keys.items() if v in self.jobs}

    def upload(self, species, sample_id, filename, data):
        summary = validate_input(species, sample_id, filename, data)
        self.cleanup()
        with self.lock:
            if len(self.uploads) >= 8 or sum(len(x['data']) for x in self.uploads.values()) + len(data) > MAX_UPLOADS_BYTES:
                raise APIError('待运行文件已达到本机缓存上限，请移除旧文件后重试。', 'capacity', 429)
            token = secrets.token_urlsafe(24)
            self.uploads[token] = {'data': data, 'summary': summary, 'stored_at': time.time()}
        return {'upload_id': token, 'summary': summary, 'expires_in_seconds': RETENTION_SECONDS}

    def submit(self, payload):
        species = require_species(payload.get('species'))
        selected = configurations(species, payload.get('configurations'))
        source = payload.get('source')
        if source not in ('example', 'upload'):
            raise APIError('请选择已验证示例或上传单样本。')
        sample_id = require_sample_id(payload.get('sample_id'))
        request_key = payload.get('request_key')
        if not isinstance(request_key, str) or not 8 <= len(request_key) <= 128:
            raise APIError('缺少有效请求标识，请刷新页面后重试。')
        self.cleanup()
        with self.lock:
            if request_key in self.request_keys:
                existing = self.jobs[self.request_keys[request_key]]
                if existing['request'] != payload:
                    raise APIError('同一请求标识不能用于不同输入。', 'request_conflict', 409)
                return self.snapshot(existing['id'])
            if not scientific_runtime_ready() or (species == 'human' and not backend.human_ready()):
                raise APIError('当前环境未就绪。请按本地运行指南配置冻结 Python/R 环境；仍可查看保存示例。', 'runtime_unavailable', 503)
            if sum(x['status'] in ('queued', 'running') for x in self.jobs.values()) >= 8:
                raise APIError('任务队列已满，请等待当前推断完成。', 'queue_full', 429)
            if source == 'example':
                if species == 'human':
                    sample_id='GSM755211'; path=FILES['human-example']
                else:
                    try: info=backend.example_info(payload.get('example_id','GSE128537'))
                    except ValueError as exc: raise APIError(str(exc)) from exc
                    sample_id=info['sample_id']; path=ROOT/info['input']
                data = path.read_bytes()
                summary = validate_input(species, sample_id, path.name, data)
            else:
                if payload.get('contract_confirmed') is not True:
                    raise APIError('请确认样本符合当前参考模型的输入规范。', 'contract_required')
                upload = self.uploads.get(payload.get('upload_id'))
                if not upload:
                    raise APIError('文件缓存已过期或已移除，请重新选择文件。', 'upload_expired', 410)
                summary = upload['summary'].copy()
                if summary['species'] != species or summary['sample_id'] != sample_id:
                    raise APIError('文件校验上下文与当前样本不一致，请重新选择文件。', 'input_changed', 409)
                data = upload['data']
            job_id = secrets.token_urlsafe(18)
            job = {'id': job_id, 'request': dict(payload), 'species': species, 'sample_id': sample_id,
                   'configurations': selected, 'source': source, 'example_id': payload.get('example_id','GSE128537'), 'input_summary': summary,
                   'created_at': now(), 'created_epoch': time.time(), 'status': 'queued', 'phase': 'queued',
                   'events': [], 'result': None, 'error': None}
            self.jobs[job_id] = job
            self.request_keys[request_key] = job_id
            self._event(job, 'queued', '输入检查完成，已进入本机任务队列。')
            self.executor.submit(self._run, job_id, data, summary['suffix'])
            return self.snapshot(job_id)

    def _event(self, job, phase, message):
        job['phase'] = phase
        job['events'].append({'phase': phase, 'message': message, 'at': now()})

    def _run(self, job_id, data, suffix):
        with self.lock:
            job = self.jobs[job_id]
            job['status'], job['started_at'], job['started_epoch'] = 'running', now(), time.time()
            self._event(job, 'inference', '正在执行冻结 CEL → PLM → 模型推断。' if job['species'] == 'human'
                        else '正在应用冻结来源均值、尺度与所选配置，并计算候选分数。')
        try:
            if job['species'] == 'human':
                program = 'BOTH' if len(job['configurations']) == 2 else job['configurations'][0]
                result = backend.run_human(data, suffix, job['sample_id'], program)
            else:
                result = backend.run_macaque(data, suffix, job['sample_id'], job['configurations'])
            if job['source'] == 'example':
                with self.lock:
                    self._event(job, 'verifying', '正在与原保存输出逐类别比较分数、排序与类别轴。')
                result['saved_output_comparison'] = backend.compare_example(result,job['example_id'])
                if job['species'] == 'macaque':
                    backend.add_example_context(result,job['example_id'])
            # Validate JSON before reporting success, keeping original backend result fields intact.
            json.dumps(result, allow_nan=False)
            with self.lock:
                job['result'], job['status'] = result, 'succeeded'
                self._event(job, 'complete', '真实推断完成。结果可查看及下载。')
        except Exception as exc:
            print(f'BrainTrace job {job_id}: {type(exc).__name__}; inference failed, no result returned.', flush=True)
            # No local filesystem, native stdout/stderr, or stack trace in HTTP responses.
            message = '冻结推断未完成，未生成结果。请检查文件完整性、平台与冻结运行环境。'
            if isinstance(exc, ValueError) and '180 seconds' in str(exc):
                message = '推断超过 180 秒，已终止该请求；未生成结果。'
            with self.lock:
                job['status'], job['error'] = 'failed', {'code': 'inference_failed', 'message': message}
                self._event(job, 'error', message)
        finally:
            del data
            with self.lock:
                job['finished_at'], job['finished_epoch'] = now(), time.time()

    def snapshot(self, job_id):
        self.cleanup()
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                raise APIError('任务不存在或已过期。请重新运行；已下载的结果不受影响。', 'job_expired', 404)
            result = {k: v for k, v in job.items() if k not in ('request', 'created_epoch', 'started_epoch', 'finished_epoch')}
            result['elapsed_seconds'] = round((job.get('finished_epoch') or time.time()) - job['created_epoch'], 2)
            result['queue_position'] = sum(x['created_epoch'] < job['created_epoch'] and x['status'] in ('queued', 'running') for x in self.jobs.values()) if job['status'] == 'queued' else 0
            return json.loads(json.dumps(result, allow_nan=False))

    def close(self):
        self.stop_cleanup.set()
        self.cleanup_thread.join(timeout=2)
        self.executor.shutdown(wait=True, cancel_futures=True)


def validate_public_origin(value):
    if value is None:
        return None
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment
            or any(c.isspace() for c in value)):
        raise ValueError('Public origin must be an HTTPS origin without path, credentials or trailing slash.')
    _ = parsed.port
    return value


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, public_origin=None):
        self.public_origin = validate_public_origin(public_origin)
        super().__init__(address, Handler)
        self.store = JobStore()
        self.token = secrets.token_urlsafe(32)

    def server_close(self):
        super().server_close()
        self.store.close()


class Handler(BaseHTTPRequestHandler):
    server_version = 'BrainTraceLocal/1'

    def log_message(self, *_):
        pass

    def respond(self, data, status=200, content_type='application/json; charset=utf-8', filename=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def check_local(self, mutation=False):
        port = self.server.server_port
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        origins = {f'http://{x}' for x in hosts}
        if self.server.public_origin:
            hosts.add(urlsplit(self.server.public_origin).netloc)
            origins.add(self.server.public_origin)
        if self.headers.get('Host') not in hosts:
            raise APIError('请求域名未配置。', 'host_rejected', 403)
        origin = self.headers.get('Origin')
        if origin and origin not in origins:
            raise APIError('请求来源不匹配。', 'origin_rejected', 403)
        if mutation and not secrets.compare_digest(self.headers.get('X-BrainTrace-Token', ''), self.server.token):
            raise APIError('会话已更新，请刷新页面。', 'session_expired', 403)

    def read_body(self, limit):
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            size = -1
        if size < 0 or size > limit:
            raise APIError('请求大小无效或超出限制。', 'file_size', 413)
        self.connection.settimeout(60)
        data = self.rfile.read(size)
        if len(data) != size:
            raise APIError('上传未完成，请重新选择文件。', 'upload_incomplete')
        return data

    def dispatch(self, method):
        try:
            self.check_local(mutation=method != 'GET')
            parsed = urlsplit(self.path)
            path = unquote(parsed.path)
            query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
            if method == 'GET':
                if path == '/api/bootstrap':
                    ready = scientific_runtime_ready()
                    self.respond({'api_version': 2, 'scheme': backend.SCHEME, 'examples': backend.read_json(ROOT/'examples/three_tier/EXAMPLES.json'), 'session_token': self.server.token,
                                  'runtime': {'human': ready and backend.human_ready(), 'macaque': ready},
                                  'human_labels': backend.read_json(ROOT / 'metadata/human_labels.json'),
                                  'retention_minutes': RETENTION_SECONDS // 60,
                                  'input_formats': (ROOT / 'docs/INPUT_FORMATS.md').read_text(encoding='utf-8'),
                                  'model_card': (ROOT / 'docs/MODEL_CARD.md').read_text(encoding='utf-8')})
                elif path == '/api/examples':
                    species = require_species(query.get('species'))
                    selected = configurations(species, query.get('configurations', '').split(','))
                    result=backend.saved_example(species, selected,query.get('example_id','GSE128537'))
                    if query.get('format')=='csv':
                        self.respond(backend.result_csv(result).encode('utf-8'),content_type='text/csv; charset=utf-8',filename='braintrace_saved_scores.csv')
                    else:self.respond(result)
                elif path.startswith('/api/jobs/'):
                    job_id=path.removeprefix('/api/jobs/').removesuffix('/scores.csv')
                    job=self.server.store.snapshot(job_id)
                    if path.endswith('/scores.csv'):
                        if job['status']!='succeeded':raise APIError('Result is not available.', 'result_unavailable',409)
                        self.respond(backend.result_csv(job['result']).encode('utf-8'),content_type='text/csv; charset=utf-8',filename='braintrace_live_scores.csv')
                    else:self.respond(job)
                elif path.startswith('/api/files/'):
                    key=path.removeprefix('/api/files/')
                    file = FILES.get(key) or resource_files().get(key)
                    if not file or not file.is_file():
                        raise APIError('文件不存在。', 'not_found', 404)
                    self.respond(file.read_bytes(), content_type='application/octet-stream', filename=file.name)
                elif path in ('/', '/index.html', '/app.js', '/styles.css', '/favicon.svg', '/resources.html', '/resources.js'):
                    file = ROOT / 'web' / ('index.html' if path == '/' else path[1:])
                    self.respond(file.read_bytes(), content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                else:
                    raise APIError('地址不存在。', 'not_found', 404)
            elif method == 'POST' and path == '/api/uploads':
                species = require_species(query.get('species'))
                data = self.read_body((80 if species == 'human' else 8) * 1024**2)
                self.respond(self.server.store.upload(species, query.get('sample_id'), query.get('filename'), data), 201)
            elif method == 'POST' and path == '/api/jobs':
                try:
                    payload = json.loads(self.read_body(16 * 1024))
                    if not isinstance(payload, dict):
                        raise ValueError()
                except (ValueError, UnicodeError):
                    raise APIError('请求必须为 JSON 对象。')
                self.respond(self.server.store.submit(payload), 202)
            elif method == 'DELETE' and path.startswith('/api/uploads/'):
                with self.server.store.lock:
                    self.server.store.uploads.pop(path.removeprefix('/api/uploads/'), None)
                self.respond({'removed': True})
            else:
                raise APIError('接口不存在。', 'not_found', 404)
        except APIError as exc:
            self.respond({'error': {'code': exc.code, 'message': str(exc), 'detail': exc.detail}}, exc.status)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.respond({'error': {'code': 'server_error', 'message': '本地服务处理失败，请检查启动终端或重新启动服务。'}}, 500)

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def do_DELETE(self):
        self.dispatch('DELETE')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--public-origin', help='Exact HTTPS origin served by a local reverse proxy, e.g. https://demo.example.org')
    args = parser.parse_args()
    try:
        validate_public_origin(args.public_origin)
    except ValueError as exc:
        parser.error(str(exc))
    if not (ROOT/'science/lower/BEAMS.json').is_file() or not (ROOT/'examples/three_tier/EXAMPLES.json').is_file():
        parser.error('Runtime assets are absent. Use tools/prepare_runtime.py with the separately supplied runtime_assets directory.')
    with PreviewServer(('127.0.0.1', args.port), public_origin=args.public_origin) as server:
        print(f'BrainTrace local preview: http://127.0.0.1:{server.server_port}', flush=True)
        print('One inference worker; frozen models; Ctrl+C to stop.', flush=True)
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            pass
