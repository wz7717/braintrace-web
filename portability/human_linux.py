"""Linux CEL application adapter. Original bundle and scientific kernels stay intact."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_one(source, sample_id, program, out, rscript, rlib, temp_root):
    if platform.system() != 'Linux':
        raise RuntimeError('This adapter is qualified only for Linux.')
    spec = importlib.util.spec_from_file_location('original_frozen_plm9', ROOT/'science/human/code/predict_frozen_plm9.py')
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    bundle_path = ROOT/'science/human/PREDICTION_BUNDLE.json'
    bundle, files, genes, helper, models = frozen.validate_bundle(bundle_path)
    training = models['RAW_FIXED']
    models = frozen.select_programs(models, program)
    record = frozen.input_records(Path(source), sample_id)[0]
    out, temp_root = Path(out), Path(temp_root)
    out.mkdir(parents=True, exist_ok=False)
    temp_root.mkdir(parents=True, exist_ok=True)
    gzip_spec = importlib.util.spec_from_file_location('original_gzip_expander', files['gzip_helper'])
    gzip_helper = importlib.util.module_from_spec(gzip_spec)
    gzip_spec.loader.exec_module(gzip_helper)
    cel, owned, owner, expected, materialized = frozen.owned_cel(Path(record['cel_path']), temp_root, gzip_helper, sample_id)
    driver = Path(__file__).with_name('predict_linux.R')
    adapter = {'id': 'braintrace.linux.r461.v1', 'driver_sha256': frozen.sha(driver),
               'python_entry_sha256': frozen.sha(Path(__file__))}
    request = {
        'schema': 'braintrace.rawcel.frozen_prediction_request.v1', 'sample_id': sample_id,
        'CEL_path': str(cel), 'CEL_sha256': frozen.sha(cel),
        'files': {role: {**bundle['files'][role], 'path': str(path)} for role, path in files.items()},
        'runtime_R': bundle['runtime']['R'], 'dimensions': bundle['dimensions'],
        'protocol_sha256': bundle['protocol_sha256'],
        'training_sample_ids': training['training_sample_ids'].tolist(),
        'training_donor_ids': training['training_donor_ids'].tolist(),
        'chosen_program': program, 'executed_programs': list(models), 'gene_ids': genes,
        'upstream_fit_allowed': False, 'synthetic_fixture': False, 'portability_adapter': adapter,
    }
    request_path = out/'REQUEST.json'
    frozen.new_json(request_path, request)
    env = {**os.environ, 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
           'R_LIBS_USER': str(rlib), **{key:'1' for key in frozen.THREAD_ENV}}
    child = subprocess.run([str(rscript), '--vanilla', str(driver), '--request', str(request_path),
                            '--out', str(out), '--library', str(rlib)], env=env, capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=180)
    (out/'R_STDOUT.txt').write_text(child.stdout, encoding='utf-8')
    (out/'R_STDERR.txt').write_text(child.stderr, encoding='utf-8')
    if child.returncode:
        raise RuntimeError('Linux R application failed: ' + child.stderr[-2000:])
    qc = frozen.read_json(out/'UPSTREAM_QC.json')
    features = out/'GENE_FEATURES.f64le'
    if (qc.get('status') != 'PASS_SINGLE_SAMPLE_FROZEN_APPLICATION' or qc.get('sample_id') != sample_id
            or qc.get('gene_ids') != genes or qc.get('upstream_fit_allowed') is not False
            or qc.get('portability_adapter') != adapter or qc.get('feature_sha256') != frozen.sha(features)
            or features.stat().st_size != len(genes)*8):
        raise ValueError('Linux application receipt or feature binding differs.')
    feature = frozen.np.fromfile(features, dtype='<f8').reshape(1, len(genes))
    predictions = frozen.predict_features(helper, models, feature, genes, program)
    result = {'schema':'braintrace.rawcel.linux_prediction.v1', 'sample_id':sample_id,
              'predictions':predictions, 'portability_adapter':adapter, 'new_fit_count':0,
              'source_bundle_sha256':frozen.sha(bundle_path), 'R_version':qc['R_version'],
              'feature_sha256':frozen.sha(features), 'warnings':frozen.WARNINGS}
    frozen.new_json(out/'PREDICTION.json', result)
    frozen.clean_owned(owned, owner, expected)
    return result


def run_human(data, suffix, sample_id, program):
    import tempfile
    import demo_backend as original
    from bounded_uploads import check_cel_expansion
    original.validate_id(sample_id)
    if suffix.lower() not in ('.cel', '.cel.gz') or not 0 < len(data) <= 80*1024**2:
        raise ValueError('Use one CEL/CEL.gz file up to 80 MiB.')
    if program not in original.HUMAN_PROGRAMS:
        raise ValueError('Unknown frozen program.')
    check_cel_expansion(data, suffix)
    config = original.runtime_config()
    with tempfile.TemporaryDirectory(prefix='cel_', dir=config['temp_root']) as work:
        work = Path(work)
        source = work/('input'+suffix.lower()); source.write_bytes(data)
        result = run_one(source, sample_id, program, work/'output', config['rscript'], config['rlib'], work/'native')
        return {'species':'human', 'sample_id':sample_id, 'mode':'live_frozen_inference', 'new_fits':0,
                'runtime_adapter':'braintrace.linux.r461.v1', 'R_version':result['R_version'],
                'predictions': {k:original.result_item(v['class_ids'],v['score9']) for k,v in result['predictions'].items()}}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('input','sample-id','program','out','rscript','rlib','temp-root'):
        ap.add_argument('--'+key, required=True)
    a = ap.parse_args()
    run_one(a.input, a.sample_id, a.program, a.out, a.rscript, a.rlib, a.temp_root)
