"""Extract one column from an existing prepared full-axis file; no mapping or normalization."""
from pathlib import Path
import argparse, io, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import three_tier_backend as b

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--sample-id',required=True)
    p.add_argument('--mapping',choices=[m for m in b.SCHEME['mapping_versions'] if m.startswith(('GSE128537_', 'GSE179328_'))],required=True,
                   help='Full-library inputs only. Use prepare_psychencode_sample.py for adult common-annotation counts.')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();b.validate_id(a.sample_id)
    if a.output.exists():p.error('Output exists; use a new file.')
    with b.np.load(a.input,allow_pickle=False) as z:
        samples=z['samples'].tolist()
        if samples.count(a.sample_id)!=1:p.error('Sample ID must occur exactly once.')
        i=samples.index(a.sample_id)
        if z['x'].shape!=(21668,len(samples)) or z['full_library_counts'].shape!=(len(samples),):p.error('Unexpected full-axis input dimensions.')
        payload=dict(x=z['x'][:,i:i+1],genes=z['genes'],samples=z['samples'][i:i+1],observed=z['observed'],full_library_counts=z['full_library_counts'][i:i+1],
                     contract_version=b.np.array(b.CONTRACT),mapping_version=b.np.array(a.mapping),normalization=b.np.array('full_library_ln1p_CPM'),full_count_rows=b.np.array(30807 if a.mapping.startswith('GSE128537_') else 22515))
    buf=io.BytesIO();b.np.savez_compressed(buf,**payload)
    prepared=b.read_input(buf.getvalue(),'.npz',a.sample_id)
    if prepared['lower_status']!='compatible':p.error('Input is not compatible: '+str(prepared['missing_fields']))
    with a.output.open('xb') as f:f.write(buf.getvalue())
    print('Extracted one existing sample. No normalization, mapping or inference performed.')
if __name__=='__main__':main()
