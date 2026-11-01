"""One existing human CEL and one adult macaque sample; no fitting/cohort evaluation."""
from pathlib import Path
import argparse
import json
import os
import platform
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import three_tier_backend as backend
from portability.human_linux import run_one


def main(a):
    assert platform.system()=='Linux'
    out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
    root=backend.ROOT
    started=time.monotonic()
    prediction=run_one(root/'examples/human/GSM755211.CEL.gz','GSM755211','BOTH',out/'human',
        Path(a.prefix)/'R/bin/Rscript',Path(a.prefix)/'rlib',out/'temporary')
    observed=backend.np.fromfile(out/'human/GENE_FEATURES.f64le',dtype='<f8')
    expected=backend.np.fromfile(a.human_features,dtype='<f8')
    assert observed.shape==expected.shape==(16295,)
    feature_delta=float(backend.np.max(backend.np.abs(observed-expected)))
    assert feature_delta<=1e-10,feature_delta
    result={'species':'human','sample_id':'GSM755211','mode':'live_frozen_inference','new_fits':0,
        'predictions':{k:backend.legacy.result_item(v['class_ids'],v['score9']) for k,v in prediction['predictions'].items()}}
    human_compare=backend.compare_example(result)
    assert human_compare['pass'],human_compare
    human_seconds=time.monotonic()-started
    info=backend.example_info('PsychENCODE_HIP')
    path=root/info['input']
    started=time.monotonic()
    macaque=backend.run_macaque(path.read_bytes(),path.suffix,info['sample_id'],['floor_clip'])
    macaque_compare=backend.compare_example(macaque,'PsychENCODE_HIP')
    assert macaque_compare['pass'],macaque_compare
    (out/'macaque.json').write_text(json.dumps(macaque,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'platform':platform.platform(),'python':platform.python_version(),
        'R_version':prediction['R_version'],'feature_count':16295,'feature_atol':1e-10,
        'feature_max_abs_difference':feature_delta,'human_seconds':human_seconds,'human':human_compare,
        'macaque_seconds':time.monotonic()-started,'macaque':macaque_compare,
        'training':0,'cohort_rerun':False,'human_samples':1,'macaque_samples':1}
    (out/'LINUX_PORTABILITY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--prefix',required=True)
    p.add_argument('--human-features',required=True)
    main(p.parse_args())
