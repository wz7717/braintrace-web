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
import os
import sys
import tempfile
from pathlib import Path
from anonymous_sessions import APIError, AnonymousSessions, QueuePolicy, client_ip
from queued_jobs import JobStore
from process_jobs import ProcessRunner
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

    def __init__(self, address, public_origin=None, policy=None, runner=None, work_root=None, trust_proxy=False):
        self.public_origin = validate_public_origin(public_origin)
        if trust_proxy and not self.public_origin:
            raise ValueError('Trusted proxy headers require an explicit public HTTPS origin.')
        self.trust_proxy = trust_proxy
        self.policy = policy or QueuePolicy()
        self.slots = threading.BoundedSemaphore(self.policy.http_connections)
        super().__init__(address, Handler)
        self.sessions = AnonymousSessions(self.policy, self.public_origin)
        if not self.public_origin:
            self.sessions.cookie_name += '_' + str(self.server_port)
        if runner is None:
            base = work_root or os.environ.get('BRAINTRACE_WORK_ROOT')
            if not base:
                base = Path(backend.legacy.runtime_config().get('temp_root') or tempfile.gettempdir())/'braintrace_anonymous'
            runner = ProcessRunner(ROOT, base)
        self.store = JobStore(sys.modules[__name__], self.sessions, self.policy, runner)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            try:
                request.settimeout(1)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def server_close(self):
        super().server_close()
        if hasattr(self, 'store'):
            self.store.close()


class Handler(BaseHTTPRequestHandler):
    server_version = 'BrainTraceQueue/1'

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_):
        pass

    def respond(self, data, status=200, content_type='application/json; charset=utf-8', filename=None, cookie=None):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Vary', 'Cookie')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def check_local(self):
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
        self.ip = client_ip(self.headers, self.client_address[0], self.server.public_origin, self.server.trust_proxy)

    def session(self, create=False, mutation=False):
        self.server.store.cleanup()
        owner, csrf, cookie = self.server.sessions.resolve(self.headers.get('Cookie'), self.ip, create=create)
        if mutation:
            self.server.sessions.mutation(owner, self.ip, self.headers.get('X-BrainTrace-Token', ''))
        return owner, csrf, cookie

    def read_length(self, limit):
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
            raise APIError('需要明确且唯一的文件大小。', 'file_size', 400)
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            size = -1
        if size < 0 or size > limit:
            raise APIError('请求大小无效或超出限制。', 'file_size', 413)
        return size

    def read_body(self, limit):
        size = self.read_length(limit)
        deadline = time.monotonic() + self.server.policy.body_timeout_seconds
        chunks, remaining = [], size
        while remaining:
            seconds = deadline - time.monotonic()
            if seconds <= 0:
                raise TimeoutError('Body deadline reached.')
            self.connection.settimeout(seconds)
            block = self.rfile.read1(min(remaining, 64 * 1024))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        data = b''.join(chunks)
        if len(data) != size:
            raise APIError('上传未完成，请重新选择文件。', 'upload_incomplete')
        return data

    def dispatch(self, method):
        try:
            self.check_local()
            parsed = urlsplit(self.path)
            path = unquote(parsed.path)
            query = {k:v[-1] for k,v in parse_qs(parsed.query).items()}
            owner = self.session(mutation=True)[0] if method != 'GET' else None
            if method == 'GET':
                if path == '/api/bootstrap':
                    owner, csrf, cookie = self.session(create=True)
                    ready = scientific_runtime_ready() and self.server.store.runner.healthy
                    human_path = getattr(self.server.store.runner, 'work_root', Path('local'))
                    self.respond({'api_version':3, 'scheme':backend.SCHEME,
                        'examples':backend.read_json(ROOT/'examples/three_tier/EXAMPLES.json'), 'session_token':csrf,
                        'anonymous_session':True, 'limits':self.server.policy.public(), 'usage':self.server.store.usage(owner),
                        'runtime':{'human':ready and backend.human_ready() and str(human_path).isascii(), 'macaque':ready},
                        'human_labels':backend.read_json(ROOT/'metadata/human_labels.json'),
                        'retention_minutes':self.server.policy.retention_seconds // 60,
                        'input_formats':(ROOT/'docs/INPUT_FORMATS.md').read_text(encoding='utf-8'),
                        'model_card':(ROOT/'docs/MODEL_CARD.md').read_text(encoding='utf-8')}, cookie=cookie)
                elif path == '/api/examples':
                    species = require_species(query.get('species'))
                    selected = configurations(species, query.get('configurations', '').split(','))
                    result = backend.saved_example(species, selected, query.get('example_id','GSE128537'))
                    if query.get('format') == 'csv':
                        self.respond(backend.result_csv(result).encode('utf-8'), content_type='text/csv; charset=utf-8', filename='braintrace_saved_scores.csv')
                    else:
                        self.respond(result)
                elif path.startswith('/api/jobs/'):
                    owner = self.session()[0]
                    job_id = path.removeprefix('/api/jobs/').removesuffix('/scores.csv')
                    job = self.server.store.snapshot(owner, job_id)
                    if path.endswith('/scores.csv'):
                        if job['status'] != 'succeeded':
                            raise APIError('结果尚不可用。', 'result_unavailable', 409)
                        self.respond(backend.result_csv(job['result']).encode('utf-8'), content_type='text/csv; charset=utf-8', filename='braintrace_live_scores.csv')
                    else:
                        self.respond(job)
                elif path.startswith('/api/files/'):
                    key = path.removeprefix('/api/files/')
                    file = FILES.get(key) or resource_files().get(key)
                    if not file or not file.is_file():
                        raise APIError('文件不存在。', 'not_found', 404)
                    self.respond(file.read_bytes(), content_type='application/octet-stream', filename=file.name)
                elif path in ('/', '/index.html', '/app.js', '/styles.css', '/favicon.svg', '/resources.html', '/resources.js'):
                    file = ROOT/'web'/('index.html' if path == '/' else path[1:])
                    self.respond(file.read_bytes(), content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                else:
                    raise APIError('地址不存在。', 'not_found', 404)
            elif method == 'POST' and path == '/api/uploads':
                species = require_species(query.get('species'))
                limit = (80 if species == 'human' else 8)*1024**2
                size = self.read_length(limit)
                with self.server.store.upload_slot(owner, self.ip, size) as ticket:
                    data = self.read_body(limit)
                    upload = self.server.store.upload(owner, species, query.get('sample_id'), query.get('filename'), data, ticket)
                self.respond(upload, 201)
            elif method == 'POST' and path == '/api/jobs':
                try:
                    payload = json.loads(self.read_body(16*1024))
                    if not isinstance(payload, dict):
                        raise ValueError()
                except (ValueError, UnicodeError):
                    raise APIError('请求必须为 JSON 对象。')
                self.respond(self.server.store.submit(owner, self.ip, payload), 202)
            elif method == 'DELETE' and path.startswith('/api/uploads/'):
                self.server.store.remove_upload(owner, path.removeprefix('/api/uploads/'))
                self.respond({'removed':True})
            else:
                raise APIError('接口不存在。', 'not_found', 404)
        except APIError as exc:
            self.respond({'error':{'code':exc.code,'message':str(exc),'detail':exc.detail}}, exc.status)
        except TimeoutError:
            self.respond({'error':{'code':'upload_timeout','message':'上传超时，缓存预留已释放。'}}, 408)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.respond({'error':{'code':'server_error','message':'服务未完成请求，请稍后重试。'}}, 500)

    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_DELETE(self): self.dispatch('DELETE')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--public-origin', help='Exact HTTPS origin served by a local reverse proxy.')
    parser.add_argument('--trust-proxy-client-ip', action='store_true', help='Require the local proxy to overwrite X-BrainTrace-Client-IP.')
    parser.add_argument('--queue-config', type=Path, help='Private server quota overrides; see queue.example.json.')
    parser.add_argument('--work-root', type=Path, help='Private job workspace root; ASCII path required for live CEL.')
    args = parser.parse_args()
    try:
        validate_public_origin(args.public_origin)
        policy = QueuePolicy.from_file(args.queue_config)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if not (ROOT/'science/lower/BEAMS.json').is_file() or not (ROOT/'examples/three_tier/EXAMPLES.json').is_file():
        parser.error('Runtime assets are absent. Assemble code with the separately supplied runtime_assets.')
    with PreviewServer(('127.0.0.1', args.port), public_origin=args.public_origin, policy=policy,
                       work_root=args.work_root, trust_proxy=args.trust_proxy_client_ip) as server:
        print(f'BrainTrace anonymous queue: http://127.0.0.1:{server.server_port}', flush=True)
        print('One process job at a time; no login; per-session ownership and quotas. Ctrl+C to stop.', flush=True)
        try:
            server.serve_forever(poll_interval=.5)
        except KeyboardInterrupt:
            pass
