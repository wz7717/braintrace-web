"""Run the two published GEO examples and check the declared-scale input contract."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import three_tier_backend as backend


def npz(fields):
    output = io.BytesIO()
    np.savez_compressed(output, **fields)
    return output.getvalue()


def rejected(raw, suffix, sample):
    try:
        backend.run_macaque(raw, suffix, sample, ['floor_clip'])
    except ValueError as error:
        assert 'normalization' in str(error), str(error)
        return str(error)
    raise AssertionError('Obtained a prediction with an incompatible normalization')


def extract(raw, sample, mapping, out):
    source = out.parent / 'matrix.npz'
    source.write_bytes(raw)
    return subprocess.run([
        sys.executable, '-B', str(ROOT/'tools/extract_prepared_sample.py'),
        '--input', str(source), '--sample-id', sample,
        '--mapping', mapping, '--output', str(out),
    ], capture_output=True, text=True, errors='replace')


def csv_input(genes, x, observed, library, scales):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['gene_id', 'ln1p_cpm', 'observed', 'full_library_counts', 'normalization'])
    writer.writerows((g, float(v), int(o), library, scale) for g, v, o, scale in zip(genes,x,observed,scales,strict=True))
    return out.getvalue().encode()


def check_example(example, work):
    sample = example['sample_id']
    body = (ROOT/example['input']).read_bytes()
    with np.load(io.BytesIO(body), allow_pickle=False) as artifact:
        fields = {key: artifact[key] for key in artifact.files}
    original = backend.run_macaque(body, '.npz', sample, ['floor_clip'])
    original_check = backend.compare_example(original, example['id'])
    assert original_check['pass']
    expected_ranks = {t:r['ranking'] for t,r in original['tiers'].items()}
    checked = {}
    for scale, array in [('linear_CPM', np.expm1(fields['x'])),
                         ('log2_1plus_CPM', fields['x'] / np.log(2))]:
        bad = npz(dict(fields, normalization=np.array(scale), x=array))
        reason = rejected(bad, '.npz', sample)
        out = work/(example['id']+'_'+scale+'.npz')
        run = extract(bad, sample, example['mapping_version'], out)
        assert run.returncode and 'normalization' in run.stderr and not out.exists(), run.stderr
        checked[scale] = {'inference_error':reason,'extraction_rejected':True}
    legacy = fields.copy()
    for key in ('contract_version','mapping_version','normalization','full_count_rows'):
        legacy.pop(key)
    old = backend.run_macaque(npz(legacy), '.npz', sample, ['floor_clip'])['tiers']
    assert old['Network']['ranking']==expected_ranks['Network']
    assert all(old[t]['status']=='input_incompatible' for t in ['Group','Exact'])
    for kind, source in [('labelled', body), ('legacy', npz(legacy))]:
        out = work/(example['id']+'_'+kind+'.npz')
        run = extract(source, sample, example['mapping_version'], out)
        assert run.returncode==0, run.stderr
        replay = backend.run_macaque(out.read_bytes(), '.npz', sample, ['floor_clip'])
        assert all(replay['tiers'][t]['ranking']==r for t,r in expected_ranks.items())
    genes = fields['genes']
    head_rows = backend.assets()[1]
    observed = fields['observed']
    x = fields['x'][:,0]
    library = float(fields['full_library_counts'][0])
    panel = {'observed_logcpm':x[head_rows][None,:], 'genes':genes[head_rows],
             'observed':observed[head_rows],'samples':fields['samples'],'full_library_counts':fields['full_library_counts']}
    legacy_panel = backend.run_macaque(npz(panel), '.npz', sample, ['floor_clip'])['tiers']
    assert legacy_panel['Network']['ranking']==expected_ranks['Network']
    assert all(legacy_panel[t]['status']=='input_insufficient' for t in ['Group','Exact'])
    rejected(npz(dict(panel,normalization=np.array('linear_CPM'))), '.npz', sample)
    for keep in (np.arange(len(genes)),head_rows):
        scales = ['']*len(keep)
        scales[-1] = 'log2_1plus_CPM'
        rejected(csv_input(genes[keep], x[keep], observed[keep], library, scales), '.csv', sample)
    return {'cohort':example['id'], 'sample':sample, 'original':original_check, 'explicit_wrong_scales':checked,
            'legacy_full_axis':{t:r['status'] for t,r in old.items()},
            'legacy_panel':{t:r['status'] for t,r in legacy_panel.items()},
            'labelled_and_legacy_valid_extractions_match_all_ranks':True,
            'network_only_npz_and_both_csv_lengths_checked':True}


if __name__=='__main__':
    with TemporaryDirectory() as tmp:
        results = [check_example(backend.example_info(cohort),Path(tmp)) for cohort in ['GSE128537','GSE179328']]
    print(json.dumps(results,ensure_ascii=False,indent=2))
