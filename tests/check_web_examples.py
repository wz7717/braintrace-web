"""Exercise saved and live example selection through the local HTTP interface."""
import csv
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import site_server as web
from check_anonymous_queue import Client, eventually


class WebExampleChecks(unittest.TestCase):
    def setUp(self):
        work = Path(self.enterContext(TemporaryDirectory()))
        self.server = self.enterContext(web.PreviewServer(('127.0.0.1', 0), work_root=work))
        thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)
        self.client = Client(self.server)

    def test_conflicting_and_unknown_examples_are_rejected(self):
        for species, example, owner in [
            ('human', 'GSE179328', 'macaque'), ('human', 'GSE128537', 'macaque'),
            ('macaque', 'GSM755211', 'human'), ('human', 'UNKNOWN', None),
            ('macaque', 'UNKNOWN', None), ('human', '', None),
        ]:
            config = 'RAW_FIXED' if species == 'human' else 'floor_clip'
            query = urlencode(dict(species=species, configurations=config, example_id=example))
            job = dict(species=species, configurations=[config], source='example',
                       sample_id='example', example_id=example, request_key='invalid-example')
            for path, payload in [('/api/examples?' + query, None),
                                  ('/api/examples?' + query + '&format=csv', None), ('/api/jobs', job)]:
                with self.subTest(species=species, example=example, path=path):
                    status, body, _ = self.client.call(path, payload)
                    self.assertEqual(status, 400)
                    self.assertEqual(set(body), {'error'})
                    self.assertEqual(body['error']['code'], 'invalid_example')
                    self.assertIn(repr(example), body['error']['message'])
                    self.assertIn(species, body['error']['message'])
                    if owner:
                        self.assertIn(owner, body['error']['message'])
        self.assertFalse(self.server.store.jobs)

    def test_saved_identity_in_json_and_csv(self):
        for species, supplied, resolved, sample in [
            ('human', None, 'GSM755211', 'GSM755211'), ('human', 'GSM755211', 'GSM755211', 'GSM755211'),
            ('macaque', None, 'GSE128537', '10_10'), ('macaque', 'GSE128537', 'GSE128537', '10_10'),
            ('macaque', 'GSE179328', 'GSE179328', 'LID_100660'),
        ]:
            with self.subTest(species=species, supplied=supplied):
                query = dict(species=species, configurations='RAW_FIXED' if species == 'human' else 'floor_clip')
                if supplied is not None:
                    query['example_id'] = supplied
                url = '/api/examples?' + urlencode(query)
                status, result, _ = self.client.call(url)
                self.assertEqual(status, 200)
                self.assertEqual((result['species'], result['example_id'], result['sample_id']), (species, resolved, sample))
                status, data, _ = self.client.call(url + '&format=csv')
                self.assertEqual(status, 200)
                rows = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
                self.assertEqual({(r['species'], r['sample_id']) for r in rows}, {(species, sample)})

    def test_live_job_uses_selected_specimen(self):
        status, job, _ = self.client.call('/api/jobs', dict(species='macaque', configurations=['floor_clip'],
            source='example', example_id='GSE179328', sample_id='example', request_key='valid-example'))
        self.assertEqual(status, 202, job)
        self.assertEqual((job['example_id'], job['sample_id']), ('GSE179328', 'LID_100660'))
        def finished():
            current = self.client.call('/api/jobs/' + job['id'])[1]
            return current if current['status'] not in ('queued', 'running') else None
        done = eventually(finished, timeout=self.server.policy.macaque_timeout_seconds)
        self.assertEqual(done['status'], 'succeeded', done.get('error'))
        self.assertEqual(done['result']['sample_id'], 'LID_100660')
        self.assertTrue(done['result']['saved_output_comparison']['pass'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
