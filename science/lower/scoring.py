"""Verbatim existing inference functions; see docs/CODE_PROVENANCE.md."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from typing import Any, Sequence
NUMERICAL_SIGNAL_TOLERANCE = 1e-12

def rank_metrics(ranking,truth):
    pos=ranking.index(truth)+1 if truth in ranking else 0
    return int(pos==1),int(0<pos<=3),1/pos if pos else 0.

def lower_predict(b,xq,genes,truth,observed_mask=None):
    cand=b['candidates'];order=b['order'];ref=b['ref'];ann=b['ann']
    q=xq[order];observed=pd.Series(xq,index=genes) if observed_mask is None else pd.Series(xq[observed_mask],index=genes[observed_mask])
    a=trace_corr(ref[:50],q[:50]);c=trace_corr(ref[:100],q[:100]);g=trace_corr(ref,q)
    fused=.25*zscore(a)+.75*zscore(c)
    ereason=signal_reason(genes[order[:50]].tolist(),observed,q[:50],a)
    if not ereason:ereason=signal_reason(genes[order[:100]].tolist(),observed,q[:100],c)
    if not ereason and ranking_is_undifferentiated(fused):ereason='exact_fusion_undifferentiated'
    greason=signal_reason(genes[order].tolist(),observed,q,g)
    # Preserve production ordering: rows first in reverse argsort of exact fusion,
    # then stable descending Group Top200 score and first occurrence of each group.
    initial=np.argsort(fused)[::-1].tolist() if not ereason else list(range(len(cand)))
    exact=[cand[j] for j in initial] if not ereason else []
    groups=[];members=[];gscores=[]
    if not greason:
        for j in sorted(initial,key=lambda j:float(g[j]),reverse=True):
            name=ann[cand[j]]['resolution_group']
            if name not in groups:
                groups.append(name);members.append(ann[cand[j]]['group_members']);gscores.append(float(g[j]))
        if len(groups)>1 and ranking_is_undifferentiated(np.array(gscores)):
            greason='group_aggregated_scores_undifferentiated';groups=[];members=[];gscores=[]
    truth_group=next((groups[j] for j,m in enumerate(members) if truth in m),'')
    eh1,eh3,emrr=rank_metrics(exact,truth);gh1,gh3,gmrr=rank_metrics(groups,truth_group)
    return {'candidate_regions_json':json.dumps(cand),'n_candidate_regions':len(cand),
            'n_candidate_groups':len({ann[r]['resolution_group'] for r in cand}),
            'Group_valid':not bool(greason),'Group_failure':greason or '',
            'Exact_valid':not bool(ereason),'Exact_failure':ereason or '',
            'Group_ranking_json':json.dumps(groups),'Group_members_json':json.dumps(members),'Group_scores_json':json.dumps(gscores),
            'Exact_ranking_json':json.dumps(exact),'exact_fusion_candidate_order_json':json.dumps(fused.tolist()),
            'corr50_candidate_order_json':json.dumps(a.tolist()),'corr100_candidate_order_json':json.dumps(c.tolist()),
            'corr200_candidate_order_json':json.dumps(g.tolist()),
            'Group_hit1':gh1,'Group_hit3':gh3,'Group_MRR':gmrr,'Exact_hit1':eh1,'Exact_hit3':eh3,'Exact_MRR':emrr,
            'group_top1_member_count':len(members[0]) if members else 0,
            'group_top3_union_member_count':len(set().union(*map(set,members[:3]))) if members else 0,
            'true_group_members_json':json.dumps(ann[truth]['group_members']) if truth in ann else '[]',
            'exact_score_tie_count':len(fused)-len(set(fused)),
            'group_region_score_tie_count':len(g)-len(set(g)),
            'beam_artifact':b['folder']}

def trace_corr(A: np.ndarray, b: np.ndarray) -> np.ndarray:
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    if A.ndim != 2 or b.ndim != 1 or A.shape[0] != b.size:
        raise ValueError("Pearson reference and query dimensions do not match")
    if not np.isfinite(A).all() or not np.isfinite(b).all():
        raise ValueError("Pearson reference and query must contain only finite values")
    b0 = b - b.mean()
    A0 = A - A.mean(axis=0, keepdims=True)
    num = (A0 * b0[:, None]).sum(axis=0)
    den = np.sqrt((A0 ** 2).sum(axis=0) * (b0 ** 2).sum() + 1e-12)
    corr = num / den
    if not np.isfinite(corr).all():
        raise ValueError("Pearson calculation produced nonfinite scores")
    return corr

def signal_reason(genes: list[str], observed: pd.Series, vector: np.ndarray, scores: np.ndarray) -> str | None:
    signal = panel_signal_evidence(genes, observed, vector)
    if not signal['evaluable']:
        return str(signal['reason'])
    if ranking_is_undifferentiated(scores):
        return 'scores_do_not_distinguish_candidates'
    return None

def _finite_standard_deviation(values: np.ndarray) -> float | None:
    if not values.size or not np.isfinite(values).all():
        return None
    scale = float(np.max(np.abs(values)))
    result = 0.0 if scale == 0 else float(np.std(values / scale) * scale)
    return result if np.isfinite(result) else None

def panel_signal_evidence(
    genes: Sequence[str],
    observed: pd.Series,
    scoring_values: np.ndarray,
) -> dict[str, Any]:
    """Describe actual panel observations separately from zero-filled scores.

    This only rejects undefined or numerically constant Pearson evidence. It is
    not a calibrated coverage, detection or out-of-distribution threshold.
    """
    panel = pd.Index(genes).astype(str)
    present = panel.isin(observed.index)
    values = observed.reindex(panel[present]).to_numpy(dtype=float)
    vector = np.asarray(scoring_values, dtype=float)
    finite = np.isfinite(values)
    diagnostics: dict[str, Any] = {
        "n_panel_genes": int(len(panel)),
        "n_observed_genes": int(present.sum()),
        "n_finite_observed_genes": int(finite.sum()),
        "n_nonzero_observed_genes": int(np.count_nonzero(values[finite])),
        "observed_standard_deviation": _finite_standard_deviation(values),
        "scoring_standard_deviation": _finite_standard_deviation(vector),
    }
    reason = None
    if not present.any():
        reason = "no_observed_panel_genes"
    elif not finite.all():
        reason = "nonfinite_observed_panel_values"
    elif len(values) < 2:
        reason = "fewer_than_two_observed_panel_genes"
    elif float(np.ptp(values)) <= NUMERICAL_SIGNAL_TOLERANCE:
        reason = "constant_observed_panel_values"
    elif not np.isfinite(vector).all():
        reason = "nonfinite_scoring_values"
    elif vector.size < 2 or float(np.ptp(vector)) <= NUMERICAL_SIGNAL_TOLERANCE:
        reason = "constant_scoring_vector"
    diagnostics["evaluable"] = reason is None
    diagnostics["reason"] = reason
    return diagnostics

def ranking_is_undifferentiated(scores: np.ndarray) -> bool:
    values = np.asarray(scores, dtype=float)
    return (
        values.size < 2
        or not np.isfinite(values).all()
        or float(np.ptp(values)) <= NUMERICAL_SIGNAL_TOLERANCE
    )

def zscore(scores: np.ndarray) -> np.ndarray:
    scores = np.asarray(scores, dtype=np.float64)
    std = float(scores.std())
    if std <= 1e-12:
        return np.zeros_like(scores)
    return (scores - float(scores.mean())) / std

