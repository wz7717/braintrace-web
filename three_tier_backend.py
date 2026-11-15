"""Shared local web/CLI adapter for the selected frozen scheme. No fitting."""
from __future__ import annotations
import csv
import io
import json
import platform
import zipfile
from functools import lru_cache
import demo_backend as legacy
from demo_backend import ROOT, ATOL, np, read_json, validate_id, runtime_config, human_ready
from threadpoolctl import threadpool_limits
from science.macaque import psychencode_adapter as adult
from bounded_uploads import check_macaque_container

ROUTES = ('floor_clip',)
SCHEME = read_json(ROOT / 'metadata/SCHEME.json')
SCHEME_ID = SCHEME['scheme_id']
CONTRACT = 'braintrace.three_tier_input.v1'
run_human = legacy.run_human

def human_ready():
    return legacy.human_ready() and all((ROOT/'science/human'/rel).is_file() for rel in (
        'protocol/PROTOCOL.json','reference/FROZEN_UPSTREAM_STATE_INDEX.json','models/final_RAW_FIXED.npz','models/final_RANK_FIXED.npz'))

@lru_cache(maxsize=1)
def assets():
    genes = read_json(ROOT / 'science/lower/genes.json')
    head = read_json(ROOT / 'science/macaque/floor_clip/genes.json')
    index = {g:i for i,g in enumerate(genes)}
    beams = {tuple(sorted(b['networks'])):b['id'] for b in read_json(ROOT/'science/lower/BEAMS.json')}
    return genes, np.array([index[g] for g in head]), beams

def _scalar(z, name):
    if name not in z: return None
    v = np.asarray(z[name])
    if v.shape != (): return None
    return v.item()

def read_input(data, suffix, sample_id):
    """Full axis is required to consider lower tiers; absent metadata never implies compatibility."""
    validate_id(sample_id)
    if not data or len(data) > 8*1024**2:
        raise ValueError('Prepared macaque input must be nonempty and at most 8 MiB.')
    check_macaque_container(data, suffix)
    genes, head_rows, _ = assets()
    if suffix.lower()=='.tsv' or (suffix.lower()=='.csv' and adult.is_count_csv(data)):
        fields=adult.prepare_counts(data,suffix.lower(),sample_id)
        prepared=read_input(adult.npz_bytes(fields),'.npz',sample_id)
        prepared['input_type']='psychencode_common_annotation_counts'
        return prepared
    meta = {}
    common_total = None
    if suffix.lower() == '.npz':
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if len(z.infolist()) > 12 or sum(f.file_size for f in z.infolist()) > 16*1024**2:
                raise ValueError('Prepared NPZ exceeds the single-sample size limit.')
        with np.load(io.BytesIO(data), allow_pickle=False) as z:
            if 'x' not in z.files:
                x, observed, _, library = legacy.read_macaque_input(
                    data, suffix, sample_id, expected_genes=[genes[i] for i in head_rows])
                return dict(head_x=x, head_observed=observed, library=library, input_type='network_panel_5000', lower_status='input_insufficient', missing_fields=['full_21668_gene_axis','raw_full_library_logcpm','full_axis_observed_mask','mapping_version','contract_version'])
            required={'x','observed','genes','samples','full_library_counts'}
            if not required.issubset(z.files): raise ValueError('Full-axis NPZ needs x, observed, genes, samples and full_library_counts.')
            if z['genes'].shape!=(21668,) or z['genes'].tolist()!=genes:
                raise ValueError('Full-axis NPZ must use the supplied 21,668 gene IDs in exact order; a partial panel is insufficient.')
            if z['samples'].shape!=(1,) or z['samples'].dtype.kind not in 'US' or not str(z['samples'][0]):
                raise ValueError('Exactly one nonempty sample string is required.')
            x=z['x'].copy(); observed=z['observed'].copy(); library=z['full_library_counts'].copy()
            common_total=z['public_common_annotation_counts_total'].copy() if 'public_common_annotation_counts_total' in z.files else None
            meta={k:_scalar(z,k) for k in ('contract_version','mapping_version','normalization','full_count_rows')}
    elif suffix.lower()=='.csv':
        rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        if len(rows)==5000:
            x, observed, _, library = legacy.read_macaque_input(
                data, suffix, sample_id, expected_genes=[genes[i] for i in head_rows])
            return dict(head_x=x,head_observed=observed,library=library,input_type='network_panel_5000',lower_status='input_insufficient',missing_fields=['full_21668_gene_axis','raw_full_library_logcpm','full_axis_observed_mask','mapping_version','contract_version'])
        if len(rows)!=21668 or not {'gene_id','ln1p_cpm','observed','full_library_counts'}.issubset(rows[0]):
            raise ValueError('CSV needs exactly 5,000 Network rows or all 21,668 three-tier rows with gene_id, ln1p_cpm, observed and full_library_counts.')
        indexed={r['gene_id']:r for r in rows}
        if len(indexed)!=21668 or set(indexed)!=set(genes):
            raise ValueError('Full-axis CSV must contain every supplied gene ID exactly once.')
        rows=[indexed[g] for g in genes]
        if any(r['observed'] not in ('0','1') for r in rows):raise ValueError('observed must be 0 or 1.')
        observed=np.array([r['observed']=='1' for r in rows])
        x=np.array([[float(r['ln1p_cpm'])] for r in rows],dtype=np.float32)
        totals={float(r['full_library_counts']) for r in rows}
        if len(totals)!=1:raise ValueError('Use one full-library total on every row.')
        library=np.array(list(totals))
        if 'public_common_annotation_counts_total' in rows[0]:
            common_totals={float(r['public_common_annotation_counts_total']) for r in rows}
            if len(common_totals)!=1:raise ValueError('Use one common-annotation total on every row.')
            common_total=np.array(list(common_totals))
        for k in ('contract_version','mapping_version','normalization','full_count_rows'):
            vals={r.get(k,'') for r in rows}
            meta[k]=next(iter(vals)) if len(vals)==1 and '' not in vals else None
        if meta['full_count_rows'] is not None:
            try:meta['full_count_rows']=int(meta['full_count_rows'])
            except ValueError:meta['full_count_rows']=None
    else:
        raise ValueError('Use a prepared NPZ or CSV file.')
    if x.shape!=(21668,1) or x.dtype.kind!='f' or observed.shape!=(21668,) or observed.dtype!=bool:
        raise ValueError('Require x as floating-point 21668×1 and observed as a Boolean 21668-element mask.')
    if library.shape!=(1,) or not np.isfinite(library).all() or library[0]<=0:
        raise ValueError('A positive full-library count total is required.')
    x=x.astype(np.float32)
    if not np.isfinite(x[observed]).all() or (x[observed]<0).any():
        raise ValueError('Observed values must be finite nonnegative natural ln(1+CPM).')
    missing=[k for k,v in meta.items() if v is None]
    reason='input_incompatible' if missing else 'compatible'
    if not missing:
        is_adult=meta['mapping_version']==adult.MAPPING
        expected_contract=adult.CONTRACT if is_adult else CONTRACT
        expected_normalization=adult.NORMALIZATION if is_adult else 'full_library_ln1p_CPM'
        if meta['contract_version']!=expected_contract:missing.append('supported_contract_version')
        if meta['normalization']!=expected_normalization:missing.append(expected_normalization)
        if is_adult and (common_total is None or common_total.shape!=(1,) or not np.array_equal(common_total,library)):
            missing.append('matching_public_common_annotation_counts_total')
        if meta['mapping_version'] not in SCHEME['mapping_versions']:
            missing.append('supported_mapping_version')
        else:
            mapping=read_json(ROOT/'science/lower/mappings'/(meta['mapping_version']+'.json'))
            expected=np.array([r['covered'] for r in mapping])
            if not np.array_equal(observed,expected):missing.append('observed_mask_matching_declared_mapping')
            expected_rows=26514 if is_adult else (30807 if meta['mapping_version'].startswith('GSE128537_') else 22515)
            if meta['full_count_rows']!=expected_rows:missing.append('full_count_rows_matching_declared_mapping')
        if missing:reason='input_incompatible'
    head=x[head_rows,0].reshape(1,-1).copy();head[:,~observed[head_rows]]=0
    return dict(head_x=head,head_observed=observed[head_rows],library=float(library[0]),x=x[:,0],observed=observed,
                input_type='full_axis_21668',metadata=meta,lower_status=reason,missing_fields=missing)

def input_summary(prepared):
    o=prepared['head_observed']
    is_adult=prepared.get('metadata',{}).get('mapping_version')==adult.MAPPING
    return {'normalization_background':'public_common_annotation_26514' if is_adult else 'full_library',
            'public_common_annotation_counts_total':prepared['library'] if is_adult else None,
            'input_type':prepared['input_type'],'observed_features':int(o.sum()),'missing_features':int((~o).sum()),
            'full_library_counts':prepared['library'],'lower_input_status':prepared['lower_status'],
            'lower_missing_fields':prepared['missing_fields'],
            'lower_observed_features':int(prepared['observed'].sum()) if 'observed' in prepared else None}

def _not_run(status, reason, **extra):
    return {k:dict(status=status,reason=reason,classes=[],ranking=[],scores=[],**extra) for k in ('Group','Exact')}

def lower_tiers(prepared,network):
    genes,_,beams=assets();beam=network['ranking'][:3]
    if prepared['lower_status']!='compatible':
        return _not_run(prepared['lower_status'],prepared['lower_status'],missing_fields=prepared['missing_fields']),None
    beam_id=beams.get(tuple(sorted(beam)))
    if not beam_id:return _not_run('reference_unavailable','candidate_combination_reference_not_provided'),None
    try:
        folder=ROOT/'science/lower/beams'/beam_id
        rules=read_json(folder/'RULES_AND_MEMBERS.json')
        with np.load(folder/'INPUT.npz',allow_pickle=False) as z:
            b={'candidates':z['regions'].tolist(),'order':z['gene_rows'].copy(),'ref':z['reference'].copy(),'ann':rules['annotations'],'folder':beam_id}
        q=prepared['x'].copy()
        q[~prepared['observed']]=np.load(ROOT/'science/lower/SOURCE_RAW_MEAN.npy',allow_pickle=False)[~prepared['observed']]
        scoring=legacy.load_module('braintrace_existing_lower',ROOT/'science/lower/scoring.py')
        with threadpool_limits(limits=1):
            row=scoring.lower_predict(b,q,np.array(genes),'',observed_mask=prepared['observed'])
        return tiers_from_row(row,beam_id),beam_id
    except Exception as exc:
        # Preserve Network; never substitute another reference, model or saved example.
        print('Lower inference failed: '+type(exc).__name__,flush=True)
        return _not_run('failed','lower_inference_failed'),beam_id

def tiers_from_row(row,beam_id):
    def parse(key):return json.loads(row[key])
    group=parse('Group_ranking_json');members=parse('Group_members_json');cand=parse('candidate_regions_json')
    result={}
    for tier in ('Group','Exact'):
        valid=row[tier+'_valid'] in (True,'True')
        result[tier]={'status':'succeeded' if valid else 'not_evaluable','reason':row[tier+'_failure'] or None,
                      'classes':group if tier=='Group' else cand,'ranking':parse(tier+'_ranking_json'),
                      'scores':parse('Group_scores_json' if tier=='Group' else 'exact_fusion_candidate_order_json'),
                      'score_type':'pearson_top200_member_max' if tier=='Group' else 'z_fusion_0.25_top50_0.75_top100',
                      'reference_id':beam_id}
    result['Group'].update(members=members,member_counts=[len(m) for m in members])
    result['Exact'].update(corr50=parse('corr50_candidate_order_json'),corr100=parse('corr100_candidate_order_json'),corr200=parse('corr200_candidate_order_json'))
    return result

def run_macaque(data,suffix,sample_id,routes):
    if list(routes)!=['floor_clip']:raise ValueError('The current three-tier scheme uses only floor_clip.')
    import scipy, sklearn, joblib
    if (platform.python_version(),np.__version__,scipy.__version__,sklearn.__version__)!=('3.11.9','1.26.4','1.13.1','1.5.2'):
        raise ValueError('Live inference requires the documented, pinned scientific runtime.')
    p=read_input(data,suffix,sample_id)
    folder=ROOT/'science/macaque/floor_clip'
    model=joblib.load(folder/'model.joblib')
    with np.load(folder/'state.npz',allow_pickle=False) as z:state={k:z[k].copy() for k in z.files}
    kernel=legacy.load_module('braintrace_head',ROOT/'science/macaque/inference.py')
    with threadpool_limits(limits=1):
        _,transformed,valid=kernel.transform_external(p['head_x'],p['head_observed'],state)
        probability,decision,valid,reason=kernel.score(model,transformed,valid)
    if not valid[0]:raise ValueError('Frozen Network inference rejected this sample: '+str(reason[0]))
    network=legacy.result_item(model.classes_,probability[0],decision[0])
    lower,beam_id=lower_tiers(p,network)
    result={'schema':'braintrace.three_tier_result.v1','species':'macaque','sample_id':sample_id,'mode':'live_frozen_inference',
            'scheme_id':SCHEME_ID,'input_type':p['input_type'],'input_metadata':p.get('metadata',{}),'input_summary':input_summary(p),
            'new_fits':0,'predictions':{'floor_clip':network},'candidate_networks':network['ranking'][:3],'reference_id':beam_id,
            'tiers':{'Network':dict(network,status='succeeded',reason=None,score_type='model_score'),**lower},
            'warnings':['Scores are candidate rankings, not calibrated anatomical correctness probabilities.',
                        'Group and Exact rank independently within the same Network Top3; Group does not gate Exact.',
                        'All 120 unordered Network Top3 combinations have frozen references. Lower output still requires compatible input and evaluable signal.']}
    if p.get('metadata',{}).get('mapping_version')==adult.MAPPING:
        result['warnings'].append('Normalization uses all 26514 public common-annotation rows, not the original unfiltered sequencing library; exploratory input adaptation.')
    result.update({k:pval for k,pval in input_summary(p).items() if k in ('observed_features','missing_features','full_library_counts')})
    json.dumps(result,allow_nan=False)
    return result

def example_info(example_id='GSE128537'):
    for info in read_json(ROOT/'examples/three_tier/EXAMPLES.json'):
        if info['id']==example_id:return info
    raise ValueError('Unknown saved example.')

def saved_example(species,configurations,example_id='GSE128537'):
    if species=='human':return legacy.saved_example(species,configurations)
    if list(configurations)!=['floor_clip']:raise ValueError('Only the current floor_clip scheme is available.')
    info=example_info(example_id);row=read_json(ROOT/info['saved_row'])
    network=legacy.result_item(json.loads(row['head_classes_json']),json.loads(row['head_probabilities_json']))
    _,_,beams=assets();beam_id=beams[tuple(sorted(network['ranking'][:3]))]
    saved_input=ROOT/info.get('prepared_input',info['input'])
    p=read_input(saved_input.read_bytes(),saved_input.suffix,info['sample_id'])
    result={'schema':'braintrace.three_tier_result.v1','species':'macaque','sample_id':info['sample_id'],'mode':'saved_example','scheme_id':SCHEME_ID,
            'input_type':'full_axis_21668','input_metadata':p['metadata'],'input_summary':input_summary(p),'new_fits':0,
            'predictions':{'floor_clip':network},'candidate_networks':network['ranking'][:3],'reference_id':beam_id,
            'tiers':{'Network':dict(network,status='succeeded',reason=None,score_type='model_score'),**tiers_from_row(row,beam_id)}}
    result['warnings']=['Scores are candidate rankings, not calibrated anatomical correctness probabilities.',
                        'Group and Exact rank independently within the same Network Top3; Group does not gate Exact.',
                        'All 120 unordered Network Top3 combinations have frozen references. Lower output still requires compatible input and evaluable signal.']
    result.update({k:v for k,v in input_summary(p).items() if k in ('observed_features','missing_features','full_library_counts')})
    if p.get('metadata',{}).get('mapping_version')==adult.MAPPING:
        result['warnings'].append('Normalization uses all 26514 public common-annotation rows, not the original unfiltered sequencing library; exploratory input adaptation.')
    add_example_context(result,example_id)
    return result

def add_example_context(result,example_id):
    info=example_info(example_id);row=read_json(ROOT/info['saved_row'])
    result['example_context']={k:row[k] for k in ('cohort','GSM','region_original','fine_endpoint','reason')}
    result['example_context']['allowed_regions']=json.loads(row['allowed_regions_json'])
    parents=read_json(ROOT/'science/lower/REGION_PARENT.json')
    result['reference_labels']=sorted({parents[r] for r in result['example_context']['allowed_regions']})

def compare_example(result,example_id='GSE128537'):
    if result['species']=='human':return legacy.compare_example(result)
    expected=saved_example('macaque',['floor_clip'],example_id);details={}
    for tier,item in result['tiers'].items():
        other=expected['tiers'][tier]
        axes=item['classes']==other['classes'];ranks=item['ranking']==other['ranking']
        members=item.get('members')==other.get('members')
        delta=float(np.max(np.abs(np.asarray(item['scores'])-other['scores']))) if axes and item['scores'] else None
        corr=max(float(np.max(np.abs(np.array(item[k])-other[k]))) for k in ('corr50','corr100','corr200')) if tier=='Exact' and axes else None
        passed=axes and ranks and members and item['status']==other['status'] and delta is not None and delta<=ATOL and (corr is None or corr<=ATOL)
        details[tier]={'pass':bool(passed),'same_class_axis':axes,'same_ranking':ranks,'same_members':members,'max_score_difference':delta,'max_decision_difference':corr}
    return {'pass':all(d['pass'] for d in details.values()),'absolute_tolerance':ATOL,'relative_tolerance':0,'configurations':details,
            'scope':'The selected saved example only; no cohort performance re-estimation.'}

def result_csv(result):
    out=io.StringIO(newline='');writer=csv.writer(out)
    writer.writerow(['sample_id','species','mode','scheme_id','input_type','mapping_version','configuration','tier','status','reason','reference_id','rank','class_id','score','score_type','decision','members_json','member_count','warnings_json','normalization_background','public_common_annotation_counts_total'])
    views=[('floor_clip',k,v) for k,v in result['tiers'].items()] if 'tiers' in result else [(k,'Human',dict(v,status='succeeded',score_type='model_score')) for k,v in result['predictions'].items()]
    for config,tier,item in views:
        base=[result['sample_id'],result['species'],result['mode'],result.get('scheme_id','human_frozenPLM9'),result.get('input_type','human_CEL'),result.get('input_metadata',{}).get('mapping_version',''),config,tier,item['status'],item.get('reason') or '',item.get('reference_id',result.get('reference_id','')) or '']
        warnings=json.dumps({'warnings':result.get('warnings',[]),'missing_fields':item.get('missing_fields',[])},ensure_ascii=False)
        background=[result.get('input_summary',{}).get('normalization_background',''),result.get('input_summary',{}).get('public_common_annotation_counts_total') or '']
        if not item['ranking']:writer.writerow(base+['','','',item.get('score_type',''),'','','',warnings]+background)
        for rank,cid in enumerate(item['ranking'],1):
            i=item['classes'].index(cid);members=item.get('members',[[]]*len(item['classes']))[i]
            writer.writerow(base+[rank,cid,repr(item['scores'][i]),item['score_type'],repr(item['decision'][i]) if 'decision' in item else '',json.dumps(members),len(members) if tier=='Group' else '',warnings]+background)
    return '\ufeff'+out.getvalue()
