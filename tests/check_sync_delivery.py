"""Assembly and HTTP checks only. All scientific inference entry points are blocked."""
from pathlib import Path
import importlib.util, json, re, sys, tempfile, threading, unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import three_tier_backend as backend
import site_server as web

class SyncDeliveryChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocks = [patch.object(backend, name, side_effect=AssertionError('No inference allowed'))
                      for name in ('run_human', 'run_macaque', 'lower_tiers')]
        for block in cls.blocks: block.start()
        cls.server = web.PreviewServer(('127.0.0.1', 0), public_origin='https://demo.example.org')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
        for block in cls.blocks: block.stop()

    def get(self, path, headers=None):
        with urlopen(Request(self.base+path, headers=headers or {}), timeout=10) as r:
            return r.status, r.read()

    def test_current_bootstrap_and_saved_outputs(self):
        boot=json.loads(self.get('/api/bootstrap')[1])
        self.assertEqual(boot['scheme']['deployment_asset_version'],'20261101_43_beams_psychencode_v1')
        for cohort in ('GSE128537','GSE179328','PsychENCODE_AMY','PsychENCODE_HIP'):
            saved=json.loads(self.get('/api/examples?species=macaque&configurations=floor_clip&example_id='+cohort)[1])
            self.assertEqual(saved,backend.saved_example('macaque',['floor_clip'],cohort))
        saved=json.loads(self.get('/api/examples?species=human&configurations=RAW_FIXED,RANK_FIXED')[1])
        self.assertEqual(saved['mode'],'saved_example')

    def test_all_resource_links_and_removed_routes(self):
        paths=web.resource_files()
        for path in paths.values():
            self.assertTrue(path.is_relative_to(backend.ROOT.resolve()))
            self.assertTrue(path.is_file(),str(path))
        for key in list(paths)+list(web.FILES):
            self.assertEqual(self.get('/api/files/'+key)[0],200,key)
        js=(backend.ROOT/'web/resources.js').read_text(encoding='utf-8')
        pages=json.loads(js.split('const pages = ',1)[1].split(';\n',1)[0])
        for body in pages.values():
            for path in re.findall(r'href="([^"]+)"',body):
                self.assertEqual(self.get(path)[0],200,path)
        for key in ('local-package','reviewer-package','human-addon','current-main','current-supplement','paper-data'):
            with self.assertRaises(HTTPError) as caught: self.get('/api/files/'+key)
            self.assertEqual(caught.exception.code,404)

    def test_six_reference_pairs_resolve_without_scoring(self):
        _,_,lookup=backend.assets()
        self.assertEqual(len(lookup),43)
        entries=backend.read_json(backend.ROOT/'science/lower/BEAMS.json')
        self.assertEqual(len({e['id'] for e in entries}),43)
        for entry in entries[37:]:
            self.assertEqual(lookup[tuple(sorted(entry['networks']))],entry['id'])
            directory=backend.ROOT/'science/lower/beams'/entry['id']
            rules=backend.read_json(directory/'RULES_AND_MEMBERS.json')
            self.assertIn('annotations',rules)
            with backend.np.load(directory/'INPUT.npz',allow_pickle=False) as data:
                self.assertTrue({'regions','gene_rows','reference'}.issubset(data.files))

    def test_explicit_https_proxy_origin(self):
        self.assertEqual(self.get('/api/bootstrap',{'Host':'demo.example.org','Origin':'https://demo.example.org'})[0],200)
        for headers in ({'Host':'unconfigured.example.org'},
                        {'Host':'demo.example.org','Origin':'https://unconfigured.example.org'}):
            with self.assertRaises(HTTPError) as caught: self.get('/api/bootstrap',headers)
            self.assertEqual(caught.exception.code,403)
        for value in ('http://demo.example.org','https://demo.example.org/','https://user@demo.example.org'):
            with self.assertRaises(ValueError):web.validate_public_origin(value)

    def test_resource_paths_cannot_escape_runtime(self):
        with patch.object(web.backend,'read_json',return_value={'outside':'../private.txt'}):
            with self.assertRaises(ValueError):web.resource_files()

    def test_assembly_preserves_inputs_and_refuses_overwrite(self):
        spec=importlib.util.spec_from_file_location('prepare_runtime',backend.ROOT/'tools/prepare_runtime.py')
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        with tempfile.TemporaryDirectory(prefix='braintrace-copy-check-') as tmp:
            root=Path(tmp);src=root/'code';assets=root/'assets';out=root/'runtime'
            (src/'metadata').mkdir(parents=True);assets.mkdir()
            scheme={'scheme_id':'fixture','deployment_asset_version':'fixture-v1'}
            (src/'metadata/SCHEME.json').write_text(json.dumps(scheme))
            (src/'app.py').write_bytes(b'# copy only\r\n')
            edition={'scheme_id':'fixture','edition':'fixture-v1','combination_count':43}
            (assets/'ASSET_EDITION.json').write_text(json.dumps(edition))
            for rel in ('science/lower/BEAMS.json','examples/three_tier/EXAMPLES.json',
                        'science/macaque/floor_clip/model.joblib','science/human/PREDICTION_BUNDLE.json'):
                target=assets/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'fixture')
            result=helper.prepare(src,assets,out)
            self.assertEqual(result['inference'],0)
            self.assertEqual((out/'app.py').read_bytes(),(src/'app.py').read_bytes())
            with self.assertRaises(ValueError):helper.prepare(src,assets,out)
            self.assertEqual((out/'app.py').read_bytes(),b'# copy only\r\n')

if __name__=='__main__':unittest.main(verbosity=2)
