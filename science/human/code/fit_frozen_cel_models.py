"""Fixed downstream raw-CEL/frozen-PLM classifier route; no implicit execution.

Only new-run, hash-bound, training-only upstream exports are accepted. No legacy
joint-RMA matrix, legacy model, cached predictions or old result file is read.
See CLASSIFIER_INPUT_CONTRACT.md for the parent exporter/protocol contract.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import warnings

for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '2'

import numpy as np
from scipy.stats import rankdata
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits


LABELS = np.array(['4009', '4132', '4180', '4219', '4275', '4391', '4696', '9001', '9512'])
UNSUPPORTED = ['4084', '4268', '9131']
INPUT_SCHEMA = 'braintrace.rawcel.frozen_plm_classifier_inputs.v1'
UPSTREAM_SCHEMA = 'braintrace.rawcel.frozen_plm_gene_export.v1'
PROTOCOL_SCHEMA = 'braintrace.rawcel.fixed_nine_classifier_protocol.v1'
MODEL_SCHEMA = 'braintrace.rawcel.frozen_plm9.linear_classifier.v1'
PROGRAMS = ('RAW_FIXED', 'RANK_FIXED')
FOLDS = tuple(f'outer_{f}' for f in range(5)) + ('final',)
N_RECORDS = 1083
N_GENES = 16295
N_DONORS = 132
CLASSIFIER_CODE_VERSION = 'staticU16295-v2'
HERE = Path(__file__).resolve().parent
EVAL_COPY = HERE / 'adaptation_eval_frozen_cel.py'
EVAL_BINDING = HERE / 'METRICS_CODE_BINDING.json'

FROZEN_PLAN = {
    'schema': PROTOCOL_SCHEMA,
    'classifier_code_version': CLASSIFIER_CODE_VERSION,
    'n_records': N_RECORDS, 'n_donors': N_DONORS, 'n_genes': N_GENES,
    'outer_folds': 5, 'programs': list(PROGRAMS),
    'maximum_classifier_fits': 12, 'features': 200, 'C': 0.1,
    'penalty': 'l2', 'solver': 'lbfgs', 'class_weight': 'balanced',
    'multi_class': 'multinomial', 'fit_intercept': True,
    'tol': 1e-6, 'max_iter': 5000, 'random_state': 0, 'threads': 2,
    'sample_weight': 'inverse_training_donor_sample_count_normalized_to_mean_one',
    'fisher': 'donor_weighted_between_class_variance_over_within_class_variance',
    'scale': 'donor_weighted_training_mean_population_standard_deviation',
    'rank': 'within_sample_average_ties_full_fixed_U_(rank-1)/(16295-1)',
    'feature_ties': 'stable_fixed_gene_axis_order',
    'raw_rank_eligibility_intersection': False,
    'hyperparameter_selection': False, 'bootstrap_n': 2000,
    'bootstrap_seed': 20261026,
    'model_schema': MODEL_SCHEMA,
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def binding(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def new_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def new_npz(path, **values):
    payload = io.BytesIO()
    np.savez_compressed(payload, **values)
    with Path(path).open('xb') as stream:
        stream.write(payload.getvalue())


def contained(path, root):
    path = Path(path).resolve(strict=True)
    root = Path(root).resolve(strict=True)
    if path != root and root not in path.parents:
        raise ValueError(f'Input/output must stay inside the specified new run: {path}')
    return path


def bound_file(item, run):
    if not isinstance(item, dict) or set(item) != {'path', 'bytes', 'sha256'}:
        raise ValueError('File binding must contain exactly path, bytes, sha256')
    path = Path(item['path'])
    if not path.is_absolute():
        path = run / path
    path = contained(path, run)
    if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
        raise ValueError(f'File binding mismatch: {path}')
    return path


def unique_ids(values, label, allow_empty=False):
    if not isinstance(values, list) or (not values and not allow_empty):
        raise ValueError(f'{label}: expected a nonempty list')
    if any(not isinstance(v, str) or not v.strip() for v in values) or len(set(values)) != len(values):
        raise ValueError(f'{label}: invalid/duplicate IDs')
    return values


def validate_production_export_origin(receipt, run, entry_id, protocol_sha256):
    """Prevent synthetic orchestration exports from entering formal fitting.

    Require explicit JSON false in both export and bound production state index;
    missing/null/zero fields cannot masquerade as a false boolean. This verifies
    declared production provenance, not upstream numerical correctness.
    """
    if receipt.get('synthetic_fixture') is not False:
        raise ValueError(f'Formal upstream receipt requires synthetic_fixture=false: {entry_id}')
    upstream_bindings = receipt.get('upstream_state_bindings')
    if not isinstance(upstream_bindings, list) or not upstream_bindings:
        raise ValueError(f'No frozen upstream state bindings: {entry_id}')
    state_indices = []
    for item in upstream_bindings:
        path = bound_file(item, run)
        if path.name == 'FROZEN_UPSTREAM_STATE_INDEX.json':
            state_indices.append(read_json(path))
    if len(state_indices) != 1:
        raise ValueError(f'Exactly one bound production frozen upstream state index is required: {entry_id}')
    state = state_indices[0]
    if state.get('synthetic_fixture') is not False:
        raise ValueError(f'Formal upstream state requires synthetic_fixture=false: {entry_id}')
    for key, value in {
        'schema': 'braintrace.rawcel.frozen_upstream_state.v1',
        'status': 'PASS_FROZEN_REFERENCE_AND_GENE_EXPORT',
        'entry_id': entry_id, 'protocol_sha256': protocol_sha256,
    }.items():
        if state.get(key) != value:
            raise ValueError(f'Production upstream state contract mismatch: {entry_id}/{key}')


def load_metrics():
    receipt = read_json(EVAL_BINDING)
    if receipt['schema'] != 'braintrace.rawcel.metrics_code_copy.v1':
        raise ValueError('Unsupported independent metrics-copy binding')
    if sha(EVAL_COPY) != receipt['new_copy_sha256']:
        raise ValueError('Metrics helper code changed after independent copy binding')
    spec = importlib.util.spec_from_file_location('adaptation_eval_frozen_cel', EVAL_COPY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not np.array_equal(module.LABELS, LABELS):
        raise ValueError('Metrics helper label axis differs')
    return module


def validate_protocol(protocol_path, protocol_sha256, execute=False):
    protocol_path = Path(protocol_path).resolve(strict=True)
    if sha(protocol_path) != protocol_sha256:
        raise ValueError('Protocol SHA256 mismatch')
    protocol = read_json(protocol_path)
    plan = protocol.get('downstream_classifier')
    if not isinstance(plan, dict):
        raise ValueError('Protocol lacks downstream_classifier block')
    for key, value in FROZEN_PLAN.items():
        # bool is an int subclass: require the same JSON type as well as value.
        if key not in plan or type(plan[key]) is not type(value) or plan[key] != value:
            raise ValueError(f'Frozen classifier protocol mismatch: {key}')
    if execute and plan.get('execution_authorized') is not True:
        raise ValueError('Protocol has not explicitly authorized downstream execution')
    for key in ('records_csv_sha256', 'gene_ids_json_sha256'):
        if not isinstance(plan.get(key), str) or re.fullmatch('[0-9a-f]{64}', plan[key]) is None:
            raise ValueError(f'Protocol must freeze the exact independent metadata/gene-axis file: {key}')
    required_code = {'fit_frozen_cel_models.py': Path(__file__).resolve(),
                     'adaptation_eval_frozen_cel.py': EVAL_COPY,
                     'METRICS_CODE_BINDING.json': EVAL_BINDING}
    code = plan.get('code_sha256', {})
    for key, path in required_code.items():
        if code.get(key) != sha(path):
            raise ValueError(f'Frozen code SHA256 mismatch: {key}')
    load_metrics()
    return protocol


def validate_inputs(run, manifest_path, protocol_sha256, frozen_plan):
    run = Path(run).resolve(strict=True)
    manifest_path = contained(manifest_path, run)
    manifest = read_json(manifest_path)
    if manifest.get('schema') != INPUT_SCHEMA or manifest.get('protocol_sha256') != protocol_sha256:
        raise ValueError('Only the new raw-CEL/frozen-PLM input manifest schema and bound protocol are accepted')
    if manifest.get('input_origin') != 'raw_CEL' or manifest.get('legacy_joint_RMA_used') is not False:
        raise ValueError('Legacy or unspecified upstream origin rejected')
    if manifest['records_csv']['sha256'] != frozen_plan['records_csv_sha256']:
        raise ValueError('Records file differs from protocol-frozen metadata')
    if manifest['gene_ids_json']['sha256'] != frozen_plan['gene_ids_json_sha256']:
        raise ValueError('Gene axis differs from the protocol-frozen full fixed universe')
    records_path = bound_file(manifest['records_csv'], run)
    with records_path.open(encoding='utf-8-sig', newline='') as stream:
        records = list(csv.DictReader(stream))
    required = {'sample_id', 'donor', 'truth', 'fold', 'bank'}
    if len(records) != N_RECORDS or not records or not required.issubset(records[0]):
        raise ValueError('Expected exactly 1083 records with the frozen record columns')
    samples = unique_ids([r['sample_id'] for r in records], 'record sample IDs')
    donors = [r['donor'] for r in records]
    if any(not d.strip() for d in donors) or len(set(donors)) != N_DONORS:
        raise ValueError('Expected exactly 132 known donors')
    if set(r['truth'] for r in records) != set(LABELS):
        raise ValueError('All nine canonical labels must be retained')
    donor_fold = {}
    for row in records:
        if row['fold'] not in {'0', '1', '2', '3', '4'}:
            raise ValueError('Fold must be the original frozen integer 0..4')
        d, f = row['donor'], int(row['fold'])
        if d in donor_fold and donor_fold[d] != f:
            raise ValueError('A donor crosses outer folds')
        donor_fold[d] = f
        row['fold'] = f
    # Freeze the exact partition using the old protocol's metadata-only rule;
    # read no old prediction/model/result. Parent must independently bind the
    # supplied new records CSV to its approved copy of the original ledger.
    frozen_donors = sorted(set(donors), key=lambda d: (hashlib.sha256(('20261024|' + d).encode()).hexdigest(), d))
    expected = {d: i % 5 for i, d in enumerate(frozen_donors)}
    if donor_fold != expected:
        raise ValueError('Fold ledger differs from the original frozen donor partition')
    genes_path = bound_file(manifest['gene_ids_json'], run)
    genes = unique_ids(read_json(genes_path), 'fixed gene IDs')
    if len(genes) != N_GENES:
        raise ValueError('Expected the full fixed static 16295-gene axis')
    entries = manifest.get('entries')
    if not isinstance(entries, list) or [e.get('id') for e in entries] != list(FOLDS):
        raise ValueError('Require exactly outer_0..outer_4, final, in that order')
    checked = []
    for entry in entries:
        eid = entry['id']
        if any(entry.get(key) != value for key, value in {
            'dtype': 'float64', 'endian': 'little', 'layout': 'sample-major',
            'n_rows': N_RECORDS, 'n_genes': N_GENES,
        }.items()):
            raise ValueError(f'Feature export layout mismatch: {eid}')
        if entry.get('sample_ids') != samples or entry.get('gene_ids_sha256') != manifest['gene_ids_json']['sha256']:
            raise ValueError(f'Feature sample/gene axis mismatch: {eid}')
        if eid == 'final':
            training = samples
            query = []
        else:
            f = int(eid.rsplit('_', 1)[1])
            training = [r['sample_id'] for r in records if r['fold'] != f]
            query = [r['sample_id'] for r in records if r['fold'] == f]
        if entry.get('training_sample_ids') != training or entry.get('query_sample_ids') != query:
            raise ValueError(f'Upstream training/query sample ledger mismatch: {eid}')
        train_set = set(training)
        train_donors = sorted({r['donor'] for r in records if r['sample_id'] in train_set})
        if entry.get('training_donor_ids') != train_donors:
            raise ValueError(f'Upstream training donor ledger mismatch: {eid}')
        if not set(r['truth'] for r in records if r['sample_id'] in train_set) == set(LABELS):
            raise ValueError(f'Missing training class: {eid}')
        feature_path = bound_file(entry['feature_file'], run)
        if feature_path.stat().st_size != N_RECORDS * N_GENES * 8:
            raise ValueError(f'Feature byte count mismatch: {eid}')
        receipt_path = bound_file(entry['upstream_receipt'], run)
        receipt = read_json(receipt_path)
        expected_receipt = {
            'schema': UPSTREAM_SCHEMA, 'entry_id': eid, 'input_origin': 'raw_CEL',
            'protocol_sha256': protocol_sha256, 'legacy_joint_RMA_used': False,
            'upstream_fit_scope': 'training_only',
            'query_application': 'single_sample_frozen_target_effects_scales',
            'gene_aggregation': 'fixed_annotation_no_label_learning',
            'training_sample_ids': training, 'training_donor_ids': train_donors,
            'query_sample_ids': query, 'sample_ids': samples,
            'gene_ids_sha256': manifest['gene_ids_json']['sha256'],
            'feature_file': entry['feature_file'],
        }
        for key, value in expected_receipt.items():
            if receipt.get(key) != value:
                raise ValueError(f'Upstream receipt contract mismatch: {eid}/{key}')
        # The parent receipt attests mapping, sample-local background correction,
        # train-only target/effects/scales, per-sample application and exact-set
        # block assembly. Bind their new-run evidence without legacy discovery.
        if receipt.get('upstream_checks_passed') is not True:
            raise ValueError(f'Upstream checks have not passed: {eid}')
        validate_production_export_origin(receipt, run, eid, protocol_sha256)
        # Per-row feature identity is checked before any fit; same-row equality
        # across donors is held rather than silently counted as independent.
        X = np.memmap(feature_path, mode='r', dtype='<f8', shape=(N_RECORDS, N_GENES))
        if not np.isfinite(X).all():
            raise ValueError(f'Nonfinite feature matrix: {eid}')
        row_hash_owner = {}
        cross_donor_duplicate_rows = []
        for i in range(N_RECORDS):
            h = hashlib.sha256(X[i].tobytes()).hexdigest()
            if h in row_hash_owner and donors[row_hash_owner[h]] != donors[i]:
                cross_donor_duplicate_rows.append([samples[row_hash_owner[h]], samples[i]])
            else:
                row_hash_owner[h] = i
        if cross_donor_duplicate_rows:
            raise ValueError(f'Exact duplicate feature rows across donors require resolution: {eid}: {cross_donor_duplicate_rows[:3]}')
        del X
        checked.append({'entry': entry, 'feature_path': feature_path, 'receipt_path': receipt_path,
                        'training_n': len(training), 'query_n': len(query)})
    return manifest, records, np.array(genes), checked


def representation(X, program):
    X = np.asarray(X, dtype=np.float64)
    if program == 'RAW_FIXED':
        return X
    if program == 'RANK_FIXED':
        return (rankdata(X, axis=1, method='average') - 1) / (N_GENES - 1)
    raise ValueError('Unknown fixed representation')


def train_arrays(X, truth, donor, gene_ids, program):
    if X.ndim != 2 or X.shape[1] != N_GENES or not np.isfinite(X).all():
        raise ValueError('Training array must be finite Nx16295')
    if set(truth) != set(LABELS):
        raise ValueError('Missing canonical training class')
    counts = Counter(donor.tolist())
    w = np.array([1 / counts[d] for d in donor], dtype=float)
    w /= w.sum()
    mu = w @ X
    var = np.sum(w[:, None] * (X - mu) ** 2, axis=0)
    between = np.zeros(N_GENES)
    within = np.zeros(N_GENES)
    for label in LABELS:
        take = truth == label
        wc = w[take]
        xc = X[take]
        mass = wc.sum()
        center = wc @ xc / mass
        between += mass * (center - mu) ** 2
        within += np.sum(wc[:, None] * (xc - center) ** 2, axis=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        fisher = between / within
    eligible = (var > 0) & ~np.isnan(fisher) & ~np.isneginf(fisher)
    indices = np.flatnonzero(eligible)
    if len(indices) < 200:
        raise ValueError('Fewer than 200 eligible genes in this representation/training fold')
    selected = indices[np.argsort(-fisher[indices], kind='stable')[:200]]
    mean, scale = mu[selected], np.sqrt(var[selected])
    features = (X[:, selected] - mean) / scale
    model = LogisticRegression(penalty='l2', C=.1, solver='lbfgs', class_weight='balanced',
        multi_class='multinomial', fit_intercept=True, tol=1e-6, max_iter=5000, random_state=0)
    with threadpool_limits(limits=2), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model.fit(features, truth, sample_weight=w * len(w))
    fit_warnings = [{'category': warning.category.__name__, 'message': str(warning.message)} for warning in caught]
    if any(issubclass(warning.category, ConvergenceWarning) for warning in caught):
        raise RuntimeError('ConvergenceWarning; no model retry or altered iterations permitted')
    if not np.array_equal(model.classes_, LABELS):
        raise ValueError('Model class order mismatch')
    if not np.isfinite(model.coef_).all() or not np.isfinite(model.intercept_).all():
        raise ValueError('Nonfinite fitted classifier')
    return {'selected_U_indices': selected, 'selected_gene_ids': gene_ids[selected],
            'mean': mean, 'scale': scale, 'coef': model.coef_, 'intercept': model.intercept_,
            'class_ids': model.classes_, 'eligible_U_indices': indices,
            'fisher_scores': fisher, 'donor_weights': w, 'n_iter': model.n_iter_}, fit_warnings


def load_model(path, expected_protocol_sha256=None):
    with np.load(path, allow_pickle=False) as payload:
        model = {key: payload[key].copy() for key in payload.files}
    if str(model.get('schema', '')) != MODEL_SCHEMA:
        raise ValueError('Legacy/unsupported model schema rejected')
    metadata = json.loads(str(model['metadata_json']))
    if metadata.get('input_origin') != 'raw_CEL_training_only_frozen_PLM_gene_features':
        raise ValueError('Legacy/unknown model upstream origin rejected')
    if metadata.get('program') not in PROGRAMS:
        raise ValueError('Unknown model representation')
    if expected_protocol_sha256 and metadata.get('protocol_sha256') != expected_protocol_sha256:
        raise ValueError('Model protocol mismatch')
    if not np.array_equal(model.get('class_ids'), LABELS):
        raise ValueError('Model label axis mismatch')
    if model['full_gene_ids'].shape != (N_GENES,) or len(set(model['full_gene_ids'])) != N_GENES:
        raise ValueError('Model full gene axis mismatch')
    selected = model['selected_U_indices']
    if selected.shape != (200,) or selected.dtype.kind not in 'iu' or len(set(selected)) != 200 or np.any((selected < 0) | (selected >= N_GENES)):
        raise ValueError('Model selected feature indices invalid')
    if not np.array_equal(model['selected_gene_ids'], model['full_gene_ids'][selected]):
        raise ValueError('Model selected gene order mismatch')
    for key, shape in [('mean', (200,)), ('scale', (200,)), ('coef', (9, 200)), ('intercept', (9,))]:
        if model[key].shape != shape or not np.isfinite(model[key]).all():
            raise ValueError(f'Model array invalid: {key}')
    if np.any(model['scale'] <= 0):
        raise ValueError('Nonpositive model feature scale')
    model['metadata'] = metadata
    return model


def predict_array(model, X, gene_ids=None):
    if gene_ids is not None and not np.array_equal(np.asarray(gene_ids), model['full_gene_ids']):
        raise ValueError('Inference gene axis differs from model')
    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] != N_GENES or not np.isfinite(X).all():
        raise ValueError('Inference requires finite Nx16295 frozen-PLM gene features')
    represented = representation(X, model['metadata']['program'])
    z = (represented[:, model['selected_U_indices']] - model['mean']) / model['scale']
    scores = z @ model['coef'].T + model['intercept']
    scores -= scores.max(axis=1, keepdims=True)
    probability = np.exp(scores)
    probability /= probability.sum(axis=1, keepdims=True)
    if not np.isfinite(probability).all() or not np.allclose(probability.sum(axis=1), 1, atol=1e-12, rtol=0):
        raise ValueError('Nonfinite/invalid classifier probability')
    # Canonical LABELS axis is sorted, so argmax has the frozen ID tie break.
    return LABELS[np.argmax(probability, axis=1)], probability


def verify_one(model_path, X, gene_ids, protocol_sha256, verification_indices):
    model = load_model(model_path, protocol_sha256)
    subset = np.asarray(X[verification_indices], dtype=np.float64)
    pred, batch = predict_array(model, subset, gene_ids)
    single = np.vstack([predict_array(model, subset[i:i + 1], gene_ids)[1][0] for i in range(len(subset))])
    delta = float(np.max(np.abs(batch - single)))
    if delta > 1e-12 or not np.array_equal(pred, LABELS[np.argmax(single, axis=1)]):
        raise ValueError('Single-sample versus batch classifier inference mismatch')
    return {'single_batch_max_abs_probability_delta': delta,
            'probability_sha256': hashlib.sha256(np.round(batch, 12).astype('<f8').tobytes()).hexdigest(),
            'prediction': pred.tolist(), 'verification_sample_n': len(subset),
            'probability9': batch.tolist()}


def write_stratified_tables(output, records, predictions):
    """Explicit bank-by-class denominators/confusions after all attempts close."""
    bank_names = sorted({r['bank'] for r in records})
    class_rows, confusion_rows = [], []
    for program, pred in predictions.items():
        for bank in bank_names:
            indices = np.array([i for i, r in enumerate(records) if r['bank'] == bank])
            subset = [records[i] for i in indices]
            truth = np.array([r['truth'] for r in subset])
            donor = np.array([r['donor'] for r in subset])
            p = pred[indices]
            donor_axis = np.unique(donor)
            w = np.array([1 / np.sum(donor == d) / len(donor_axis) for d in donor])
            for label in LABELS:
                take, predicted = truth == label, p == label
                nt, npred = int(take.sum()), int(predicted.sum())
                tp = int((take & predicted).sum())
                cd = np.unique(donor[take])
                recall = float(np.mean([np.mean(p[take & (donor == d)] == label) for d in cd])) if nt else None
                class_rows.append({'program': program, 'bank': bank, 'class_id': str(label),
                    'truth_n': nt, 'truth_donors_n': len(cd), 'prediction_n': npred,
                    'true_positive_n': tp, 'failed_n': int((take & (p == 'FAIL')).sum()),
                    'count_recall': tp / nt if nt else None, 'donor_balanced_recall': recall,
                    'count_precision': tp / npred if npred else None})
                for prediction in list(LABELS) + ['FAIL']:
                    cell = take & (p == prediction)
                    confusion_rows.append({'program': program, 'bank': bank, 'truth': str(label),
                        'prediction': str(prediction), 'n': int(cell.sum()),
                        'bank_donor_equal_mass': float(w[cell].sum())})
    for name, rows in [('BANK_CLASS_METRICS.csv', class_rows), ('BANK_CONFUSION.csv', confusion_rows)]:
        with (output / name).open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)


def fit_route(run, protocol_path, protocol_sha256, manifest_path, output_name):
    run = Path(run).resolve(strict=True)
    if Path(output_name).name != output_name or output_name in {'', '.', '..'}:
        raise ValueError('output-name must name one new direct child directory')
    protocol_path = contained(protocol_path, run)
    protocol = validate_protocol(protocol_path, protocol_sha256, execute=True)
    manifest, records, genes, checked = validate_inputs(run, manifest_path, protocol_sha256, protocol['downstream_classifier'])
    output = run / output_name
    output.mkdir(exist_ok=False)
    models = output / 'models'
    models.mkdir()
    new_json(output / 'EXECUTION_LOCK.json', {'pid': os.getpid(), 'scope': 'twelve fixed classifier attempts only',
        'protocol': binding(protocol_path), 'input_manifest': binding(manifest_path),
        'classifier_code': binding(__file__), 'maximum_classifier_fits': 12})
    new_json(output / 'INPUT_BINDINGS.json', {'schema': INPUT_SCHEMA, 'manifest': manifest,
        'protocol': binding(protocol_path), 'manifest_binding': binding(manifest_path),
        'records_n': N_RECORDS, 'donors_n': N_DONORS, 'gene_n': N_GENES,
        'sources': [{'id': c['entry']['id'], 'feature_file': c['entry']['feature_file'],
                     'upstream_receipt': c['entry']['upstream_receipt'],
                     'training_sample_ids': c['entry']['training_sample_ids'],
                     'training_donor_ids': c['entry']['training_donor_ids'],
                     'query_sample_ids': c['entry']['query_sample_ids']} for c in checked]})
    truth = np.array([r['truth'] for r in records])
    donors = np.array([r['donor'] for r in records])
    sample = np.array([r['sample_id'] for r in records])
    fold = np.array([r['fold'] for r in records])
    predictions = {program: np.full(N_RECORDS, 'FAIL', dtype='<U4') for program in PROGRAMS}
    probabilities = {program: np.full((N_RECORDS, 9), np.nan) for program in PROGRAMS}
    fit_events = []
    attempt = 0
    for item in checked:
        entry = item['entry']
        eid = entry['id']
        train = np.ones(N_RECORDS, dtype=bool) if eid == 'final' else fold != int(eid[-1])
        query = ~train
        X = np.memmap(item['feature_path'], mode='r', dtype='<f8', shape=(N_RECORDS, N_GENES))
        for program in PROGRAMS:
            attempt += 1
            event = {'attempt': attempt, 'entry': eid, 'program': program,
                     'train_n': int(train.sum()), 'train_donors': len(set(donors[train])),
                     'query_n': int(query.sum()), 'status': 'PENDING'}
            # Progress never contains accuracy or intermediate held-out scores.
            print(json.dumps({'event': 'FIT_START', 'attempt': attempt, 'entry': eid, 'program': program}), flush=True)
            try:
                # A representation is computed sample-locally. All learned
                # eligibility, Fisher and scaling use training rows only.
                represented_train = representation(X[train], program)
                arrays, fit_warnings = train_arrays(represented_train, truth[train], donors[train], genes, program)
                del represented_train
                metadata = {'schema': MODEL_SCHEMA, 'program': program, 'entry_id': eid,
                    'role': 'full-development-research-artifact' if eid == 'final' else 'outer-fold-research-model',
                    'input_origin': 'raw_CEL_training_only_frozen_PLM_gene_features',
                    'protocol_sha256': protocol_sha256, 'input_manifest': binding(manifest_path),
                    'upstream_receipt': entry['upstream_receipt'], 'source_feature_file': entry['feature_file'],
                    'frozen_plan': FROZEN_PLAN,
                    'training_class_counts': dict(Counter(truth[train].tolist())),
                    'training_n': int(train.sum()), 'training_donors_n': len(set(donors[train])),
                    'unsupported_ids': UNSUPPORTED,
                    'anatomy': {'4219': 'target hippocampus only; narrower than source limbic category',
                                '4275': 'target putamen', '4391': 'target thalamus',
                                '9001': 'target substantia nigra'},
                    'assumptions': ['Only the exact fixed gene axis and this fitted upstream PLM state are supported.',
                                    'No cfRNA, arbitrary-platform, all-midbrain or twelve-region capability established.',
                                    'Research probability scores are not calibrated clinical probabilities.'],
                    'versions': {'python': sys.version, 'numpy': np.__version__,
                                 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}}
                model_path = models / f'{eid}_{program}.npz'
                new_npz(model_path, schema=np.array(MODEL_SCHEMA), metadata_json=np.array(json.dumps(metadata, allow_nan=False)),
                    full_gene_ids=genes, training_sample_ids=sample[train], training_donor_ids=donors[train],
                    query_sample_ids=sample[query], **arrays)
                loaded = load_model(model_path, protocol_sha256)
                for key, array in arrays.items():
                    same = np.array_equal(loaded[key], array, equal_nan=True) if array.dtype.kind in 'fci' else np.array_equal(loaded[key], array)
                    if not same:
                        raise ValueError(f'Serialized classifier array mismatch: {key}')
                # Exercise both held-out and training rows, at least one per
                # supported truth class, and the first/last sample.
                vix = sorted(set([0, N_RECORDS - 1] + [int(np.flatnonzero(truth == label)[0]) for label in LABELS]
                                 + np.flatnonzero(query)[:3].tolist()))
                local_verification = verify_one(model_path, X, genes, protocol_sha256, vix)
                child = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'verify',
                    '--run', str(run), '--model', str(model_path), '--manifest', str(Path(manifest_path).resolve()),
                    '--entry', eid, '--protocol-sha256', protocol_sha256,
                    '--indices-json', json.dumps(vix)], capture_output=True, text=True, check=True,
                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, timeout=180)
                child_verification = json.loads(child.stdout)
                if (child_verification['prediction'] != local_verification['prediction'] or
                    child_verification['verification_sample_n'] != local_verification['verification_sample_n'] or
                    child_verification['single_batch_max_abs_probability_delta'] > 1e-12 or
                    not np.allclose(child_verification['probability9'], local_verification['probability9'], rtol=0, atol=1e-12)):
                    raise ValueError('Fresh-process model verification differs')
                if eid != 'final':
                    p, prob = predict_array(loaded, X[query], genes)
                    predictions[program][query] = p
                    probabilities[program][query] = prob
                event.update(status='PASS', warnings=fit_warnings, model=binding(model_path),
                             serialization='exact array reload; allow_pickle=False; fresh process PASS',
                             inference_verification={key: value for key, value in local_verification.items()
                                                     if key not in {'prediction', 'probability9'}})
            except Exception as error:
                event.update(status='FAIL', error_type=type(error).__name__, error=str(error))
                # Failed outer queries remain FAIL/NaN in complete denominators.
            fit_events.append(event)
            with (output / 'TRAINING_EVENTS.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
            print(json.dumps({'event': 'FIT_COMPLETE', 'attempt': attempt, 'entry': eid,
                              'program': program, 'status': event['status']}), flush=True)
        del X
    if attempt != 12:
        raise ValueError('Frozen twelve-attempt budget did not close')
    new_npz(output / 'OUTER_OOF.npz', sample_id=sample, donor=donors, truth=truth, fold=fold,
        class_ids=LABELS, programs=np.array(PROGRAMS),
        predictions=np.stack([predictions[p] for p in PROGRAMS]),
        probability9=np.stack([probabilities[p] for p in PROGRAMS]))
    new_json(output / 'ALL_FITS_CLOSED.json', {'schema': 'braintrace.rawcel.fixed_nine_fits_closed.v1',
        'status': 'ALL_TWELVE_FIXED_ATTEMPTS_CLOSED', 'attempts': attempt,
        'successful_fits': sum(e['status'] == 'PASS' for e in fit_events),
        'failed_fits': sum(e['status'] != 'PASS' for e in fit_events), 'events': fit_events,
        'no_selection': True, 'no_legacy_results_read': True})
    # One joint reveal only after every fixed outer and final attempt closes.
    summary = load_metrics().evaluate(records, predictions, output / 'evaluation', bootstrap_n=2000, seed=20261026)
    write_stratified_tables(output / 'evaluation', records, predictions)
    new_json(output / 'DELIVERY.json', {'schema': 'braintrace.rawcel.fixed_nine_downstream_delivery.v1',
        'status': 'CLOSED_NO_MORE_CLASSIFIER_FITS', 'protocol': binding(protocol_path),
        'input_manifest': binding(manifest_path), 'attempts': attempt, 'no_selection': True,
        'development_summary': summary,
        'limitations': ['UKBEC remains historically exposed development.',
                       'Frozen train-only raw-CEL upstream processing is a new route, not legacy-joint-RMA compatibility.',
                       'Only nine supported labels; parietal, insula and pons unsupported.',
                       'Independent compatible-cohort/donor confirmation and all12-region development remain required.']})
    print(json.dumps({'status': 'CLOSED', 'output': str(output), 'summary': summary}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'fit'):
        command = subs.add_parser(name)
        command.add_argument('--run', required=True)
        command.add_argument('--protocol', required=True)
        command.add_argument('--protocol-sha256', required=True)
        command.add_argument('--manifest', required=True)
        if name == 'fit':
            command.add_argument('--execute', action='store_true', required=True,
                                 help='Explicit execution flag; protocol must separately authorize it')
            command.add_argument('--output-name', default='downstream_attempt01')
    verify = subs.add_parser('verify', help='Array serialization/inference checks only; no fitting')
    verify.add_argument('--run', required=True)
    verify.add_argument('--model', required=True)
    verify.add_argument('--manifest', required=True)
    verify.add_argument('--entry', choices=FOLDS, required=True)
    verify.add_argument('--protocol-sha256', required=True)
    verify.add_argument('--indices-json', required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        run = Path(args.run).resolve(strict=True)
        model_path = contained(args.model, run)
        manifest = read_json(contained(args.manifest, run))
        if manifest.get('schema') != INPUT_SCHEMA or manifest.get('protocol_sha256') != args.protocol_sha256:
            raise ValueError('Verification requires new manifest/protocol')
        entry = next(e for e in manifest['entries'] if e['id'] == args.entry)
        feature_path = bound_file(entry['feature_file'], run)
        genes = np.array(read_json(bound_file(manifest['gene_ids_json'], run)))
        X = np.memmap(feature_path, mode='r', dtype='<f8', shape=(N_RECORDS, N_GENES))
        indices = json.loads(args.indices_json)
        if not isinstance(indices, list) or not indices or len(set(indices)) != len(indices) or any(type(i) is not int or i < 0 or i >= N_RECORDS for i in indices):
            raise ValueError('Invalid verification sample indices')
        print(json.dumps(verify_one(model_path, X, genes, args.protocol_sha256, indices), allow_nan=False))
    elif args.command == 'validate':
        run = Path(args.run).resolve(strict=True)
        protocol = validate_protocol(contained(args.protocol, run), args.protocol_sha256, execute=False)
        _, records, genes, checked = validate_inputs(run, args.manifest, args.protocol_sha256, protocol['downstream_classifier'])
        print(json.dumps({'status': 'VALIDATED_NO_FITS', 'records': len(records), 'genes': len(genes),
                          'entries': [i['entry']['id'] for i in checked]}))
    else:
        fit_route(args.run, args.protocol, args.protocol_sha256, args.manifest, args.output_name)


if __name__ == '__main__':
    main()
