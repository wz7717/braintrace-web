"""Targeted startup checks using synthetic processes only; no model inference."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from startup_runtime import StartupManager, run_logged, safe_log


def until(predicate):
    end=time.monotonic()+8
    while time.monotonic()<end:
        if predicate(): return
        time.sleep(.02)
    raise AssertionError('Timed out waiting for synthetic startup')

class StartupChecks(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','Linux installer')
    def test_partial_cache_installs_only_missing_package_then_skips_everything(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); prefix=root/'deps'; bins=root/'bin'; bins.mkdir()
            for rel in ('R/bin','worker/bin','rlib'): (prefix/rel).mkdir(parents=True)
            calls=root/'calls'; calls.write_text('')
            for name in ('preprocessCore','affxparser','jsonlite'): (prefix/'rlib'/name).touch()
            def executable(path,body):
                path.write_text('#!'+sys.executable+'\n'+body); path.chmod(0o755)
            executable(prefix/'R/bin/Rscript',
                'import pathlib,sys\np=pathlib.Path('+repr(str(prefix/'rlib'))+')\ns=" ".join(sys.argv)\n'
                'for name in ("preprocessCore","affxparser","digest","jsonlite"):\n'
                ' if "packageVersion(\'"+name+"\')" in s and not (p/name).exists(): sys.exit(1)\n')
            executable(prefix/'R/bin/R',
                'import pathlib,sys\narchive=pathlib.Path(sys.argv[-1]).name\n'
                'name=archive.split("_")[0]\npathlib.Path('+repr(str(prefix/'rlib'))+',name).touch()\n'
                'with open('+repr(str(calls))+',"a") as f: f.write("install "+name+"\\n")\n')
            executable(prefix/'worker/bin/python','pass\n')
            executable(bins/'curl',
                'import pathlib,sys\np=pathlib.Path(sys.argv[sys.argv.index("--output")+1]); p.write_bytes(b"archive fixture")\n'
                'with open('+repr(str(calls))+',"a") as f: f.write("download "+p.name+"\\n")\n')
            for name in ('make','uv'):
                executable(bins/name,'raise SystemExit("Unexpected rebuild")\n')
            env={**os.environ,'PATH':str(bins)+':/usr/bin:/bin'}
            cmd=['bash',str(Path(__file__).resolve().parents[1]/'deployment/setup_linux.sh'),str(prefix)]
            first=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            self.assertEqual(calls.read_text().splitlines(),['download digest_0.6.39.tar.gz.part','install digest'])
            second=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(second.returncode,0,second.stdout+second.stderr)
            self.assertEqual(len(calls.read_text().splitlines()),2)
            self.assertEqual(second.stdout.count('installation skipped'),5)

    def test_one_build_for_concurrent_visitors_and_ready_reuse(self):
        gate=threading.Event(); calls=[]; value=object()
        def build(report):
            calls.append(1); report('r','building'); gate.wait(5); return value
        manager=StartupManager(build)
        threads=[threading.Thread(target=manager.start) for _ in range(12)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(calls),1)
        self.assertEqual(manager.snapshot()['stage'],'r')
        gate.set(); until(lambda:manager.snapshot()['state']=='ready')
        self.assertIs(manager.value,value)
        self.assertFalse(manager.start(retry=True))
        self.assertEqual(len(calls),1)

    def test_failure_is_visible_no_auto_retry_and_explicit_recovery(self):
        calls=[]
        def build(report):
            calls.append(1)
            if len(calls)==1: raise RuntimeError('synthetic install error')
            return 'ready'
        manager=StartupManager(build,retry_delay=0)
        manager.start(); until(lambda:manager.snapshot()['state']=='failed')
        self.assertIn('synthetic install error',manager.snapshot()['log'])
        self.assertFalse(manager.start())
        self.assertTrue(manager.start(retry=True))
        until(lambda:manager.snapshot()['state']=='ready')
        self.assertEqual(len(calls),2)

    def test_retry_cooldown_and_bounded_sanitized_logs(self):
        manager=StartupManager(lambda report:(_ for _ in ()).throw(ValueError('error')))
        manager.start(); until(lambda:manager.snapshot()['state']=='failed')
        self.assertFalse(manager.start(retry=True))
        for i in range(300): manager.report(None,str(i))
        self.assertEqual(len(manager.snapshot()['log'].splitlines()),160)
        line=safe_log('https://user:password@example.org token=secretvalue '+str(Path.home()))
        self.assertNotIn('secretvalue',line); self.assertNotIn('user:password',line)
        self.assertNotIn(str(Path.home()),line)

    def test_output_streams_before_process_exits(self):
        with tempfile.TemporaryDirectory() as d:
            seen=threading.Event(); errors=[]
            def report(stage,line):
                if stage=='r': seen.set()
            def target():
                try: run_logged([sys.executable,'-u','-c','import time; print("[braintrace:stage] r"); time.sleep(.5)'],Path(d)/'build.log',report,timeout=5)
                except Exception as exc: errors.append(exc)
            t=threading.Thread(target=target); t.start()
            self.assertTrue(seen.wait(3)); self.assertTrue(t.is_alive())
            t.join(); self.assertFalse(errors)
            self.assertIn('[braintrace:stage] r',(Path(d)/'build.log').read_text())

    def test_nonzero_exit_retains_log(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'code 7'):
                run_logged([sys.executable,'-u','-c','print("specific compiler failure"); raise SystemExit(7)'],Path(d)/'build.log',lambda *a:None)
            self.assertIn('specific compiler failure',(Path(d)/'build.log').read_text())

    @unittest.skipUnless(os.name=='posix','Linux process groups')
    def test_timeout_stops_descendant_and_next_build_can_run(self):
        with tempfile.TemporaryDirectory() as d:
            pidfile=Path(d)/'pid'
            script='import subprocess,time; p=subprocess.Popen(["sleep","60"]); open('+repr(str(pidfile))+',"w").write(str(p.pid)); time.sleep(60)'
            with self.assertRaisesRegex(RuntimeError,'exceeded'):
                run_logged([sys.executable,'-u','-c',script],Path(d)/'build.log',lambda *a:None,timeout=.4)
            pid=int(pidfile.read_text())
            status=Path('/proc')/str(pid)/'stat'
            self.assertTrue(not status.exists() or status.read_text().split()[2]=='Z')
            run_logged([sys.executable,'-c','print("recovered")'],Path(d)/'build.log',lambda *a:None,timeout=3)

if __name__=='__main__': unittest.main(verbosity=2)
