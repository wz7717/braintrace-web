"""Anonymous browser sessions and bounded, in-memory rate counters. No model code."""
from collections import deque
from dataclasses import asdict, dataclass
from hashlib import sha256
from http.cookies import SimpleCookie, CookieError
import ipaddress
import json
import re
import secrets
import threading
import time


class APIError(Exception):
    def __init__(self, message, code='invalid_request', status=400, detail=None):
        super().__init__(message)
        self.code, self.status, self.detail = code, status, detail


@dataclass(frozen=True)
class QueuePolicy:
    session_idle_seconds: int = 1800
    session_absolute_seconds: int = 7200
    retention_seconds: int = 1800
    max_sessions: int = 1000
    new_sessions_per_ip_hour: int = 10
    uploads_per_session_minute: int = 10
    mutations_per_session_minute: int = 30
    mutations_per_ip_minute: int = 90
    jobs_per_session_half_hour: int = 4
    jobs_per_ip_half_hour: int = 12
    active_jobs_per_session: int = 1
    active_jobs_per_ip: int = 3
    active_jobs_global: int = 8
    uploads_per_session: int = 2
    uploads_global: int = 16
    input_bytes_per_session: int = 96 * 1024**2
    input_bytes_global: int = 160 * 1024**2
    stored_jobs_global: int = 128
    queue_timeout_seconds: int = 900
    macaque_timeout_seconds: int = 120
    human_timeout_seconds: int = 240
    http_connections: int = 16
    body_timeout_seconds: int = 60

    @classmethod
    def from_file(cls, path):
        if path is None:
            return cls()
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ValueError('Unknown queue policy fields.')
        if any(type(v) is not int or v <= 0 for v in data.values()):
            raise ValueError('Queue policy values must be positive integers.')
        return cls(**data)

    def public(self):
        fields = ('retention_seconds', 'active_jobs_per_session', 'active_jobs_global',
                  'uploads_per_session', 'jobs_per_session_half_hour',
                  'queue_timeout_seconds', 'macaque_timeout_seconds', 'human_timeout_seconds')
        values = asdict(self)
        return {k: values[k] for k in fields}


class RateLimits:
    def __init__(self, clock=time.monotonic):
        self.clock, self.items, self.lock = clock, {}, threading.RLock()

    def take_many(self, rules):
        """Check all quotas before charging any; counters have bounded key cardinality."""
        with self.lock:
            current = self.clock()
            self.items = {k: v for k, v in self.items.items() if v[0] and v[0][-1] + v[1] > current}
            if len(self.items) + sum(k not in self.items for k, _, _ in rules) > 8192:
                raise APIError('服务繁忙，请稍后重试。', 'rate_limit', 429)
            pending = []
            for key, maximum, window in rules:
                times, _ = self.items.get(key, (deque(), window))
                while times and times[0] <= current - window:
                    times.popleft()
                if len(times) >= maximum:
                    raise APIError('请求过于频繁，请稍后重试。', 'rate_limit', 429)
                pending.append((key, times, window))
            for key, times, window in pending:
                times.append(current)
                self.items[key] = (times, window)


class AnonymousSessions:
    def __init__(self, policy, public_origin=None, clock=time.monotonic):
        self.policy, self.public_origin, self.clock = policy, public_origin, clock
        self.cookie_name = '__Host-BrainTraceSession' if public_origin else 'BrainTraceLocalSession'
        self.sessions, self.lock = {}, threading.RLock()
        self.rates = RateLimits(clock)

    def parse(self, header):
        if not header or len(header) > 4096:
            return None
        try:
            cookies = SimpleCookie(); cookies.load(header)
            value = cookies[self.cookie_name].value
        except (CookieError, KeyError):
            return None
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
            return None
        return sha256(value.encode('ascii')).hexdigest()

    def expired(self, entry, current):
        return (current - entry['seen'] >= self.policy.session_idle_seconds or
                current - entry['created'] >= self.policy.session_absolute_seconds)

    def sweep(self):
        with self.lock:
            current = self.clock()
            expired = {k for k, v in self.sessions.items() if self.expired(v, current)}
            for key in expired:
                del self.sessions[key]
            return expired

    def resolve(self, cookie_header, ip, *, create=False):
        owner, current = self.parse(cookie_header), self.clock()
        with self.lock:
            entry = self.sessions.get(owner)
            if entry is not None and not self.expired(entry, current):
                entry['seen'] = current
                return owner, entry['csrf'], None
            if not create:
                raise APIError('匿名会话已过期，请刷新页面。', 'session_expired', 401)
            # Expired entries are removed by sweep so JobStore can also cancel their work.
            if len(self.sessions) >= self.policy.max_sessions:
                raise APIError('服务会话已满，请稍后重试。', 'capacity', 503)
            self.rates.take_many([(('new-session', ip), self.policy.new_sessions_per_ip_hour, 3600)])
            raw = secrets.token_urlsafe(32)
            owner = sha256(raw.encode('ascii')).hexdigest()
            entry = {'csrf': secrets.token_urlsafe(32), 'created': current, 'seen': current}
            self.sessions[owner] = entry
            cookie = f'{self.cookie_name}={raw}; HttpOnly; SameSite=Strict; Path=/'
            if self.public_origin:
                cookie += '; Secure'
            return owner, entry['csrf'], cookie

    def alive(self, owner):
        with self.lock:
            entry = self.sessions.get(owner)
            return entry is not None and not self.expired(entry, self.clock())

    def mutation(self, owner, ip, csrf):
        with self.lock:
            entry = self.sessions.get(owner)
            if not entry or not isinstance(csrf, str) or not secrets.compare_digest(entry['csrf'], csrf):
                raise APIError('匿名会话校验失败，请刷新页面。', 'session_rejected', 403)
        self.rates.take_many([
            (('mutations', owner), self.policy.mutations_per_session_minute, 60),
            (('ip-mutations', ip), self.policy.mutations_per_ip_minute, 60)])


def client_ip(headers, peer, public_origin, trust_proxy):
    """Trust only an explicitly configured local proxy's overwritten single-IP header."""
    if trust_proxy and public_origin and headers.get('Host') == public_origin.split('://', 1)[1]:
        value = headers.get('X-BrainTrace-Client-IP', '')
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as exc:
            raise APIError('代理客户端地址未正确配置。', 'proxy_configuration', 503) from exc
    return str(ipaddress.ip_address(peer))
