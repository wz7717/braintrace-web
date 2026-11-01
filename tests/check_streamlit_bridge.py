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
        with patch('cloud_service.bootstrap',return_value=self.svc) as build:
            first=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=20)
            self.assertEqual(len(first.exception),0)
            self.assertEqual(first.radio[0].value,'猕猴三层 / Macaque')
            first.radio[0].set_value('人类 CEL / Human').run()
            self.assertEqual(len(first.exception),0)
            self.assertEqual(first.multiselect[0].value,['RAW_FIXED','RANK_FIXED'])
            st.cache_resource.clear()
            second=AppTest.from_file(str(web.ROOT/'streamlit_app.py')).run(timeout=20)
            self.assertEqual(len(second.exception),0)
            self.assertNotEqual(first.session_state['_anonymous_cookie'],second.session_state['_anonymous_cookie'])
            self.assertEqual(build.call_count,1)
        cloud_service._SERVICE=None
        st.cache_resource.clear()


if __name__=='__main__': unittest.main(verbosity=2)
