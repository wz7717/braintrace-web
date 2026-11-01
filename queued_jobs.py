"""FIFO single-worker queue with session ownership, quotas and finite lifetimes."""
from collections import deque
from contextlib import contextmanager
import json
import secrets
import threading
import time

from anonymous_sessions import APIError
from process_jobs import JobFailure


ACTIVE = ('queued', 'running')

class JobStore:
    def __init__(self, api, sessions, policy, runner, clock=time.monotonic):
        self.api, self.sessions, self.policy, self.runner, self.clock = api, sessions, policy, runner, clock
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.uploads, self.reservations, self.jobs, self.request_keys = {}, {}, {}, {}
        self.queue, self.closed = deque(), False
        self.stop_cleanup = threading.Event()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True, name='anonymous-fifo-worker')
        self.cleaner = threading.Thread(target=self._cleanup_loop, daemon=True, name='anonymous-expiry')
        self.worker.start(); self.cleaner.start()

    def _cleanup_loop(self):
        while not self.stop_cleanup.wait(1):
            self.cleanup()

    def _event(self, job, phase, message):
        job['phase'] = phase
        job['events'].append({'phase': phase, 'message': message, 'at': self.api.now()})

    def _finish(self, job, result=None, error=None):
        job.pop('data', None)
        job['result'], job['error'] = result, error
        job['status'] = 'failed' if error else 'succeeded'
        job['finished_at'], job['finished_epoch'] = self.api.now(), self.clock()
        self._event(job, 'error' if error else 'complete', error['message'] if error else '真实推断完成。结果仅供当前匿名会话查看及下载。')

    def cleanup(self):
        expired = self.sessions.sweep()
        current = self.clock()
        with self.changed:
            self.uploads = {k: v for k, v in self.uploads.items()
                if v['owner'] not in expired and current - v['stored_at'] < self.policy.retention_seconds}
            self.reservations = {k: v for k, v in self.reservations.items()
                if v['owner'] not in expired and current - v['stored_at'] < self.policy.body_timeout_seconds + 30}
            for job in self.jobs.values():
                if job['status'] not in ACTIVE:
                    continue
                if job['owner'] in expired:
                    job['cancel'].set()
                    if job['status'] == 'queued':
                        self._finish(job, error={'code':'session_expired','message':'匿名会话已过期，排队任务已移除。'})
                elif job['status'] == 'queued' and current - job['created_epoch'] >= self.policy.queue_timeout_seconds:
                    self._finish(job, error={'code':'queue_timeout','message':'排队超过时间上限，未启动推断；可以重新提交。'})
            self.jobs = {k: v for k, v in self.jobs.items() if v['status'] in ACTIVE
                         or current - v['finished_epoch'] < self.policy.retention_seconds}
            self.request_keys = {k: v for k, v in self.request_keys.items() if v in self.jobs}
            self.queue = deque(k for k in self.queue if k in self.jobs and self.jobs[k]['status'] == 'queued')

    def _require_owner(self, owner):
        if self.closed:
            raise APIError('服务正在关闭，请稍后重试。', 'service_closing', 503)
        if not self.sessions.alive(owner):
            raise APIError('匿名会话已过期，请刷新页面。', 'session_expired', 401)

    def _bytes(self, owner=None):
        entries = list(self.uploads.values()) + list(self.reservations.values())
        total = sum(v.get('bytes', len(v.get('data', b''))) for v in entries if owner is None or v['owner'] == owner)
        total += sum(len(v.get('data', b'')) for v in self.jobs.values() if owner is None or v['owner'] == owner)
        return total

    def _check_bytes(self, owner, size):
        if self._bytes(owner) + size > self.policy.input_bytes_per_session:
            raise APIError('当前匿名会话的输入缓存已满，请移除旧文件或等待任务结束。', 'session_capacity', 429)
        if self._bytes() + size > self.policy.input_bytes_global:
            raise APIError('服务输入缓存已满，请稍后重试。', 'capacity', 429)

    @contextmanager
    def upload_slot(self, owner, ip, size):
        """Reserve quota BEFORE reading an HTTP body or validating its contents."""
        self.cleanup()
        self.sessions.rates.take_many([(('uploads', owner), self.policy.uploads_per_session_minute, 60)])
        with self.lock:
            self._require_owner(owner)
            entries = list(self.uploads.values()) + list(self.reservations.values())
            if sum(v['owner'] == owner for v in entries) >= self.policy.uploads_per_session:
                raise APIError('当前匿名会话最多保留两个待运行文件。', 'upload_quota', 429)
            if len(entries) >= self.policy.uploads_global:
                raise APIError('服务上传缓存已满，请稍后重试。', 'capacity', 429)
            self._check_bytes(owner, size)
            ticket = secrets.token_urlsafe(18)
            self.reservations[ticket] = {'owner':owner,'ip':ip,'bytes':size,'stored_at':self.clock()}
        try:
            yield ticket
        finally:
            with self.lock:
                self.reservations.pop(ticket, None)

    def upload(self, owner, species, sample_id, filename, data, ticket):
        summary = self.api.validate_input(species, sample_id, filename, data)
        with self.lock:
            self._require_owner(owner)
            reservation = self.reservations.get(ticket)
            if not reservation or reservation['owner'] != owner or reservation['bytes'] != len(data):
                raise APIError('上传预留已过期，请重新上传。', 'upload_expired', 410)
            token = secrets.token_urlsafe(24)
            self.uploads[token] = {'owner':owner,'data':data,'summary':summary,'stored_at':self.clock()}
            del self.reservations[ticket]
        return {'upload_id':token,'summary':summary,'expires_in_seconds':self.policy.retention_seconds}

    def remove_upload(self, owner, token):
        with self.lock:
            entry = self.uploads.get(token)
            if not entry or entry['owner'] != owner:
                raise APIError('文件不存在或已过期。', 'upload_expired', 404)
            del self.uploads[token]

    def submit(self, owner, ip, payload):
        species = self.api.require_species(payload.get('species'))
        selected = self.api.configurations(species, payload.get('configurations'))
        sample_id = self.api.require_sample_id(payload.get('sample_id'))
        source, key = payload.get('source'), payload.get('request_key')
        if source not in ('example', 'upload'):
            raise APIError('请选择已验证示例或上传单样本。')
        if not isinstance(key, str) or not 8 <= len(key) <= 128:
            raise APIError('缺少有效请求标识，请刷新页面后重试。')
        self.cleanup()
        with self.changed:
            self._require_owner(owner)
            previous = self.request_keys.get((owner, key))
            if previous:
                job = self.jobs[previous]
                if job['request'] != payload:
                    raise APIError('同一请求标识不能用于不同输入。', 'request_conflict', 409)
                return self.snapshot(owner, previous)
            active = [v for v in self.jobs.values() if v['status'] in ACTIVE]
            if sum(v['owner'] == owner for v in active) >= self.policy.active_jobs_per_session:
                raise APIError('当前匿名会话已有排队或运行任务，请等待完成。', 'session_job_quota', 429)
            if sum(v['ip'] == ip for v in active) >= self.policy.active_jobs_per_ip:
                raise APIError('当前网络的活动任务已达上限，请稍后重试。', 'ip_job_quota', 429)
            if len(active) >= self.policy.active_jobs_global:
                raise APIError('任务队列已满，请稍后重试。', 'queue_full', 429)
            if len(self.jobs) >= self.policy.stored_jobs_global:
                raise APIError('服务结果缓存已满，请稍后重试。', 'capacity', 429)
            if not self.runner.healthy or not self.api.scientific_runtime_ready() or (species == 'human' and not self.api.backend.human_ready()):
                raise APIError('冻结运行环境或计算服务暂不可用。', 'runtime_unavailable', 503)
            if source == 'upload':
                if payload.get('contract_confirmed') is not True:
                    raise APIError('请确认样本符合输入规范。', 'contract_required')
                token = payload.get('upload_id')
                entry = self.uploads.get(token) if isinstance(token, str) else None
                if not entry or entry['owner'] != owner:
                    raise APIError('文件不存在或已过期。', 'upload_expired', 404)
                summary, data = entry['summary'].copy(), entry['data']
                if summary['species'] != species or summary['sample_id'] != sample_id:
                    raise APIError('文件校验上下文与当前样本不一致。', 'input_changed', 409)
            else:
                if species == 'human':
                    path, sample_id = self.api.FILES['human-example'], 'GSM755211'
                else:
                    try:
                        info = self.api.backend.example_info(payload.get('example_id', 'GSE128537'))
                    except (ValueError, TypeError) as exc:
                        raise APIError('示例不存在。') from exc
                    path, sample_id = self.api.ROOT/info['input'], info['sample_id']
                self._check_bytes(owner, path.stat().st_size)
                data = path.read_bytes()
                summary = self.api.validate_input(species, sample_id, path.name, data)
            self.sessions.rates.take_many([
                (('jobs', owner), self.policy.jobs_per_session_half_hour, 1800),
                (('ip-jobs', ip), self.policy.jobs_per_ip_half_hour, 1800)])
            job_id = secrets.token_urlsafe(18)
            job = {'id':job_id,'owner':owner,'ip':ip,'request':dict(payload),'data':data,'cancel':threading.Event(),
                'species':species,'sample_id':sample_id,'configurations':selected,'source':source,
                'example_id':payload.get('example_id','GSE128537'),'input_summary':summary,
                'created_at':self.api.now(),'created_epoch':self.clock(),'status':'queued','phase':'queued',
                'events':[],'result':None,'error':None}
            self.jobs[job_id] = job
            self.request_keys[(owner, key)] = job_id
            if source == 'upload':
                del self.uploads[token]  # Transfer the one buffer to the job; no duplicate quota accounting.
            self.queue.append(job_id)
            self._event(job, 'queued', '输入检查完成，已进入单机任务队列。')
            self.changed.notify()
            return self.snapshot(owner, job_id)

    def _worker_loop(self):
        while True:
            with self.changed:
                self.changed.wait_for(lambda: self.closed or self.queue)
                if self.closed:
                    return
                job_id = self.queue.popleft()
                job = self.jobs.get(job_id)
                if not job or job['status'] != 'queued':
                    continue
                if not self.sessions.alive(job['owner']):
                    self._finish(job, error={'code':'session_expired','message':'匿名会话已过期，未启动推断。'})
                    continue
                if self.clock() - job['created_epoch'] >= self.policy.queue_timeout_seconds:
                    self._finish(job, error={'code':'queue_timeout','message':'排队超过时间上限，未启动推断；可以重新提交。'})
                    continue
                job['status'], job['started_at'], job['started_epoch'] = 'running', self.api.now(), self.clock()
                self._event(job, 'inference', '正在独立进程中执行冻结推断。')
                spec = {k:job[k] for k in ('species','sample_id','configurations','source','example_id')}
                spec['suffix'] = job['input_summary']['suffix']
                timeout = self.policy.human_timeout_seconds if job['species'] == 'human' else self.policy.macaque_timeout_seconds
            try:
                result = self.runner.run(spec, job['data'], timeout, job['cancel'])
                with self.lock:
                    self._finish(job, result=result)
            except Exception as exc:
                code = exc.code if isinstance(exc, JobFailure) else 'worker_failed'
                message = str(exc) if isinstance(exc, JobFailure) else '计算进程未正常完成，队列将继续处理下一任务。'
                with self.lock:
                    self._finish(job, error={'code':code,'message':message})

    def snapshot(self, owner, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job['owner'] != owner:
                raise APIError('任务不存在或已过期。', 'job_expired', 404)
            excluded = ('owner','ip','request','data','cancel','created_epoch','started_epoch','finished_epoch')
            result = {k:v for k,v in job.items() if k not in excluded}
            result['elapsed_seconds'] = round((job.get('finished_epoch') or self.clock()) - job['created_epoch'], 2)
            result['queue_position'] = sum(v['created_epoch'] < job['created_epoch'] and v['status'] in ACTIVE
                for v in self.jobs.values()) if job['status'] == 'queued' else 0
            return json.loads(json.dumps(result, allow_nan=False))

    def usage(self, owner):
        with self.lock:
            return {'active_jobs':sum(v['owner'] == owner and v['status'] in ACTIVE for v in self.jobs.values()),
                    'pending_uploads':sum(v['owner'] == owner for v in self.uploads.values())}

    def close(self):
        self.stop_cleanup.set()
        with self.changed:
            self.closed = True
            for job in self.jobs.values():
                if job['status'] in ACTIVE:
                    job['cancel'].set()
                    if job['status'] == 'queued':
                        self._finish(job, error={'code':'service_closing','message':'服务关闭，未启动推断。'})
            self.changed.notify_all()
        self.cleaner.join(timeout=2)
        self.worker.join(timeout=10)
        if self.worker.is_alive():
            raise RuntimeError('Worker did not stop after bounded process cancellation.')
        with self.lock:
            self.uploads.clear(); self.reservations.clear(); self.jobs.clear(); self.request_keys.clear()
