"""Extract and prepare ONE existing RMB sample; no training or inference."""
from pathlib import Path
import argparse, json, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from science.macaque.psychencode_adapter import extract_column,prepare_counts,npz_bytes

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix',type=Path,required=True)
    parser.add_argument('--sample-id',required=True)
    parser.add_argument('--out',type=Path,required=True,help='New directory; refuses overwrite.')
    args=parser.parse_args()
    if args.out.exists():parser.error('Output exists; choose a new directory.')
    data=extract_column(args.matrix,args.sample_id)
    fields=prepare_counts(data,'.tsv',args.sample_id)
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'COMMON_COUNTS.tsv').write_bytes(data)
    (args.out/'PREPARED_SINGLE_SAMPLE.npz').write_bytes(npz_bytes(fields))
    print(json.dumps({'sample_id':args.sample_id,'count_rows':26514,'normalization':str(fields['normalization']),
        'common_annotation_counts_total':float(fields['public_common_annotation_counts_total'][0]),
        'output':str(args.out),'fits':0,'inferences':0},ensure_ascii=False))
