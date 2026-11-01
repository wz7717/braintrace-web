"""Combine a source checkout and separately supplied assets into a NEW runtime.
Copies files only. Does not download, install, fit, score or alter the source/asset directories.
"""
from pathlib import Path
import argparse, json, shutil

def prepare(source, assets, output):
    source, assets, output = (Path(p).resolve() for p in (source, assets, output))
    if output.exists():
        raise ValueError('Output already exists; choose a new directory. Nothing was overwritten.')
    if output.is_relative_to(source) or output.is_relative_to(assets):
        raise ValueError('Place the runtime outside the source and asset directories.')
    required = ('ASSET_EDITION.json','science/lower/BEAMS.json','examples/three_tier/EXAMPLES.json',
                'science/macaque/floor_clip/model.joblib','science/human/PREDICTION_BUNDLE.json')
    for rel in required:
        if not (assets/rel).is_file(): raise ValueError('Missing runtime asset: '+rel)
    edition=json.loads((assets/'ASSET_EDITION.json').read_text(encoding='utf-8-sig'))
    scheme=json.loads((source/'metadata/SCHEME.json').read_text(encoding='utf-8-sig'))
    if edition['edition'] != scheme['deployment_asset_version'] or edition['scheme_id'] != scheme['scheme_id']:
        raise ValueError('Source and runtime-asset editions do not match.')
    plans={}
    for root in (source,assets):
        for p in root.rglob('*'):
            if not p.is_file(): continue
            rel=p.relative_to(root)
            if any(part in ('.git','__pycache__','.venv','venv','results','uploads','logs') for part in rel.parts):continue
            if p.name in ('runtime.local.json','Caddyfile') or p.name.startswith('.env') or p.suffix=='.pyc':continue
            if rel in plans: raise ValueError('Code/asset path collision: '+str(rel))
            plans[rel]=p
    if shutil.disk_usage(output.parent).free < sum(p.stat().st_size for p in plans.values())+10*1024**2:
        raise ValueError('Insufficient free space for the new runtime.')
    output.mkdir()
    for rel,p in plans.items():
        q=output/rel; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q)
    return {'runtime':str(output),'copied_files':len(plans),'reference_combinations':edition['combination_count'],
            'training':0,'inference':0,'environment_changes':0}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assets',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True,help='New directory in an existing parent directory.')
    args=ap.parse_args()
    try: print(json.dumps(prepare(Path(__file__).resolve().parents[1],args.assets,args.out),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc: ap.error(str(exc))
