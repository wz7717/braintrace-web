"""Replay packaged examples through the frozen models and test the runtime contracts."""
import ast
import csv
from functools import cache, cached_property
from http.cookiejar import CookieJar
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch
from urllib.request import HTTPCookieProcessor, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import three_tier_backend as b
import site_server as web


@cache
def live_example(cohort):
    info = b.example_info(cohort)
    source = b.ROOT / info['input']
    return b.run_macaque(source.read_bytes(), source.suffix, info['sample_id'], ['floor_clip'])


def npz_bytes(fields):
    output = io.BytesIO()
    b.np.savez_compressed(output, **fields)
    return output.getvalue()


class ThreeTierChecks(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        live_example.cache_clear()

    @cached_property
    def data(self):
        return (b.ROOT / b.example_info('GSE128537')['input']).read_bytes()

    @cached_property
    def prepared(self):
        return b.read_input(self.data, '.npz', 'unknown_001')

    @property
    def net(self):
        return live_example('GSE128537')['tiers']['Network']

    def payload(self, **changes):
        with b.np.load(io.BytesIO(self.data), allow_pickle=False) as sample:
            fields = dict(sample)
        for name, value in changes.items():
            if value is None:
                fields.pop(name, None)
            else:
                fields[name] = value
        return npz_bytes(fields)

    def assert_live_matches_frozen_row(self, cohort):
        actual = live_example(cohort)
        frozen = b.read_json(b.ROOT / b.example_info(cohort)['saved_row'])
        self.assertEqual(actual['mode'], 'live_frozen_inference')
        self.assertEqual(actual['sample_id'], frozen['sample_id'])
        score_columns = {
            'Network': ('head_classes_json', 'Network_scores_json'),
            'Group': ('Group_ranking_json', 'Group_scores_json'),
            'Exact': ('candidate_regions_json', 'exact_fusion_candidate_order_json'),
        }
        self.assertEqual(set(actual['tiers']), set(score_columns))
        for tier, (classes, scores) in score_columns.items():
            item = actual['tiers'][tier]
            self.assertEqual(item['status'], 'succeeded', tier)
            self.assertEqual(item['ranking'], json.loads(frozen[tier + '_ranking_json']), tier)
            self.assertEqual(item['classes'], json.loads(frozen[classes]), tier)
            b.np.testing.assert_allclose(item['scores'], json.loads(frozen[scores]), rtol=0, atol=b.ATOL,
                                         err_msg=f'{cohort} {tier} scores')
        self.assertEqual(actual['tiers']['Group']['members'], json.loads(frozen['Group_members_json']))
        for key in ('corr50', 'corr100', 'corr200'):
            b.np.testing.assert_allclose(actual['tiers']['Exact'][key],
                                         json.loads(frozen[key + '_candidate_order_json']),
                                         rtol=0, atol=b.ATOL, err_msg=f'{cohort} {key}')

    def test_live_GSE128537_matches_frozen_row(self):
        self.assert_live_matches_frozen_row('GSE128537')

    def test_live_GSE179328_matches_frozen_row(self):
        self.assert_live_matches_frozen_row('GSE179328')

    def test_contract_and_missing_metadata(self):
        self.assertEqual(self.prepared['lower_status'],'compatible')
        missing=b.read_input(self.payload(mapping_version=None),'.npz','unknown')
        self.assertEqual(missing['lower_status'],'input_incompatible')
        self.assertIn('mapping_version',missing['missing_fields'])
        tiers,_=b.lower_tiers(missing,self.net)
        self.assertEqual(tiers['Exact']['ranking'],[])
    def test_partial_axis_rejected_not_imputed(self):
        with self.assertRaisesRegex(ValueError,'21,668|shape'):
            b.read_input(self.payload(genes=b.np.array(b.assets()[0][:-1])),'.npz','unknown')
    def test_mask_and_scale_not_silently_accepted(self):
        mask=self.prepared['observed'].copy();mask[0]=~mask[0]
        p=b.read_input(self.payload(observed=mask),'.npz','unknown')
        self.assertEqual(p['lower_status'],'input_incompatible')
        self.assertIn('observed_mask_matching_declared_mapping',p['missing_fields'])
        with self.assertRaisesRegex(ValueError,'normalization'):
            b.read_input(self.payload(normalization=b.np.array('TPM')),'.npz','unknown')
    def test_legacy_panel_reports_insufficient(self):
        genes, head_rows, _ = b.assets()
        sample = b.example_info('GSE128537')['sample_id']
        panel_genes = b.np.asarray(genes)[head_rows]
        values = self.prepared['x'][head_rows]
        observed = self.prepared['observed'][head_rows]
        library = self.prepared['library']
        panel = npz_bytes({
            'genes': panel_genes, 'observed_logcpm': values.reshape(1, -1),
            'observed': observed, 'samples': b.np.array([sample]),
            'full_library_counts': b.np.array([library]),
        })
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['gene_id', 'ln1p_cpm', 'observed', 'full_library_counts'])
        writer.writerows((g, float(x), int(mask), library)
                         for g, x, mask in zip(panel_genes, values, observed, strict=True))
        for suffix, data in [('.npz', panel), ('.csv', output.getvalue().encode())]:
            with self.subTest(suffix=suffix):
                tiers = b.run_macaque(data, suffix, sample, ['floor_clip'])['tiers']
                self.assertEqual(tiers['Network']['status'], 'succeeded')
                self.assertEqual(tiers['Network']['ranking'], self.net['ranking'])
                for tier in ('Group', 'Exact'):
                    self.assertEqual(tiers[tier]['status'], 'input_insufficient')
                    self.assertEqual(tiers[tier]['ranking'], [])

    def test_uncovered_combination_without_model_call(self):
        genes, head_rows, beams = b.assets()
        network, prepared = self.net, self.prepared
        incomplete = beams.copy()
        del incomplete[tuple(sorted(network['ranking'][:3]))]
        with patch.object(b, 'assets', return_value=(genes, head_rows, incomplete)), \
                patch.object(b.legacy, 'load_module') as load_scorer:
            tiers, reference = b.lower_tiers(prepared, network)
        load_scorer.assert_not_called()
        self.assertIsNone(reference)
        for tier in ('Group', 'Exact'):
            self.assertEqual(tiers[tier]['status'], 'reference_unavailable')
            self.assertEqual(tiers[tier]['ranking'], [])

    def test_mock_failure_distinct(self):
        network = self.net
        with patch.object(b.legacy, 'load_module', side_effect=RuntimeError('MOCK failure')):
            tiers, reference = b.lower_tiers(self.prepared, network)
        self.assertEqual(tiers['Group']['status'], 'failed')
        self.assertTrue(reference)
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
        result = live_example('GSE128537')
        rows = list(csv.DictReader(io.StringIO(b.result_csv(result).lstrip('\ufeff'))))
        self.assertEqual(len(rows),sum(len(t['ranking']) for t in result['tiers'].values()))
        for row in rows:
            item=result['tiers'][row['tier']];i=item['classes'].index(row['class_id'])
            self.assertEqual(float(row['score']),item['scores'][i]);self.assertEqual(row['scheme_id'],b.SCHEME_ID)
            if row['tier']=='Group':self.assertEqual(json.loads(row['members_json']),item['members'][i])
        result=json.loads(json.dumps(result));result['tiers'].update(b._not_run('input_insufficient','input_insufficient',missing_fields=['full_21668_gene_axis']))
        rows=list(csv.DictReader(io.StringIO(b.result_csv(result).lstrip('\ufeff'))))
        self.assertEqual([r['status'] for r in rows[-2:]],['input_insufficient','input_insufficient'])
    def test_http_saved_upload_and_resources(self):
        work_root = Path(self.enterContext(TemporaryDirectory()))
        server = self.enterContext(web.PreviewServer(('127.0.0.1', 0), work_root=work_root))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        opener = build_opener(HTTPCookieProcessor(CookieJar()))

        def get(route):
            with opener.open(base + route) as response:
                return response.read()

        example = '/api/examples?species=macaque&configurations=floor_clip&example_id=GSE179328'
        saved = json.loads(get(example))
        self.assertEqual(saved['mode'], 'saved_example')
        self.assertEqual(saved['sample_id'], 'LID_100660')
        token = json.loads(get('/api/bootstrap'))['session_token']
        request = Request(base + '/api/uploads?species=macaque&sample_id=unknown&filename=test.npz',
                          data=self.data, headers={'X-BrainTrace-Token': token}, method='POST')
        with opener.open(request) as response:
            self.assertEqual(response.status, 201)
            upload = json.load(response)
        self.assertEqual(upload['summary']['lower_input_status'], 'compatible')
        self.assertNotIn('reference_labels', upload)

        resources = get('/resources.js')
        for route, expected in [('/api/files/macaque-example', self.data),
                                ('/api/files/coverage', web.resource_files()['coverage'].read_bytes())]:
            self.assertIn(route.encode(), resources)
            self.assertEqual(get(route), expected)

        with opener.open(base + example + '&format=csv') as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), 'text/csv')
            reader = csv.DictReader(io.StringIO(response.read().decode('utf-8-sig')))
            self.assertTrue({'sample_id', 'tier', 'status', 'rank', 'class_id', 'score'}.issubset(reader.fieldnames))
            rows = list(reader)
        self.assertEqual({row['status'] for row in rows}, {'succeeded'})
        self.assertEqual({row['sample_id'] for row in rows}, {saved['sample_id']})
        expected_ranks = [(tier, rank, label) for tier in ('Network', 'Group', 'Exact')
                          for rank, label in enumerate(saved['tiers'][tier]['ranking'], 1)]
        self.assertEqual([(r['tier'], int(r['rank']), r['class_id']) for r in rows], expected_ranks)

    def test_human_saved_results(self):
        expected = b.read_json(b.ROOT / 'examples/human/EXPECTED_PREDICTION.json')
        saved = b.saved_example('human', ['RAW_FIXED', 'RANK_FIXED'])
        self.assertEqual(saved['sample_id'], expected['sample_id'])
        self.assertEqual(set(saved['predictions']), {'RAW_FIXED', 'RANK_FIXED'})
        for program, item in saved['predictions'].items():
            frozen = expected['predictions'][program]
            self.assertEqual(item['classes'], frozen['class_ids'])
            self.assertEqual(item['scores'], frozen['score9'])
            self.assertEqual(item['prediction'], frozen['prediction'])

    def test_human_original_bundle(self):
        links = b.ROOT / 'EXISTING_HUMAN_INPUT_REFERENCES.csv'
        if links.is_file():
            with links.open(encoding='utf-8-sig', newline='') as stream:
                linked = [Path(row['relative_path']).relative_to('runtime_assets') for row in csv.DictReader(stream)]
            if linked and not any((b.ROOT / path).is_file() for path in linked):
                self.skipTest(f'This package references {len(linked)} external human files, including '
                              'FROZEN_REFERENCE.rds. None are installed in this runtime.')
        human = b.ROOT / 'science/human'
        validator = b.legacy.load_module('human_existing_validator_test', human / 'code/predict_frozen_plm9.py')
        validator.validate_bundle(human / 'PREDICTION_BUNDLE.json')

    def test_unknown_result_never_gets_truth(self):
        # Structural guarantee: annotation/comparison is added only by explicit example callers.
        tree=ast.parse((b.ROOT/'three_tier_backend.py').read_text(encoding='utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_macaque')
        text=ast.get_source_segment((b.ROOT/'three_tier_backend.py').read_text(encoding='utf-8'),node)
        self.assertNotIn('add_example_context',text);self.assertNotIn('compare_example',text)


class CheckResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_tests = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_tests.append(test.id())


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ThreeTierChecks)
    result = unittest.TextTestRunner(verbosity=2, resultclass=CheckResult).run(suite)
    report = {
        'scheme_id': b.SCHEME_ID,
        'tests': result.testsRun, 'passed': len(result.passed_tests),
        'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
        'passed_tests': result.passed_tests,
        'failed_tests': [{'test': test.id(), 'traceback': trace} for test, trace in result.failures],
        'error_tests': [{'test': test.id(), 'traceback': trace} for test, trace in result.errors],
        'skipped_tests': [{'test': test.id(), 'reason': reason} for test, reason in result.skipped],
        'real_inference': 'The two live GEO tests compare a packaged SINGLE_SAMPLE.npz with its frozen SAVED_ROW.json.',
        'score_absolute_tolerance': b.ATOL,
        'mock_scope': ['missing reference combination', 'lower-tier runtime failure'],
    }
    output = b.ROOT / 'verification/targeted_checks.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    sys.exit(not result.wasSuccessful())
