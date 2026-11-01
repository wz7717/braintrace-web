"""Single-sample CLI; uses exactly the same backend as the local web server."""
from pathlib import Path
import argparse, json
import three_tier_backend as backend

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--species',choices=['macaque','human'],default='macaque')
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input',type=Path)
    source.add_argument('--example',choices=['GSE128537','GSE179328','PsychENCODE_AMY','PsychENCODE_HIP','human'])
    parser.add_argument('--sample-id',default='query_001')
    parser.add_argument('--program',choices=['RAW_FIXED','RANK_FIXED','BOTH'],default='RAW_FIXED')
    parser.add_argument('--saved',action='store_true',help='View saved output, without inference; requires --example.')
    parser.add_argument('--out',type=Path,required=True,help='New output directory; an existing directory is never overwritten.')
    args=parser.parse_args()
    if args.saved and not args.example:parser.error('--saved requires --example')
    species=('human' if args.example=='human' else 'macaque') if args.example else args.species
    configs=(['RAW_FIXED','RANK_FIXED'] if args.program=='BOTH' else [args.program]) if species=='human' else ['floor_clip']
    args.out.mkdir(parents=True,exist_ok=False)
    try:
        if args.saved:result=backend.saved_example(species,configs,args.example)
        else:
            if args.example:
                info=backend.example_info(args.example) if species=='macaque' else {'input':'examples/human/GSM755211.CEL.gz','sample_id':'GSM755211'}
                path=backend.ROOT/info['input'];sid=info['sample_id']
            else:path=args.input;sid=args.sample_id
            suffix='.cel.gz' if path.name.lower().endswith('.cel.gz') else path.suffix
            result=backend.run_macaque(path.read_bytes(),suffix,sid,configs) if species=='macaque' else backend.run_human(path.read_bytes(),suffix,sid,args.program)
            if args.example:
                result['saved_output_comparison']=backend.compare_example(result,args.example)
                if species=='macaque':backend.add_example_context(result,args.example)
        (args.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        (args.out/'scores.csv').write_text(backend.result_csv(result),encoding='utf-8',newline='')
    except Exception as exc:
        (args.out/'error.json').write_text(json.dumps({'status':'failed','error':str(exc)},ensure_ascii=False),encoding='utf-8')
        raise
    print(json.dumps({'status':'completed','output':str(args.out),'mode':result['mode'],'tiers':{k:v['status'] for k,v in result.get('tiers',{}).items()},'comparison':result.get('saved_output_comparison')},ensure_ascii=False))
if __name__=='__main__':main()
