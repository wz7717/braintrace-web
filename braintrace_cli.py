"""Single-sample CLI; uses exactly the same backend as the local web server."""
from pathlib import Path
import argparse, json
import three_tier_backend as backend

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--species', choices=['macaque', 'human'],
                        help='Must match the selected example. Defaults to its species with --example, or to macaque with --input.')
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input',type=Path)
    example_species = {example['id']: 'macaque' for example in backend.example_catalog()}
    example_species['human'] = 'human'
    source.add_argument('--example', choices=example_species,
                        help='Select an installed macaque example or the human example. Human live inference requires the GSM755211 CEL; --saved reads its packaged result.')
    parser.add_argument('--sample-id',default='query_001')
    parser.add_argument('--program', choices=['RAW_FIXED', 'RANK_FIXED', 'BOTH'],
                        help='Human program (default: RAW_FIXED). Omit for macaque to use floor_clip.')
    parser.add_argument('--saved',action='store_true',help='View saved output, without inference; requires --example.')
    parser.add_argument('--out',type=Path,required=True,help='New output directory; an existing directory is never overwritten.')
    args=parser.parse_args()
    if args.saved and not args.example:parser.error('--saved requires --example')
    if args.example is None:
        species = args.species or 'macaque'
    else:
        species = example_species[args.example]
        if args.species is not None and args.species != species:
            parser.error(f'--species {args.species} conflicts with --example {args.example}. '
                         f'Use --species {species} or omit --species.')
    if args.program is not None and species == 'macaque':
        parser.error(f'--program {args.program} is a human program and conflicts with macaque input. '
                     'Omit --program to use floor_clip.')
    program = args.program or ('RAW_FIXED' if species == 'human' else 'floor_clip')
    configs = ['RAW_FIXED', 'RANK_FIXED'] if program == 'BOTH' else [program]
    example_id = backend.HUMAN_EXAMPLE['id'] if args.example == 'human' else args.example
    args.out.mkdir(parents=True,exist_ok=False)
    try:
        if args.saved:result=backend.saved_example(species,configs,example_id)
        else:
            if args.example:
                info=backend.example_info(example_id, species=species)
                path=backend.ROOT/info['input'];sid=info['sample_id']
            else:path=args.input;sid=args.sample_id
            suffix='.cel.gz' if path.name.lower().endswith('.cel.gz') else path.suffix
            result=backend.run_macaque(path.read_bytes(),suffix,sid,configs) if species=='macaque' else backend.run_human(path.read_bytes(),suffix,sid,program)
            if args.example:
                result['saved_output_comparison']=backend.compare_example(result,example_id)
                if species=='macaque':backend.add_example_context(result,example_id)
        (args.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        (args.out/'scores.csv').write_text(backend.result_csv(result),encoding='utf-8',newline='')
    except Exception as exc:
        (args.out/'error.json').write_text(json.dumps({'status':'failed','error':str(exc)},ensure_ascii=False),encoding='utf-8')
        raise
    print(json.dumps({'status':'completed','output':str(args.out),'mode':result['mode'],'tiers':{k:v['status'] for k,v in result.get('tiers',{}).items()},'comparison':result.get('saved_output_comparison')},ensure_ascii=False))
if __name__=='__main__':main()
