"""Single-sample web adapter. The packaged scientific kernels are unchanged."""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import zipfile
from bounded_uploads import check_macaque_container, check_cel_expansion

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
ROUTES = ('baseline', 'floor_clip', 'floor_only', 'clip_only')
HUMAN_PROGRAMS = ('RAW_FIXED', 'RANK_FIXED', 'BOTH')
ATOL = 1e-10


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime_config():
    config = read_json(ROOT / 'runtime.example.json')
    local = ROOT / 'runtime.local.json'
    if local.is_file():
        config.update(read_json(local))
    for key in ('python', 'rscript', 'rlib', 'rlib_site', 'temp_root'):
        override = os.environ.get('BRAINTRACE_' + key.upper())
        if override:
            config[key] = override
    return config


def validate_id(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise ValueError('Use a sample ID of 1–128 ASCII letters, digits, underscores, dots or hyphens.')
    return value


def human_ready():
    config = runtime_config()
    return all(config.get(k) and Path(config[k]).exists() for k in ('python', 'rscript', 'rlib', 'temp_root'))


def ranked(classes, scores):
    return sorted(range(len(classes)), key=lambda i: (-float(scores[i]), str(classes[i])))


def result_item(classes, scores, decision=None):
    classes = [str(c) for c in classes]
    scores = np.asarray(scores, dtype=np.float64)
    if scores.shape != (len(classes),) or not np.isfinite(scores).all():
        raise ValueError('Invalid score axis returned by the frozen model.')
    order = ranked(classes, scores)
    result = {'classes': classes, 'scores': scores.tolist(),
              'ranking': [classes[i] for i in order], 'prediction': classes[order[0]]}
    if decision is not None:
        result['decision'] = np.asarray(decision, dtype=np.float64).tolist()
    return result


def read_macaque_input(data: bytes, suffix: str, sample_id: str):
    """Require one full, named panel; observed zero and missing are distinct."""
    validate_id(sample_id)
    genes = read_json(ROOT / 'science/macaque/baseline/genes.json')
    if len(data) > 8 * 1024**2:
        raise ValueError('Prepared macaque input must be at most 8 MiB.')
    check_macaque_container(data, suffix)
    if suffix.lower() == '.npz':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if len(archive.infolist()) > 8 or sum(x.file_size for x in archive.infolist()) > 16 * 1024**2:
                raise ValueError('Prepared NPZ exceeds the single-sample size limit.')
        with np.load(io.BytesIO(data), allow_pickle=False) as payload:
            required = {'observed_logcpm', 'observed', 'genes', 'samples', 'full_library_counts'}
            if not required.issubset(payload.files):
                raise ValueError('NPZ needs observed_logcpm, observed, genes, samples and full_library_counts.')
            axis = payload['genes']
            if axis.shape != (5000,) or axis.tolist() != genes:
                raise ValueError('NPZ gene axis must match the supplied 5,000-gene template exactly.')
            if payload['samples'].shape != (1,):
                raise ValueError('Exactly one sample is supported.')
            x = payload['observed_logcpm'].copy()
            observed = payload['observed'].copy()
            library = payload['full_library_counts'].copy()
    elif suffix.lower() == '.csv':
        rows = list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        if len(rows) != 5000 or not {'gene_id', 'ln1p_cpm', 'observed', 'full_library_counts'}.issubset(rows[0]):
            raise ValueError('CSV needs 5,000 rows and gene_id, ln1p_cpm, observed, full_library_counts columns.')
        by_gene = {r['gene_id']: r for r in rows}
        if len(by_gene) != 5000 or set(by_gene) != set(genes):
            raise ValueError('CSV gene IDs must be unique and match the frozen panel.')
        rows = [by_gene[g] for g in genes]
        if any(r['observed'] not in ('0', '1') for r in rows):
            raise ValueError('observed must be 0 or 1; a measured zero uses observed=1.')
        observed = np.array([r['observed'] == '1' for r in rows], dtype=bool)
        x = np.array([[float(r['ln1p_cpm']) for r in rows]], dtype=np.float32)
        totals = [float(r['full_library_counts']) for r in rows]
        if len(set(totals)) != 1:
            raise ValueError('Use the same full-library count total on every CSV row.')
        library = np.array(totals[:1], dtype=np.float64)
    else:
        raise ValueError('Use a prepared NPZ or CSV file.')
    if x.shape != (1, 5000) or x.dtype.kind != 'f' or observed.shape != (5000,) or observed.dtype != bool:
        raise ValueError('Require one floating-point 1×5000 array and a Boolean 5000-element mask.')
    if library.shape != (1,) or not np.isfinite(library).all() or library[0] <= 0:
        raise ValueError('A positive full-library count total is required.')
    # Matches the saved external input representation; the frozen transform
    # retains its original float32 arithmetic and source-mean assignment order.
    x = x.astype(np.float32)
    if not np.isfinite(x[:, observed]).all() or (x[:, observed] < 0).any():
        raise ValueError('Observed values must be finite and nonnegative ln(1 + CPM).')
    x[:, ~observed] = 0  # placeholder only; the kernel applies source means
    return x, observed, genes, float(library[0])


def run_macaque(data, suffix, sample_id, routes):
    if not routes or any(r not in ROUTES for r in routes) or len(set(routes)) != len(routes):
        raise ValueError('Select a known frozen macaque configuration once.')
    import scipy
    import sklearn
    if (platform.python_version(), np.__version__, scipy.__version__, sklearn.__version__) != ('3.11.9', '1.26.4', '1.13.1', '1.5.2'):
        raise ValueError('Live inference requires the documented, pinned scientific runtime.')
    x, observed, genes, library = read_macaque_input(data, suffix, sample_id)
    kernel = load_module('demo_frozen_macaque_kernel', ROOT / 'science/macaque/inference.py')
    result = {'species': 'macaque', 'sample_id': sample_id, 'mode': 'live_frozen_inference',
              'observed_features': int(observed.sum()), 'missing_features': int((~observed).sum()),
              'full_library_counts': library, 'new_fits': 0, 'predictions': {}}
    with threadpool_limits(limits=1):
        for route in routes:
            folder = ROOT / 'science/macaque' / route
            if read_json(folder / 'genes.json') != genes:
                raise ValueError('Frozen configuration gene axes differ.')
            model = joblib.load(folder / 'model.joblib')  # only packaged models, never user uploads
            with np.load(folder / 'state.npz', allow_pickle=False) as z:
                state = {k: z[k].copy() for k in z.files}
            _, transformed, valid = kernel.transform_external(x, observed, state)
            probability, decision, valid, reason = kernel.score(model, transformed, valid)
            if not valid[0]:
                raise ValueError('Frozen inference rejected this sample: ' + str(reason[0]))
            result['predictions'][route] = result_item(model.classes_, probability[0], decision[0])
    return result


def run_human(data, suffix, sample_id, program):
    validate_id(sample_id)
    if program not in HUMAN_PROGRAMS or suffix.lower() not in ('.cel', '.cel.gz'):
        raise ValueError('Use a CEL/CEL.gz input and an explicit RAW_FIXED or RANK_FIXED program.')
    if not data or len(data) > 80 * 1024**2:
        raise ValueError('CEL upload must be nonempty and at most 80 MiB.')
    check_cel_expansion(data, suffix)
    config = runtime_config()
    if not human_ready():
        raise ValueError('The host needs the documented frozen CEL Python/R runtime. Configure runtime.local.json.')
    root = Path(config['temp_root']).resolve()
    if not str(root).isascii():
        raise ValueError('The CEL native reader requires an ASCII temporary root.')
    bundle = ROOT / 'science/human'
    with tempfile.TemporaryDirectory(prefix='request_', dir=root) as work:
        work = Path(work)
        source = work / ('input' + suffix.lower())
        source.write_bytes(data)
        out = work / 'output'
        temporary = work / 'native_temp'
        command = [config['python'], '-X', 'utf8', '-B', str(bundle / 'code/predict_frozen_plm9.py'),
                   '--bundle', str(bundle / 'PREDICTION_BUNDLE.json'), '--input', str(source),
                   '--sample-id', sample_id, '--program', program, '--out', str(out),
                   '--rscript', config['rscript'], '--rlib', config['rlib'], '--temp-root', str(temporary)]
        env = os.environ.copy()
        env['R_LIBS_USER'] = config['rlib']
        if config.get('rlib_site'):
            env['R_LIBS_SITE'] = config['rlib_site']
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, creationflags=flags)
        try:
            stdout, stderr = process.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
            else:
                process.kill()
            process.communicate()
            raise ValueError('The single-sample request exceeded 180 seconds; no result is reported.')
        if process.returncode:
            # Return a short failure reason without displaying server filesystem paths.
            raise ValueError('Frozen CEL processing rejected the input or runtime. Check platform, file integrity and host dependencies.')
        prediction = read_json(next(out.glob('sample_*/PREDICTION.json')))
        result = {'species': 'human', 'sample_id': sample_id, 'mode': 'live_frozen_inference',
                  'new_fits': 0, 'predictions': {}}
        for name, item in prediction['predictions'].items():
            result['predictions'][name] = result_item(item['class_ids'], item['score9'])
        return result


def saved_example(species, configurations):
    result = {'species': species, 'mode': 'saved_example', 'new_fits': 0, 'predictions': {}}
    if species == 'human':
        saved = read_json(ROOT / 'examples/human/EXPECTED_PREDICTION.json')
        result['sample_id'] = saved['sample_id']
        for name in configurations:
            entry = saved['predictions'][name]
            result['predictions'][name] = result_item(entry['class_ids'], entry['score9'])
    else:
        meta = read_json(ROOT / 'examples/macaque/SAMPLE_METADATA.json')
        result['sample_id'] = meta['sample_id']
        result['reference_labels'] = meta['allowed_networks']
        with np.load(ROOT / 'examples/macaque/EXPECTED_SCORES.npz', allow_pickle=False) as z:
            for name in configurations:
                index = list(z['keys'][:, 1]).index(name)
                result['predictions'][name] = result_item(z['classes'], z['probabilities'][index], z['decisions'][index])
    return result


def compare_example(result):
    expected = saved_example(result['species'], list(result['predictions']))
    details = {}
    for name, item in result['predictions'].items():
        other = expected['predictions'][name]
        axes_equal = item['classes'] == other['classes']
        ranks_equal = item['ranking'] == other['ranking']
        score_delta = float(np.max(np.abs(np.array(item['scores']) - other['scores']))) if axes_equal else None
        decision_delta = None
        if 'decision' in item and axes_equal:
            decision_delta = float(np.max(np.abs(np.array(item['decision']) - other['decision'])))
        passed = axes_equal and ranks_equal and score_delta <= ATOL and (decision_delta is None or decision_delta <= ATOL)
        details[name] = {'pass': bool(passed), 'same_class_axis': axes_equal, 'same_ranking': ranks_equal,
                         'max_score_difference': score_delta, 'max_decision_difference': decision_delta}
    return {'pass': all(x['pass'] for x in details.values()), 'absolute_tolerance': ATOL,
            'relative_tolerance': 0, 'configurations': details}
