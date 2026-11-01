"""Targeted adapter checks; two HTTP sample jobs only, no cohort rerun or fitting.

Run from an assembled runtime. --live-check is explicit; without it all inference is blocked.
"""
from pathlib import Path
import argparse, csv, io, json, sys, threading, time, unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import three_tier_backend as b
import site_server as web
from science.macaque import psychencode_adapter as adapter

EXAMPLES=('PsychENCODE_AMY','PsychENCODE_HIP')

class AdapterChecks(unittest.TestCase):
    def test_two_inputs_match_original_prepared_values(self):
        for eid in EXAMPLES:
            info=b.example_info(eid)
            p=b.read_input((b.ROOT/info['input']).read_bytes(),'.tsv',info['sample_id'])
            with b.np.load(b.ROOT/info['prepared_input'],allow_pickle=False) as z:
                self.assertTrue(b.np.array_equal(p['x'],z['x'][:,0],equal_nan=True))
                self.assertTrue(b.np.array_equal(p['observed'],z['observed']))
                self.assertEqual(p['library'],z['public_common_annotation_counts_total'][0])
            self.assertEqual(p['lower_status'],'compatible')
            self.assertEqual(int(p['observed'].sum()),14382)
            self.assertEqual(int(p['head_observed'].sum()),4064)
            self.assertEqual(b.input_summary(p)['normalization_background'],'public_common_annotation_26514')

    def test_raw_csv_and_reordered_rows_follow_same_rules(self):
        info=b.example_info(EXAMPLES[0]);data=(b.ROOT/info['input']).read_bytes()
        expected=b.read_input(data,'.tsv','unknown')
        rows=list(csv.reader(io.StringIO(data.decode()),delimiter='\t'))
        output=io.StringIO(newline='');writer=csv.writer(output)
        writer.writerow(['gene_id','count']);writer.writerows(reversed(rows[1:]))
        actual=b.read_input(output.getvalue().encode(),'.csv','unknown')
        self.assertTrue(b.np.array_equal(actual['x'],expected['x'],equal_nan=True))
        self.assertEqual(actual['library'],expected['library'])

    def test_partial_duplicate_fractional_or_wrong_id_counts_rejected(self):
        info=b.example_info(EXAMPLES[0]);lines=(b.ROOT/info['input']).read_text().splitlines()
        variants=[lines[:-1],lines+[lines[1]],lines[:1]+[lines[1].split('\t')[0]+'\t0.5']+lines[2:],
                  lines[:1]+['ENSG_NOT_IN_COMMON_UNIVERSE\t1']+lines[2:]]
        for variant in variants:
            with self.assertRaises(ValueError):b.read_input(('\n'.join(variant)+'\n').encode(),'.tsv','unknown')

    def test_prepared_contract_cannot_claim_whole_library_background(self):
        info=b.example_info(EXAMPLES[0])
        with b.np.load(b.ROOT/info['prepared_input'],allow_pickle=False) as z:fields={k:z[k] for k in z.files}
        fields['normalization']=b.np.array('full_library_ln1p_CPM')
        p=b.read_input(adapter.npz_bytes(fields),'.npz','unknown')
        self.assertEqual(p['lower_status'],'input_incompatible')
        self.assertIn(adapter.NORMALIZATION,p['missing_fields'])
        fields['normalization']=b.np.array(adapter.NORMALIZATION)
        fields.pop('public_common_annotation_counts_total')
        p=b.read_input(adapter.npz_bytes(fields),'.npz','unknown')
        self.assertIn('matching_public_common_annotation_counts_total',p['missing_fields'])

    def test_saved_mode_does_not_normalize_or_infer(self):
        with patch.object(adapter,'prepare_counts',side_effect=AssertionError('Saved mode cannot normalize')):
            for eid in EXAMPLES:
                result=b.saved_example('macaque',['floor_clip'],eid)
                self.assertEqual(result['mode'],'saved_example')
                self.assertEqual(result['input_summary']['normalization_background'],'public_common_annotation_26514')
                rows=list(csv.DictReader(io.StringIO(b.result_csv(result).lstrip('\ufeff'))))
                self.assertTrue(all(r['normalization_background']=='public_common_annotation_26514' for r in rows))
                self.assertTrue(all(r['public_common_annotation_counts_total'] for r in rows))

    def test_original_inputs_retain_prepared_values(self):
        for eid in ('GSE128537','GSE179328'):
            info=b.example_info(eid)
            with b.np.load(b.ROOT/info['input'],allow_pickle=False) as z:
                p=b.read_input((b.ROOT/info['input']).read_bytes(),'.npz',info['sample_id'])
                self.assertTrue(b.np.array_equal(p['x'],z['x'][:,0],equal_nan=True))
                self.assertTrue(b.np.array_equal(p['observed'],z['observed']))
                self.assertEqual(p['lower_status'],'compatible')
                self.assertEqual(b.input_summary(p)['normalization_background'],'full_library')

def live_checks(output):
    """Two jobs: an explicit example, then a generic upload. Never call fit or cohort code."""
    output.mkdir(parents=True,exist_ok=False)
    server=web.PreviewServer(('127.0.0.1',0));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    def request(path,data=None):
        headers={'X-BrainTrace-Token':server.token}
        if isinstance(data,dict):data=json.dumps(data).encode();headers['Content-Type']='application/json'
        with urlopen(Request(base+path,data=data,headers=headers),timeout=30) as r:return json.loads(r.read())
    comparisons=[]
    try:
        # Validate all adapter inputs before any scoring; the unittest suite runs first.
        for index,eid in enumerate(EXAMPLES):
            info=b.example_info(eid)
            payload=dict(species='macaque',configurations=['floor_clip'],sample_id=info['sample_id'],request_key='adult-integration-'+eid)
            if index==0:payload.update(source='example',example_id=eid)
            else:
                upload=request('/api/uploads?species=macaque&sample_id=unknown_hip&filename=common_counts.tsv',(b.ROOT/info['input']).read_bytes())
                assert upload['summary']['normalization_background']=='public_common_annotation_26514'
                payload.update(source='upload',sample_id='unknown_hip',upload_id=upload['upload_id'],contract_confirmed=True)
            job=request('/api/jobs',payload);deadline=time.monotonic()+90
            while job['status'] in ('queued','running') and time.monotonic()<deadline:
                time.sleep(.1);job=request('/api/jobs/'+job['id'])
            (output/(eid+'_job.json')).write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
            assert job['status']=='succeeded',job.get('error')
            result=job['result'];comparison=b.compare_example(result,eid)
            original=b.read_json((b.ROOT/info['saved_row']).parent/'EXPECTED_ORIGINAL.json')
            decision_delta=float(b.np.max(b.np.abs(b.np.array(result['tiers']['Network']['decision'])-original['network_decisions'])))
            assert decision_delta<=b.ATOL
            assert comparison['pass'],comparison
            assert result['reference_id']==original['beam_id']
            if index==1:
                assert 'example_context' not in result and 'reference_labels' not in result and 'saved_output_comparison' not in result
            rows=list(csv.DictReader(io.StringIO(b.result_csv(result).lstrip('\ufeff'))))
            assert all(r['normalization_background']=='public_common_annotation_26514' for r in rows)
            comparisons.append(dict(example=eid,sample_id=info['sample_id'],request_source=payload['source'],reference_id=result['reference_id'],
                decision_max_abs_difference=decision_delta,comparison=comparison))
        return comparisons
    finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-check',action='store_true')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    with patch.object(b,'run_macaque',side_effect=AssertionError('No inference in structural checks')),patch.object(b,'run_human',side_effect=AssertionError('No human inference')):
        tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AdapterChecks))
    if not tests.wasSuccessful():sys.exit(1)
    if args.live_check:
        if args.out is None:parser.error('--live-check requires a NEW --out directory')
        comparisons=live_checks(args.out)
        report=dict(structural_tests=tests.testsRun,structural_tests_passed=True,real_samples=2,network_calls=2,lower_calls=2,
                    new_fits=0,cohort_rerun=False,performance_reestimation=False,comparisons=comparisons)
        (args.out/'CHECKS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
