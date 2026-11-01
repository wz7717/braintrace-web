"""Targeted integration checks. Mocked failures are NOT scientific inference evidence."""
from pathlib import Path
import ast, csv, io, itertools, json, sys, threading, unittest
from unittest.mock import patch
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import three_tier_backend as b
import site_server as web

class ThreeTierChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=(b.ROOT/'examples/three_tier/GSE128537/SINGLE_SAMPLE.npz').read_bytes()
        cls.prepared=b.read_input(cls.data,'.npz','unknown_001')
        cls.actual=b.read_json(b.ROOT/'verification/real_GSE128537/result.json')
        cls.net=cls.actual['tiers']['Network']
        cls.server=web.PreviewServer(('127.0.0.1',0));cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def get(self,path):
        with urlopen(self.base+path) as r:return r.read()
    def payload(self,**changes):
        with b.np.load(io.BytesIO(self.data),allow_pickle=False) as z:p={k:z[k] for k in z.files}
        for k,v in changes.items():
            if v is None:p.pop(k,None)
            else:p[k]=v
        out=io.BytesIO();b.np.savez_compressed(out,**p);return out.getvalue()
    def test_saved_evidence_and_real_results(self):
        for cohort in ('GSE128537','GSE179328'):
            actual=b.read_json(b.ROOT/f'verification/real_{cohort}/result.json')
            self.assertTrue(b.compare_example(actual,cohort)['pass'])
            self.assertEqual(b.saved_example('macaque',['floor_clip'],cohort)['mode'],'saved_example')
    def test_contract_and_missing_metadata(self):
        self.assertEqual(self.prepared['lower_status'],'compatible')
        missing=b.read_input(self.payload(mapping_version=None),'.npz','unknown')
        self.assertEqual(missing['lower_status'],'input_incompatible')
        self.assertIn('mapping_version',missing['missing_fields'])
        tiers,_=b.lower_tiers(missing,self.net)
        self.assertEqual(tiers['Exact']['ranking'],[])
    def test_partial_axis_rejected_not_imputed(self):
        with self.assertRaisesRegex(ValueError,'21,668'):
            b.read_input(self.payload(genes=b.np.array(b.assets()[0][:-1])),'.npz','unknown')
    def test_mask_and_scale_not_silently_accepted(self):
        mask=self.prepared['observed'].copy();mask[0]=~mask[0]
        for data,key in [(self.payload(observed=mask),'observed_mask_matching_declared_mapping'),(self.payload(normalization=b.np.array('TPM')),'full_library_ln1p_CPM')]:
            p=b.read_input(data,'.npz','unknown');self.assertEqual(p['lower_status'],'input_incompatible');self.assertIn(key,p['missing_fields'])
    def test_legacy_panel_reports_insufficient(self):
        for file in ('OBSERVED_ONE_SAMPLE.npz','PREPARED_INPUT_EXAMPLE.csv'):
            p=b.read_input((b.ROOT/'examples/macaque'/file).read_bytes(),Path(file).suffix,'unknown')
            self.assertEqual(p['lower_status'],'input_insufficient')
            with patch.object(b.legacy,'load_module',side_effect=AssertionError('Must not score lower tiers')):
                t,_=b.lower_tiers(p,self.net)
            self.assertEqual(t['Group']['status'],'input_insufficient')
    def test_uncovered_combination_without_model_call(self):
        _,_,beams=b.assets();missing=next(c for c in itertools.combinations(self.net['classes'],3) if tuple(sorted(c)) not in beams)
        with patch.object(b.legacy,'load_module',side_effect=AssertionError('No fallback')):
            t,ref=b.lower_tiers(self.prepared,{'ranking':list(missing)})
        self.assertIsNone(ref);self.assertEqual(t['Exact']['status'],'reference_unavailable')
    def test_mock_failure_distinct(self):
        with patch.object(b.legacy,'load_module',side_effect=RuntimeError('MOCK failure')):
            t,ref=b.lower_tiers(self.prepared,self.net)
        self.assertEqual(t['Group']['status'],'failed');self.assertTrue(ref)
    def test_full_csv_and_observed_zero(self):
        p=self.prepared;out=io.StringIO();w=csv.writer(out);keys=['contract_version','mapping_version','normalization','full_count_rows']
        w.writerow(['gene_id','ln1p_cpm','observed','full_library_counts']+keys)
        for i in reversed(range(21668)):
            w.writerow([b.assets()[0][i],repr(float(p['x'][i])),int(p['observed'][i]),p['library']]+[p['metadata'][k] for k in keys])
        restored=b.read_input(out.getvalue().encode(),'.csv','unknown')
        self.assertTrue(b.np.array_equal(restored['x'],p['x']));self.assertEqual(restored['lower_status'],'compatible')
        i=b.np.flatnonzero(p['observed'])[0];x=p['x'].reshape(-1,1).copy();x[i,0]=0
        zero=b.read_input(self.payload(x=x),'.npz','unknown');self.assertTrue(zero['observed'][i]);self.assertEqual(zero['x'][i],0)
    def test_csv_roundtrip_and_status_rows(self):
        result=self.actual;rows=list(csv.DictReader(io.StringIO(b.result_csv(result).lstrip('\ufeff'))))
        self.assertEqual(len(rows),sum(len(t['ranking']) for t in result['tiers'].values()))
        for row in rows:
            item=result['tiers'][row['tier']];i=item['classes'].index(row['class_id'])
            self.assertEqual(float(row['score']),item['scores'][i]);self.assertEqual(row['scheme_id'],b.SCHEME_ID)
            if row['tier']=='Group':self.assertEqual(json.loads(row['members_json']),item['members'][i])
        result=json.loads(json.dumps(result));result['tiers'].update(b._not_run('input_insufficient','input_insufficient',missing_fields=['full_21668_gene_axis']))
        rows=list(csv.DictReader(io.StringIO(b.result_csv(result).lstrip('\ufeff'))))
        self.assertEqual([r['status'] for r in rows[-2:]],['input_insufficient','input_insufficient'])
    def test_http_saved_upload_and_resources(self):
        saved=json.loads(self.get('/api/examples?species=macaque&configurations=floor_clip&example_id=GSE179328'))
        self.assertEqual(saved['sample_id'],'LID_100660')
        req=Request(self.base+'/api/uploads?species=macaque&sample_id=unknown&filename=test.npz',data=self.data,headers={'X-BrainTrace-Token':self.server.token},method='POST')
        with urlopen(req) as r:upload=json.loads(r.read())
        self.assertEqual(upload['summary']['lower_input_status'],'compatible')
        self.assertNotIn('reference_labels',upload)
        self.assertEqual(self.get('/api/files/macaque-example'),self.data)
        self.assertEqual(self.get('/api/files/coverage'),web.resource_files()['coverage'].read_bytes())
        self.assertIn(b'csv',self.get('/resources.js'))
        self.assertEqual(self.get('/api/examples?species=macaque&configurations=floor_clip&example_id=GSE179328&format=csv').decode(),b.result_csv(saved))
    def test_human_original_validator_and_saved_results(self):
        if not (b.ROOT/'science/human/protocol/PROTOCOL.json').exists():
            self.skipTest('Private original human provenance documents intentionally omitted from portable ZIP; see HUMAN_BUNDLE_SETUP.md.')
        validator=b.legacy.load_module('human_existing_validator_test',b.ROOT/'science/human/code/predict_frozen_plm9.py')
        validator.validate_bundle(b.ROOT/'science/human/PREDICTION_BUNDLE.json')
        self.assertEqual(len(b.saved_example('human',['RAW_FIXED','RANK_FIXED'])['predictions']),2)
    def test_unknown_result_never_gets_truth(self):
        # Structural guarantee: annotation/comparison is added only by explicit example callers.
        tree=ast.parse((b.ROOT/'three_tier_backend.py').read_text(encoding='utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_macaque')
        text=ast.get_source_segment((b.ROOT/'three_tier_backend.py').read_text(encoding='utf-8'),node)
        self.assertNotIn('add_example_context',text);self.assertNotIn('compare_example',text)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ThreeTierChecks))
    report={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'mock_scope':['uncovered combination no fallback','lower runtime failure'],'real_inference':'Existing verification/real_GSE128537 and real_GSE179328 outputs compared again; no new inference in these tests.','reused_checks':'Prior unchanged human scoring and original HTTP lifecycle/idempotency checks are reused only for unaffected behavior.'}
    (b.ROOT/'verification/targeted_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    sys.exit(not result.wasSuccessful())
