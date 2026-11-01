"""Focused HTTP ownership, quota, FIFO and process-tree recovery checks. No model calls."""
from pathlib import Path
import ctypes, dataclasses, http.cookiejar, json, os, socket, sys, tempfile, threading, time, unittest
from contextlib import contextmanager
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import site_server as web
from anonymous_sessions import AnonymousSessions, QueuePolicy, RateLimits, APIError, client_ip
from process_jobs import ProcessRunner, JobFailure

def eventually(fn, timeout=5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.02)
    raise AssertionError('Expected condition did not become true.')

class Client:
    def __init__(self,server):
        self.base='http://127.0.0.1:'+str(server.server_port)
        self.jar=http.cookiejar.CookieJar();self.opener=build_opener(HTTPCookieProcessor(self.jar));self.csrf=''
        status,data,headers=self.call('/api/bootstrap')
        assert status==200,(status,data)
        self.csrf=data['session_token'];self.cookie=headers.get('Set-Cookie')
    def call(self,path,data=None,method=None,headers=None):
        h={'X-BrainTrace-Token':self.csrf}
        if isinstance(data,dict):data=json.dumps(data).encode();h['Content-Type']='application/json'
        h.update(headers or {})
        try:r=self.opener.open(Request(self.base+path,data=data,method=method,headers=h),timeout=5)
        except HTTPError as e:r=e
        with r:
            raw=r.read()
            body=json.loads(raw) if 'application/json' in r.headers.get('Content-Type','') else raw
            return r.status,body,r.headers
    def upload(self,sample='sample_a',data=b'fixture'):
        status,body,_=self.call('/api/uploads?species=macaque&sample_id='+sample+'&filename=input.npz',data)
        assert status==201,(status,body)
        return body['upload_id']
    def submit(self,upload,sample='sample_a',key='request-key-001'):
        return self.call('/api/jobs',dict(species='macaque',configurations=['floor_clip'],source='upload',
            sample_id=sample,upload_id=upload,contract_confirmed=True,request_key=key))

class GateRunner:
    healthy=True
    def __init__(self):self.release=threading.Event();self.started=[];self.finished=[]
    def run(self,spec,data,timeout,cancel):
        self.started.append(spec['sample_id'])
        while not self.release.wait(.01):
            if cancel.is_set():raise JobFailure('task_cancelled','cancelled')
        self.finished.append(spec['sample_id'])
        return {'sample_id':spec['sample_id'],'synthetic':True}

@contextmanager
def serving(policy=None,runner=None):
    # Only the transport/queue boundary is tested here. Scientific functions must never execute.
    def validate(species,sample,filename,data):
        web.require_sample_id(sample)
        return {'species':species,'sample_id':sample,'suffix':'.npz','bytes':len(data)}
    with patch.object(web,'scientific_runtime_ready',return_value=True), \
         patch.object(web.backend,'human_ready',return_value=True), \
         patch.object(web.backend,'read_json',return_value={}), \
         patch.object(web,'validate_input',side_effect=validate), \
         patch.object(web.backend,'result_csv',return_value='synthetic,csv\n'), \
         patch.object(web.backend,'run_macaque',side_effect=AssertionError('No model calls allowed')), \
         patch.object(web.backend,'run_human',side_effect=AssertionError('No model calls allowed')):
        server=web.PreviewServer(('127.0.0.1',0),policy=policy,runner=runner or GateRunner())
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);thread.start()
        try:yield server
        finally:server.shutdown();server.server_close();thread.join(timeout=3)

class HTTPChecks(unittest.TestCase):
    def test_owner_upload_job_csv_and_cookie_csrf(self):
        with serving() as s:
            a,b=Client(s),Client(s)
            self.assertNotEqual(a.csrf,b.csrf);self.assertNotEqual(a.cookie,b.cookie)
            self.assertIn('HttpOnly',a.cookie);self.assertIn('SameSite=Strict',a.cookie)
            uid=a.upload()
            self.assertEqual(b.call('/api/uploads/'+uid,method='DELETE')[0],404)
            self.assertEqual(b.submit(uid)[0],404)
            self.assertEqual(a.call('/api/uploads/'+uid,method='DELETE',headers={'X-BrainTrace-Token':b.csrf})[0],403)
            status,job,_=a.submit(uid);self.assertEqual(status,202)
            jid=job['id']
            for path in ('/api/jobs/'+jid,'/api/jobs/'+jid+'/scores.csv'):
                self.assertEqual(b.call(path)[0],404)
            self.assertTrue(set(job).isdisjoint({'owner','ip','request','data','cancel'}))
            s.store.runner.release.set()
            eventually(lambda:a.call('/api/jobs/'+jid)[1]['status']=='succeeded')
            self.assertEqual(a.call('/api/jobs/'+jid+'/scores.csv')[0],200)
            self.assertEqual(b.call('/api/jobs/'+jid+'/scores.csv')[0],404)
            a.jar.clear()
            self.assertEqual(a.call('/api/jobs/'+jid)[0],401)

    def test_idempotency_is_owner_scoped_and_single_session_active(self):
        with serving() as s:
            a,b=Client(s),Client(s);uid=a.upload()
            first=a.submit(uid)[1];second=a.submit(uid)[1]
            self.assertEqual(first['id'],second['id'])
            self.assertEqual(a.submit(uid,key='another-key')[0],429)
            self.assertEqual(a.submit(uid,sample='changed')[0],409)
            other=b.submit(b.upload())[1];self.assertNotEqual(other['id'],first['id'])
            self.assertEqual(other['queue_position'],1)
            eventually(lambda:len(s.store.runner.started)==1)
            s.store.runner.release.set()
            eventually(lambda:len(s.store.runner.finished)==2)
            self.assertEqual(len(s.store.jobs),2)

    def test_global_queue_and_ip_active_limit(self):
        for policy,expected in [(dataclasses.replace(QueuePolicy(),active_jobs_global=2),'queue_full'),
                                (dataclasses.replace(QueuePolicy(),active_jobs_per_ip=2),'ip_job_quota')]:
            with self.subTest(expected=expected),serving(policy) as s:
                clients=[Client(s) for _ in range(3)]
                for a in clients[:2]:self.assertEqual(a.submit(a.upload())[0],202)
                status,body,_=clients[2].submit(clients[2].upload())
                self.assertEqual(status,429);self.assertEqual(body['error']['code'],expected)

    def test_upload_count_reservation_budget_and_disconnected_upload(self):
        policy=dataclasses.replace(QueuePolicy(),input_bytes_per_session=12,input_bytes_global=20)
        with serving(policy) as s:
            a,b=Client(s),Client(s);uid=a.upload(data=b'12345678')
            self.assertEqual(a.call('/api/uploads?species=macaque&sample_id=x&filename=a.npz',b'12345')[0],429)
            self.assertEqual(a.submit(uid)[0],202)
            self.assertEqual(a.call('/api/uploads?species=macaque&sample_id=x&filename=a.npz',b'12345')[0],429)
            b.upload(data=b'12345678')
            self.assertEqual(b.call('/api/uploads?species=macaque&sample_id=x&filename=a.npz',b'12345')[0],429)
        with serving() as s:
            a=Client(s);a.upload();a.upload()
            self.assertEqual(a.call('/api/uploads?species=macaque&sample_id=x&filename=a.npz',b'a')[0],429)
            b=Client(s)
            cookie='; '.join(c.name+'='+c.value for c in b.jar)
            with socket.create_connection(('127.0.0.1',s.server_port),timeout=2) as sock:
                head=f'POST /api/uploads?species=macaque&sample_id=x&filename=a.npz HTTP/1.0\r\nHost: 127.0.0.1:{s.server_port}\r\nCookie: {cookie}\r\nX-BrainTrace-Token: {b.csrf}\r\nContent-Length: 100\r\n\r\n'
                sock.sendall(head.encode()+b'x');sock.shutdown(socket.SHUT_WR)
                sock.recv(4096)
            eventually(lambda:len(s.store.reservations)==0)
            self.assertEqual(len(s.store.uploads),2)

    def test_session_and_result_expiry(self):
        with serving() as s:
            a=Client(s);uid=a.upload();job=a.submit(uid)[1]
            owner=s.sessions.parse(a.cookie)
            with s.sessions.lock:s.sessions.sessions[owner]['created']-=s.policy.session_absolute_seconds+1
            s.store.cleanup()
            self.assertEqual(a.call('/api/jobs/'+job['id'])[0],401)
            eventually(lambda:s.store.jobs[job['id']]['status']=='failed')
            self.assertEqual(s.store._bytes(),0)
        with serving() as s:
            a=Client(s);job=a.submit(a.upload())[1];s.store.runner.release.set()
            eventually(lambda:s.store.jobs[job['id']]['status']=='succeeded')
            with s.store.lock:s.store.jobs[job['id']]['finished_epoch']-=s.policy.retention_seconds+1
            self.assertEqual(a.call('/api/jobs/'+job['id'])[0],404)

    def test_upload_total_deadline_releases_reservation(self):
        with serving(dataclasses.replace(QueuePolicy(),body_timeout_seconds=1)) as s:
            a=Client(s);cookie='; '.join(c.name+'='+c.value for c in a.jar)
            with socket.create_connection(('127.0.0.1',s.server_port),timeout=3) as sock:
                head=f'POST /api/uploads?species=macaque&sample_id=x&filename=a.npz HTTP/1.0\r\nHost: 127.0.0.1:{s.server_port}\r\nCookie: {cookie}\r\nX-BrainTrace-Token: {a.csrf}\r\nContent-Length: 100\r\n\r\n'
                sock.sendall(head.encode())
                # Progress must not reset the total body deadline.
                for _ in range(3):time.sleep(.25);sock.sendall(b'x')
                response=sock.recv(4096)
                self.assertIn(b'408',response)
            eventually(lambda:len(s.store.reservations)==0)
            self.assertEqual(len(s.store.uploads),0)

    def test_queued_timeout_never_starts(self):
        with serving() as s:
            a,b=Client(s),Client(s)
            a.submit(a.upload());eventually(lambda:len(s.store.runner.started)==1)
            job=b.submit(b.upload(sample='second'),sample='second')[1]
            with s.store.lock:s.store.jobs[job['id']]['created_epoch']-=s.policy.queue_timeout_seconds+1
            s.store.cleanup()
            current=b.call('/api/jobs/'+job['id'])[1]
            self.assertEqual(current['error']['code'],'queue_timeout')
            self.assertNotIn('second',s.store.runner.started)

    def test_submission_rate_limit(self):
        with serving(dataclasses.replace(QueuePolicy(),jobs_per_session_half_hour=1)) as s:
            a=Client(s);job=a.submit(a.upload())[1];s.store.runner.release.set()
            eventually(lambda:s.store.jobs[job['id']]['status']=='succeeded')
            status,body,_=a.submit(a.upload(),key='second-request')
            self.assertEqual(status,429);self.assertEqual(body['error']['code'],'rate_limit')

    def test_origin_host_and_static_allowlist(self):
        with serving() as s:
            a=Client(s)
            self.assertEqual(a.call('/api/bootstrap',headers={'Origin':'https://wrong.example'})[0],403)
            self.assertEqual(a.call('/api/bootstrap',headers={'Host':'wrong.example'})[0],403)
            for path in ('/runtime.local.json','/queue.local.json','/job_work/request.json','/../site_server.py'):
                self.assertEqual(a.call(path)[0],404)

class PolicyChecks(unittest.TestCase):
    def test_rate_windows_and_anonymous_creation_limit(self):
        clock=[0.0];rates=RateLimits(lambda:clock[0])
        rates.take_many([('a',1,60)])
        with self.assertRaises(APIError):rates.take_many([('a',1,60),('b',1,60)])
        self.assertNotIn('b',rates.items)
        clock[0]=61;rates.take_many([('a',1,60)])
        sessions=AnonymousSessions(dataclasses.replace(QueuePolicy(),new_sessions_per_ip_hour=1),clock=lambda:clock[0])
        owner,csrf,cookie=sessions.resolve(None,'127.0.0.1',create=True)
        self.assertEqual(sessions.resolve(cookie,'127.0.0.1')[0],owner)
        with self.assertRaises(APIError):sessions.resolve(None,'127.0.0.1',create=True)

    def test_secure_cookie_and_explicit_proxy_ip(self):
        sessions=AnonymousSessions(QueuePolicy(),'https://demo.example')
        _,_,cookie=sessions.resolve(None,'1.2.3.4',create=True)
        self.assertTrue(cookie.startswith('__Host-'));self.assertIn('; Secure',cookie)
        h={'Host':'demo.example','X-BrainTrace-Client-IP':'1.2.3.4'}
        self.assertEqual(client_ip(h,'127.0.0.1','https://demo.example',False),'127.0.0.1')
        self.assertEqual(client_ip(h,'127.0.0.1','https://demo.example',True),'1.2.3.4')
        h['X-BrainTrace-Client-IP']='1.2.3.4, 5.6.7.8'
        with self.assertRaises(APIError):client_ip(h,'127.0.0.1','https://demo.example',True)

def pid_stopped(pid):
    if os.name=='nt':
        from ctypes import wintypes as w
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
        k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.WaitForSingleObject.restype=w.DWORD
        k.CloseHandle.argtypes=[w.HANDLE]
        h=k.OpenProcess(0x100000,False,pid)
        if not h:return ctypes.get_last_error()==87
        try:return k.WaitForSingleObject(h,0)==0
        finally:k.CloseHandle(h)
    try:os.kill(pid,0);return False
    except ProcessLookupError:return True

class ProcessChecks(unittest.TestCase):
    def test_timeout_crash_descendants_cleanup_and_next_task(self):
        with tempfile.TemporaryDirectory(prefix='braintrace_queue_test_') as td:
            root=Path(td);worker=Path(__file__).parent/'fixtures/queue_worker.py'
            runner=ProcessRunner(web.ROOT,root/'work',worker=worker)
            for mode in ('hang','orphan','crash'):
                with self.subTest(mode=mode):
                    marker=root/(mode+'.pid')
                    with self.assertRaises(JobFailure) as caught:
                        runner.run({'sample_id':mode},str(marker).encode(),2,threading.Event())
                    self.assertEqual(caught.exception.code,'task_timeout' if mode=='hang' else 'worker_failed')
                    if mode!='crash':
                        self.assertTrue(marker.exists());eventually(lambda:pid_stopped(int(marker.read_text())))
                    self.assertEqual(list((root/'work').iterdir()),[])
                    self.assertEqual(runner.run({'sample_id':'next'},b'',2,threading.Event())['sample_id'],'next')

    def test_real_timeout_in_queue_then_next_owner_runs(self):
        with tempfile.TemporaryDirectory(prefix='braintrace_fifo_test_') as td:
            root=Path(td);marker=root/'child.pid'
            runner=ProcessRunner(web.ROOT,root/'work',worker=Path(__file__).parent/'fixtures/queue_worker.py')
            with serving(dataclasses.replace(QueuePolicy(),macaque_timeout_seconds=2),runner) as s:
                a,b=Client(s),Client(s)
                first=a.submit(a.upload('hang',str(marker).encode()),sample='hang')[1]
                second=b.submit(b.upload('next'),sample='next')[1]
                eventually(lambda:s.store.jobs[second['id']]['status']=='succeeded',8)
                self.assertEqual(s.store.jobs[first['id']]['error']['code'],'task_timeout')
                self.assertTrue(marker.exists());eventually(lambda:pid_stopped(int(marker.read_text())))
                self.assertEqual(list((root/'work').iterdir()),[])

    def test_server_close_cancels_process_tree(self):
        with tempfile.TemporaryDirectory(prefix='braintrace_close_test_') as td:
            root=Path(td);marker=root/'child.pid'
            runner=ProcessRunner(web.ROOT,root/'work',worker=Path(__file__).parent/'fixtures/queue_worker.py')
            with serving(runner=runner) as s:
                a=Client(s);a.submit(a.upload('hang',str(marker).encode()),sample='hang')
                eventually(marker.exists)
            eventually(lambda:pid_stopped(int(marker.read_text())))
            self.assertEqual(list((root/'work').iterdir()),[])

if __name__=='__main__':
    unittest.main(verbosity=2)
