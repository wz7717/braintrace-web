"""Single-profile adapter for the existing PsychENCODE/Sousa2017 common-annotation counts.

The saved Ensembl91 -> common-human-ID correspondence is reused without modification.
Numerical operations mirror prepare_adult.py: sum mapped counts, divide by ALL 26514 rows,
multiply by 1e6, natural log1p, float32. No fitting, mapping search or symbol rescue.
"""
from pathlib import Path
from functools import lru_cache
import csv, io, json
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
CONTRACT='braintrace.psychencode_common_annotation_input.v1'
MAPPING='PsychENCODE_Sousa2017_Ensembl91_XSAnno_existing_20261101'
NORMALIZATION='public_common_annotation_ln1p_CPM'
COUNT_ROWS=26514

@lru_cache(maxsize=1)
def resources():
    genes=json.loads((ROOT/'science/lower/genes.json').read_text(encoding='utf-8-sig'))
    mapping=json.loads((ROOT/'science/lower/mappings'/f'{MAPPING}.json').read_text(encoding='utf-8-sig'))
    public_ids=json.loads((ROOT/'science/macaque/psychencode/PUBLIC_GENE_IDS.json').read_text(encoding='utf-8-sig'))
    if [m['feature'] for m in mapping]!=genes:raise ValueError('PsychENCODE mapping/feature axis mismatch.')
    return genes,mapping,public_ids

def is_count_csv(data):
    try:header=next(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
    except (UnicodeError,StopIteration,csv.Error):return False
    return len(header)==2 and header[0] in ('ID','gene_id') and (header[1]=='count' or header[1].startswith('RMB'))

def prepare_counts(data,suffix,sample_id):
    if suffix not in ('.tsv','.csv'):raise ValueError('PsychENCODE raw counts require TSV or CSV.')
    if not data or len(data)>8*1024**2:raise ValueError('Use one nonempty sample count file, at most 8 MiB.')
    reader=csv.reader(io.StringIO(data.decode('utf-8-sig')),delimiter='\t' if suffix=='.tsv' else ',')
    header=next(reader,None)
    if not header or len(header)!=2 or header[0] not in ('ID','gene_id') or not (header[1]=='count' or header[1].startswith('RMB')):
        raise ValueError('Use exactly two columns: ID and RMB sample name, or gene_id and count. Extract one rhesus column from the public matrix first.')
    submitted={}
    for row in reader:
        if len(row)!=2:raise ValueError('Every count row must have one gene ID and one count.')
        gene=row[0].split('|')[0]
        if gene in submitted:raise ValueError('Duplicate common-annotation gene ID.')
        try:value=float(row[1])
        except ValueError:raise ValueError('Counts must be numeric.') from None
        if not np.isfinite(value) or value<0 or value!=np.round(value):
            raise ValueError('Counts must be finite nonnegative integers, not normalized values.')
        submitted[gene]=value
    genes,mapping,public_ids=resources()
    if len(submitted)!=COUNT_ROWS or set(submitted)!=set(public_ids):
        raise ValueError('All 26514 frozen common-annotation IDs are required exactly once; a panel or changed gene universe is unsupported.')
    counts=np.asarray([[submitted[g]] for g in public_ids],dtype=np.float64)
    library=counts.sum(axis=0)
    if not np.isfinite(library).all() or not (library>0).all():raise ValueError('The common-annotation count total must be positive and finite.')
    index={g:i for i,g in enumerate(public_ids)}
    observed=np.array([m['covered'] for m in mapping],dtype=bool)
    x=np.full((1,len(genes)),np.nan,dtype=np.float32)
    # Same saved mapping and numerical statement order as the original prepare_adult.py.
    for j,m in enumerate(mapping):
        if m['covered']:
            v=counts[[index[t] for t in m['target_ids']]].sum(axis=0)/library
            v*=1e6;np.log1p(v,out=v);x[:,j]=v.astype(np.float32)
    return dict(x=x.T,observed=observed,genes=np.array(genes),samples=np.array([sample_id]),
        full_library_counts=library.copy(),public_common_annotation_counts_total=library.copy(),
        contract_version=np.array(CONTRACT),mapping_version=np.array(MAPPING),
        normalization=np.array(NORMALIZATION),full_count_rows=np.array(COUNT_ROWS))

def npz_bytes(fields):
    stream=io.BytesIO();np.savez_compressed(stream,**fields);return stream.getvalue()

def extract_column(matrix,sample_id):
    """Select one RMB column, preserving each count string and every matrix row."""
    if not sample_id.startswith('RMB'):raise ValueError('Only rhesus RMB columns are supported.')
    output=io.StringIO(newline='');writer=csv.writer(output,delimiter='\t',lineterminator='\n')
    with Path(matrix).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f,delimiter='\t');header=next(reader)
        if header.count(sample_id)!=1:raise ValueError('Requested RMB sample must occur exactly once in the matrix header.')
        i=header.index(sample_id);writer.writerow(['ID',sample_id])
        for row in reader:
            if len(row)!=len(header):raise ValueError('Count matrix row width differs from its header.')
            writer.writerow([row[0],row[i]])
    return output.getvalue().encode('utf-8')
