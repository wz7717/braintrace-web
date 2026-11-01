"""Bounded child-process lifetime, including descendant Python/R processes."""
from pathlib import Path
import ctypes
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time


class JobFailure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class WindowsJob:
    def __init__(self, pid):
        from ctypes import wintypes as w
        size = ctypes.c_size_t
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', w.DWORD), ('min_working', size), ('max_working', size),
                        ('active', w.DWORD), ('affinity', size), ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', IO), ('process_memory', size), ('job_memory', size),
                        ('peak_process_memory', size), ('peak_job_memory', size)]
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]; k.CreateJobObjectW.restype = w.HANDLE
        k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]; k.SetInformationJobObject.restype = w.BOOL
        k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]; k.OpenProcess.restype = w.HANDLE
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]; k.AssignProcessToJobObject.restype = w.BOOL
        k.CloseHandle.argtypes = [w.HANDLE]; k.CloseHandle.restype = w.BOOL
        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            limits = Extended(); limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not k.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            process = k.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE
            if not process:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not k.AssignProcessToJobObject(self.handle, process):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                k.CloseHandle(process)
        except Exception:
            self.close()
            raise

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class ProcessRunner:
    def __init__(self, root, work_root, python=None, worker=None):
        self.root = Path(root).resolve()
        self.work_root = Path(work_root).resolve()
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.python = python or sys.executable
        self.worker = Path(worker or self.root/'inference_worker.py').resolve()
        self.healthy = True

    def run(self, spec, data, timeout, cancel):
        if not self.healthy:
            raise JobFailure('worker_unavailable', '任务清理未完成，服务暂不接受新的计算。')
        work = Path(tempfile.mkdtemp(prefix='job_', dir=self.work_root)).resolve()
        # Only this freshly allocated child directory can be removed in finally.
        if work.parent != self.work_root:
            raise RuntimeError('Unexpected work directory.')
        process = guard = None
        try:
            (work/'request.json').write_text(json.dumps(spec), encoding='utf-8')
            (work/'input.bin').write_bytes(data)
            env = os.environ.copy()
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            env['TMP'] = env['TEMP'] = env['TMPDIR'] = str(work)
            process = subprocess.Popen([self.python, '-X', 'utf8', '-B', str(self.worker), '--work', str(work)],
                cwd=self.root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, close_fds=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                start_new_session=os.name != 'nt')
            if os.name == 'nt':
                guard = WindowsJob(process.pid)
            (work/'START').touch()
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if cancel.wait(.05):
                    raise JobFailure('task_cancelled', '任务已结束：会话过期或服务正在关闭。')
                if time.monotonic() >= deadline:
                    raise JobFailure('task_timeout', '推断达到时间上限，已终止该任务；可以重新提交。')
            response = work/'response.json'
            if process.returncode or not response.is_file() or response.stat().st_size > 2 * 1024**2:
                raise JobFailure('worker_failed', '计算进程未正常完成，队列将继续处理下一任务。')
            result = json.loads(response.read_text(encoding='utf-8'))
            if not result.get('ok'):
                raise JobFailure('inference_failed', '冻结推断未完成，请检查样本格式与运行环境。')
            json.dumps(result['result'], allow_nan=False)
            return result['result']
        finally:
            if guard:
                guard.close()  # Also reaps children if the root process already exited.
            elif process is not None and os.name != 'nt':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process is not None:
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    self.healthy = False
                    raise JobFailure('cleanup_failed', '计算进程未能回收，服务暂停新的计算。') from exc
            for attempt in range(20):
                try:
                    if work.parent != self.work_root or not work.name.startswith('job_'):
                        raise RuntimeError('Unexpected cleanup target.')
                    shutil.rmtree(work)
                    break
                except (PermissionError, OSError):
                    if attempt == 19:
                        self.healthy = False
                        raise JobFailure('cleanup_failed', '任务临时文件未能清理，服务暂停新的计算。')
                    time.sleep(.1)
