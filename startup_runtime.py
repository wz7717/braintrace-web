"""Observable, single-flight startup. Never reads uploads or runs predictions."""
from collections import deque
from pathlib import Path
import os
import re
import signal
import subprocess
import threading
import time

STAGES = ('cache', 'r', 'r_packages', 'python', 'verify', 'assets', 'ready')

def safe_log(line):
    """Only installation output is published; redact credentials and home paths."""
    line = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', str(line))
    line = re.sub(r'(https?://)[^/\s@]+@', r'\1[redacted]@', line)
    line = re.sub(r'(?i)(token|password|secret|api_key)([=: ]+)[^\s&]+', r'\1\2[redacted]', line)
    return line.replace(str(Path.home()), '<home>').rstrip()[:1500]

def run_logged(command, log_path, report, timeout=1800, env=None):
    """Stream build output while enforcing a wall-clock process-group timeout."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as log:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', env=env,
            start_new_session=os.name == 'posix')
        def read_output():
            for line in process.stdout:
                clean = safe_log(line)
                log.write(clean+'\n'); log.flush()
                print(clean, flush=True)
                if clean.startswith('[braintrace:stage] '):
                    stage = clean.split(' ', 1)[1].strip()
                    report(stage if stage in STAGES else None, clean)
                else:
                    report(None, clean)
            process.stdout.close()
        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'posix': os.killpg(process.pid, signal.SIGKILL)
            else: process.kill()
            process.wait(); reader.join(timeout=3)
            raise RuntimeError(f'Dependency setup exceeded {timeout} seconds; stopped. Completed components are cached.') from None
        reader.join(timeout=3)
        if code:
            if os.name == 'posix':
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            raise RuntimeError(f'Dependency setup exited with code {code}. See the installation log below.')

class StartupManager:
    """Shared across sessions and language switches; failures never auto-loop."""
    def __init__(self, builder, retry_delay=60):
        self.builder, self.retry_delay = builder, retry_delay
        self.lock = threading.RLock()
        self.state, self.stage = 'idle', 'cache'
        self.lines = deque(maxlen=160)
        self.started = self.finished = self.updated = 0.0
        self.value, self.error = None, ''
    def report(self, stage=None, line=''):
        with self.lock:
            if stage in STAGES: self.stage = stage
            if line: self.lines.append(safe_log(line))
            self.updated = time.monotonic()
    def start(self, retry=False):
        with self.lock:
            if self.state in ('running', 'ready'): return False
            if self.state == 'failed' and (not retry or time.monotonic()-self.finished < self.retry_delay): return False
            self.state, self.stage = 'running', 'cache'
            self.started = self.updated = time.monotonic()
            self.finished, self.error = 0, ''
            self.lines.clear()
            threading.Thread(target=self._build, name='braintrace-startup', daemon=True).start()
            return True
    def _build(self):
        try:
            value = self.builder(self.report)
            with self.lock:
                self.value, self.state, self.stage = value, 'ready', 'ready'
                self.finished = self.updated = time.monotonic()
        except Exception as exc:
            with self.lock:
                self.error = safe_log(str(exc)); self.lines.append(self.error)
                self.state = 'failed'
                self.finished = self.updated = time.monotonic()
    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            elapsed = (self.finished or now)-self.started if self.started else 0
            return dict(state=self.state, stage=self.stage, elapsed=int(elapsed),
                quiet_seconds=int(now-self.updated) if self.updated else 0,
                log='\n'.join(self.lines), error=self.error,
                retry_in=max(0, int(self.retry_delay-(now-self.finished))+1) if self.state=='failed' else 0)
