import json
import numpy as np

def transform_external(x,observed,state):
    if observed.sum()<2:
        valid=np.zeros(len(x),dtype=bool)
    else:
        valid=np.isfinite(x[:,observed]).all(axis=1)&(x[:,observed]>=0).all(axis=1)
        valid &= np.ptp(x[:,observed],axis=1)>1e-12
    safe=x.copy()
    safe[:,~observed]=state['train_mean'][~observed]
    safe[~valid]=state['train_mean']
    before=safe.copy();before-=state['train_mean'];before/=state['denominator']
    before[:,~observed]=0
    z=before.copy()
    if bool(state['clip_enabled']):np.clip(z,-5,5,out=z)
    valid &= np.isfinite(z).all(axis=1)
    return before,z,valid

def score(model,z,input_valid):
    safe=z.copy();safe[~input_valid]=0
    decisions=np.asarray(model.decision_function(safe),dtype=float)
    probabilities=np.asarray(model.predict_proba(safe),dtype=float)
    valid=np.asarray(input_valid,bool).copy();reasons=np.where(valid,'','invalid_input').astype(object)
    for i in range(len(z)):
        if not valid[i]:continue
        if not np.isfinite(decisions[i]).all():reason='nonfinite_decision'
        elif not np.isfinite(probabilities[i]).all() or (probabilities[i]<0).any() or not np.isclose(probabilities[i].sum(),1,atol=1e-10):reason='invalid_probabilities'
        elif np.ptp(probabilities[i])<=1e-12:reason='undifferentiated_probabilities'
        else:reason=''
        if reason:valid[i]=False;reasons[i]=reason
    return probabilities,decisions,valid,reasons

def endpoint_row(probabilities,classes,allowed,valid,reason):
    ranking=[str(classes[j]) for j in sorted(range(len(classes)),key=lambda j:(-float(probabilities[j]),str(classes[j])))] if valid else []
    ranks=[ranking.index(label)+1 for label in allowed if label in ranking]
    rank=min(ranks) if ranks else 0
    return {'evaluable':bool(valid),'failure_reason':str(reason),'predicted_class':ranking[0] if ranking else 'FAIL',
            'true_rank':rank,'Top1':float(rank==1),'Top3':float(0<rank<=3),'MRR':1/rank if rank else 0.,
            'ranking_json':json.dumps(ranking,ensure_ascii=False),
            'exact_tie_extra_classes':len(classes)-len(set(probabilities)) if np.isfinite(probabilities).all() else None}
