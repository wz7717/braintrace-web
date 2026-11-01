"""Focused session/UI bridge tests. Synthetic worker only; no model inference."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cloud_service import CloudService
from browser_download import local_download
from anonymous_sessions import APIError
from check_anonymous_queue import GateRunner, eventually
import site_server as web


class BridgeChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.runner=GateRunner()
        self.svc=CloudService(web.ROOT,sys.executable,Path(self.temp.name),runner=self.runner)
        self.svc.api.validate_input=lambda species,sample,filename,data: dict(species=species,sample_id=sample,suffix='.npz',bytes=len(data))
        self.a,self.acsrf,self.acookie=self.svc.session()
        self.b,self.bcsrf,self.bcookie=self.svc.session()

    def tearDown(self):
        self.svc.store.close(); self.temp.cleanup()

    def upload(self,owner,csrf,key='request-one'):
        return self.svc.submit_upload(owner,csrf,'macaque','synthetic','input.npz',b'fixture',['floor_clip'],key)

    def test_private_job_csv_and_single_active(self):
        job=self.upload(self.a,self.acsrf)
        with self.assertRaises(APIError): self.svc.result(self.b,job['id'])
        with self.assertRaises(APIError): self.svc.csv(self.b,job['id'])
        with self.assertRaises(APIError): self.upload(self.a,self.acsrf,'request-two')
        self.assertFalse(self.svc.store.uploads) # rejected resubmission releases temporary upload
        self.runner.release.set()
        eventually(lambda:self.svc.result(self.a,job['id'])['status']=='succeeded')
        with patch.object(self.svc.backend,'result_csv',return_value='synthetic,csv\n'):
            self.assertEqual(self.svc.csv(self.a,job['id']),'synthetic,csv\n')

    def test_expired_owner_cannot_read_completed_result(self):
        job=self.upload(self.a,self.acsrf); self.runner.release.set()
        eventually(lambda:self.svc.result(self.a,job['id'])['status']=='succeeded')
        self.svc.sessions.sessions[self.a]['created']-=self.svc.policy.session_absolute_seconds
        with self.assertRaises(APIError): self.svc.result(self.a,job['id'])

    def test_no_shared_download_endpoint_or_unescaped_label(self):
        link=local_download('private,data','safe.csv','<script>')
        self.assertIn('URL.createObjectURL',link)
        self.assertNotIn('private,data',link)
        self.assertIn('&lt;script&gt;',link)
        self.assertNotIn('http',link)

    def test_streamlit_routes_and_independent_sessions(self):
        from streamlit.testing.v1 import AppTest
        import streamlit as st
        st.cache_resource.clear()
        import cloud_service
        cloud_service._SERVICE=None
        cloud_service._STARTUP=None
        with patch('cloud_service.bootstrap',return_value=self.svc) as build:
            first=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=20)
            eventually(lambda:cloud_service._STARTUP.snapshot()['state']=='ready')
            first.run()
            self.assertEqual(len(first.exception),0)
            self.assertEqual(first.radio(key='route').value,'macaque')
            first.radio(key='route').set_value('human').run()
            self.assertEqual(len(first.exception),0)
            self.assertEqual(first.multiselect[0].value,['RAW_FIXED','RANK_FIXED'])
            st.cache_resource.clear()
            second=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=20)
            self.assertEqual(len(second.exception),0)
            self.assertNotEqual(first.session_state['_anonymous_cookie'],second.session_state['_anonymous_cookie'])
            self.assertEqual(build.call_count,1)
        cloud_service._SERVICE=None
        cloud_service._STARTUP=None
        st.cache_resource.clear()

    def ready_manager(self):
        from startup_runtime import StartupManager
        manager=StartupManager(lambda report:self.svc)
        manager.start(); eventually(lambda:manager.snapshot()['state']=='ready')
        return manager

    def test_language_switch_preserves_inputs_and_active_job(self):
        from streamlit.testing.v1 import AppTest
        with patch('cloud_service.get_startup',return_value=self.ready_manager()):
            app=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=20)
            cookie=app.session_state['_anonymous_cookie']
            app.text_input(key='sample_id').set_value('retained_id').run()
            app.radio(key='input_source').set_value('example').run()
            app.selectbox(key='example_id').set_value('PsychENCODE_HIP').run()
            app.button(key='run_inference').click().run()
            job_id=app.session_state['_job']
            eventually(lambda:len(self.runner.started)==1)
            app.radio(key='ui_language').set_value('English').run()
            self.assertEqual(len(app.exception),0)
            self.assertEqual(app.session_state['_job'],job_id)
            self.assertEqual(app.session_state['_anonymous_cookie'],cookie)
            self.assertEqual(app.radio(key='input_source').value,'example')
            self.assertEqual(app.selectbox(key='example_id').value,'PsychENCODE_HIP')
            self.assertTrue(app.button(key='run_inference').disabled)
            self.assertIn('expression',app.title[0].value)
            self.assertEqual(len(self.runner.started),1)
            app.radio(key='input_source').set_value('upload').run()
            # Streamlit removes widgets not rendered; language switches alone retain them.
            app.text_input(key='sample_id').set_value('language_kept').run()
            app.radio(key='ui_language').set_value('中文').run()
            self.assertEqual(app.text_input(key='sample_id').value,'language_kept')

    def test_startup_is_nonblocking_and_language_does_not_restart_it(self):
        import threading
        from startup_runtime import StartupManager
        from streamlit.testing.v1 import AppTest
        gate=threading.Event(); calls=[]
        def build(report):
            calls.append(1); report('r','synthetic R build'); gate.wait(10); return self.svc
        manager=StartupManager(build); manager.start()
        try:
            with patch('cloud_service.get_startup',return_value=manager):
                app=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=5)
                self.assertEqual(len(app.exception),0)
                self.assertFalse(app.get('file_uploader'))
                self.assertIn('synthetic R build',app.code[0].value)
                app.radio(key='ui_language').set_value('English').run(timeout=5)
                self.assertEqual(len(calls),1)
                self.assertTrue(any('Prepare R' in x.value for x in app.markdown))
                gate.set(); eventually(lambda:manager.snapshot()['state']=='ready')
                app.run(); self.assertTrue(app.get('file_uploader'))
        finally: gate.set()

    def test_startup_error_and_retry_are_visible(self):
        from startup_runtime import StartupManager
        from streamlit.testing.v1 import AppTest
        calls=[]
        def build(report):
            calls.append(1)
            if len(calls)==1: raise ValueError('synthetic CRAN download failure')
            return self.svc
        manager=StartupManager(build,retry_delay=0)
        manager.start(); eventually(lambda:manager.snapshot()['state']=='failed')
        with patch('cloud_service.get_startup',return_value=manager):
            app=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=10)
            self.assertTrue(app.error)
            self.assertIn('synthetic CRAN',app.code[0].value)
            # Allow the monotonic cooldown boundary to pass, then request one retry.
            manager.finished-=1
            app.run(); app.button(key='retry_startup').click().run()
            eventually(lambda:manager.snapshot()['state']=='ready')
            app.run()
            self.assertEqual(len(app.exception),0)
            self.assertTrue(app.get('file_uploader'))
            self.assertEqual(len(calls),2)

    def test_completed_results_and_download_labels_in_both_languages(self):
        from streamlit.testing.v1 import AppTest
        self.runner.run=lambda spec,data,timeout,cancel: dict(sample_id='synthetic',species='macaque',mode='fixture',
            tiers={name:dict(classes=['A','B','C'],ranking=['A','B','C'],scores=[.6,.3,.1],
                **({'members':[['A'],['B'],['C']]} if name=='Group' else {})) for name in ('Network','Group','Exact')})
        with patch('cloud_service.get_startup',return_value=self.ready_manager()), \
             patch.object(self.svc.backend,'result_csv',return_value='synthetic,csv\n'):
            app=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=20)
            app.radio(key='input_source').set_value('example').run()
            app.button(key='run_inference').click().run()
            eventually(lambda:next(iter(self.svc.store.jobs.values()))['status']=='succeeded')
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any('排名' in x.value for x in app.markdown))
            app.radio(key='ui_language').set_value('English').run()
            self.assertFalse(app.exception)
            self.assertTrue(any('Candidate' in x.value and '0.6' in x.value for x in app.markdown))
            self.assertEqual(app.button(key='after_success').label,'Prepare next job')


if __name__=='__main__': unittest.main(verbosity=2)
