"""Portable, no-fit CEL -> frozenPLM9 research prediction entry point.

Each sample follows the same one-sample path. No cohort target, probe effect,
scale, feature or classifier is fitted here. A locked, fully hash-bound bundle
and an explicit compatible R runtime are required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
for _key in THREAD_ENV:
    os.environ[_key] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import numpy as np
import scipy
import sklearn
from threadpoolctl import threadpool_limits

SCHEMA = "braintrace.rawcel.frozen_plm9.prediction_bundle.v1"
LABELS = ["4009", "4132", "4180", "4219", "4275", "4391", "4696", "9001", "9512"]
UNSUPPORTED = ["4084", "4268", "9131"]
PROGRAM_CHOICES = ("RAW_FIXED", "RANK_FIXED", "BOTH")
ROLES = {"reference", "annotation", "gene_ids", "protocol", "raw_model", "rank_model",
         "implementation", "classifier_helper", "r_driver", "gzip_helper", "prediction_entry",
         "upstream_state", "upstream_receipt"}
WARNINGS = [
    "RESEARCH_ONLY: frozenPLM9 supports nine labels; it does not replace the original twelve-class system.",
    "Unsupported regions: parietal (4084), insula (4268), pons (9131).",
    "Target hippocampus (4219) is narrower than the original source limbic category.",
    "Only the locked Human Exon 1.0 ST bulk-tissue input contract is supported; cfRNA/arbitrary-platform readiness is unestablished.",
    "Nine scores sum to one over the supported labels; they are uncalibrated research model scores, not a rejection test for unsupported anatomy.",
    "Normal adult eligibility and anatomical identity require external metadata; a valid CEL header alone cannot establish them.",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def new_json(path: Path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def hex_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def bundle_file(root: Path, item: dict) -> Path:
    if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
        raise ValueError("Each bundle role needs exactly path, bytes, sha256")
    if not isinstance(item["path"], str) or Path(item["path"]).is_absolute():
        raise ValueError("Bundle paths must be relative to the manifest directory")
    path = (root / item["path"]).resolve(strict=True)
    if root not in path.parents or not path.is_file():
        raise ValueError("Bundle member escapes its directory or is not a file")
    if type(item["bytes"]) is not int or item["bytes"] < 1 or not hex_sha(item["sha256"]):
        raise ValueError("Invalid member size/hash binding")
    if path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
        raise ValueError(f"Bundle member hash/size mismatch: {path}")
    return path


def load_helper(path: Path):
    spec = importlib.util.spec_from_file_location("braintrace_locked_frozen_plm9_classifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The training helper sets its own fit thread defaults on import. Production
    # inference restores the entry-point contract and constrains loaded BLAS too.
    for key in THREAD_ENV:
        os.environ[key] = "1"
    if not callable(getattr(module, "load_model", None)) or not callable(getattr(module, "predict_array", None)):
        raise ValueError("Bound classifier helper lacks the inspected inference API")
    return module


def validate_bundle(path: Path):
    path = path.resolve(strict=True)
    root = path.parent
    bundle = read_json(path)
    if bundle.get("schema") != SCHEMA or bundle.get("status") != "LOCKED_RESEARCH_ONLY":
        raise ValueError("Require a locked frozenPLM9 research prediction bundle")
    if bundle.get("synthetic_fixture") is not False:
        raise ValueError("Production prediction bundle must explicitly declare synthetic_fixture=false")
    if bundle.get("method") != "frozenPLM9" or bundle.get("class_ids") != LABELS or bundle.get("unsupported_ids") != UNSUPPORTED:
        raise ValueError("Bundle method or nine-label anatomy contract differs")
    if bundle.get("primary_program") != "RAW_FIXED" or bundle.get("secondary_programs") != ["RANK_FIXED"] or bundle.get("program_selection") != "explicit_predeclared_no_score_selection":
        raise ValueError("Bundle primary/secondary program contract differs")
    if set(bundle.get("files", {})) != ROLES:
        raise ValueError("Missing/unknown bundle file roles")
    files = {role: bundle_file(root, item) for role, item in bundle["files"].items()}
    if files["prediction_entry"] != Path(__file__).resolve():
        # The entry script may be launched from a second identical reviewed copy.
        if sha(Path(__file__).resolve()) != bundle["files"]["prediction_entry"]["sha256"]:
            raise ValueError("Executing prediction entry differs from the locked bundle")
    dimensions = bundle.get("dimensions", {})
    for name in ("genes", "clusters", "PM_probes"):
        if type(dimensions.get(name)) is not int or dimensions[name] < 1:
            raise ValueError(f"Missing positive frozen dimension: {name}")
    if dimensions["genes"] != 16295:
        raise ValueError("This classifier route requires the fixed 16295-gene axis")
    if bundle.get("kernel") != {"application": "one_sample_one_column_frozen_target_effects_scales",
                                "gene_aggregation": "arithmetic_mean_cluster_estimates",
                                "upstream_fit_allowed": False, "threads": 1}:
        raise ValueError("Unsupported inference kernel contract")
    protocol_sha = sha(files["protocol"])
    if bundle.get("protocol_sha256") != protocol_sha:
        raise ValueError("Bundle protocol binding differs")
    protocol = read_json(files["protocol"])
    down = protocol.get("downstream_classifier", {})
    if down.get("n_genes") != dimensions["genes"] or down.get("gene_ids_json_sha256") != sha(files["gene_ids"]):
        raise ValueError("Protocol/gene-axis binding differs")
    state = read_json(files["upstream_state"])
    receipt = read_json(files["upstream_receipt"])
    for key, value in {"schema": "braintrace.rawcel.frozen_upstream_state.v1", "entry_id": "final",
                       "status": "PASS_FROZEN_REFERENCE_AND_GENE_EXPORT", "protocol_sha256": protocol_sha,
                       "synthetic_fixture": False}.items():
        if state.get(key) != value or (key == "synthetic_fixture" and state.get(key) is not False):
            raise ValueError(f"Final upstream state differs: {key}")
    for key, role in (("frozen_reference", "reference"), ("annotation", "annotation"), ("gene_ids", "gene_ids")):
        if state.get(key, {}).get("sha256") != bundle["files"][role]["sha256"] or state.get(key, {}).get("bytes") != bundle["files"][role]["bytes"]:
            raise ValueError(f"Final upstream state does not bind bundled {role}")
    if receipt.get("schema") != "braintrace.rawcel.frozen_plm_gene_export.v1" or receipt.get("entry_id") != "final" or receipt.get("synthetic_fixture") is not False or receipt.get("protocol_sha256") != protocol_sha:
        raise ValueError("Final upstream export receipt differs")
    state_bindings = receipt.get("upstream_state_bindings", [])
    if len(state_bindings) != 1 or state_bindings[0].get("sha256") != bundle["files"]["upstream_state"]["sha256"] or state_bindings[0].get("bytes") != bundle["files"]["upstream_state"]["bytes"]:
        raise ValueError("Export receipt does not bind the final upstream state")
    genes = read_json(files["gene_ids"])
    if not isinstance(genes, list) or len(genes) != dimensions["genes"] or any(not isinstance(g, str) or not g for g in genes) or len(set(genes)) != len(genes):
        raise ValueError("Invalid complete frozen gene axis")
    runtime = bundle.get("runtime", {})
    actual = {"python": platform.python_version(), "python_implementation": platform.python_implementation(),
              "numpy": np.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__}
    if runtime.get("python") != actual:
        raise ValueError(f"Pinned Python/package kernel differs: actual={actual}")
    r = runtime.get("R", {})
    if not isinstance(r.get("version_string"), str) or not r["version_string"] or set(r.get("packages", {})) != {"preprocessCore", "affxparser", "digest", "jsonlite"}:
        raise ValueError("Missing pinned R/runtime package contract")
    helper = load_helper(files["classifier_helper"])
    models = {}
    for role, program in (("raw_model", "RAW_FIXED"), ("rank_model", "RANK_FIXED")):
        model = helper.load_model(files[role], protocol_sha)
        if model["metadata"].get("program") != program or model["metadata"].get("entry_id") != "final":
            raise ValueError("Only the matching final research model is allowed")
        if model["metadata"].get("role") != "full-development-research-artifact":
            raise ValueError("Expected the full-development research artifact")
        if model["metadata"].get("synthetic_fixture") is True:
            raise ValueError("Synthetic classifier fixtures cannot enter production prediction")
        model_upstream = model["metadata"].get("upstream_receipt", {})
        if model_upstream.get("sha256") != bundle["files"]["upstream_receipt"]["sha256"] or model_upstream.get("bytes") != bundle["files"]["upstream_receipt"]["bytes"]:
            raise ValueError("Classifier was not fitted from the bound final upstream export")
        if not np.array_equal(model["full_gene_ids"], np.asarray(genes)):
            raise ValueError("Model full gene order differs from frozen annotation JSON")
        if model["metadata"].get("versions", {}).get("numpy") != actual["numpy"] or model["metadata"].get("versions", {}).get("scipy") != actual["scipy"] or model["metadata"].get("versions", {}).get("sklearn") != actual["sklearn"]:
            raise ValueError("Model training package versions differ from pinned inference packages")
        if model.get("query_sample_ids", np.array(["MISSING"])).size != 0:
            raise ValueError("Final model unexpectedly declares held-out query rows")
        samples = model.get("training_sample_ids")
        donors = model.get("training_donor_ids")
        if samples is None or donors is None or samples.ndim != 1 or donors.shape != samples.shape or not samples.size or len(set(samples.tolist())) != samples.size:
            raise ValueError("Missing/invalid final model training identity ledger")
        models[program] = model
    if not np.array_equal(models["RAW_FIXED"]["training_sample_ids"], models["RANK_FIXED"]["training_sample_ids"]) or not np.array_equal(models["RAW_FIXED"]["training_donor_ids"], models["RANK_FIXED"]["training_donor_ids"]):
        raise ValueError("Raw/rank final training populations differ")
    return bundle, files, genes, helper, models


def input_records(path: Path, sample_id=None):
    path = path.resolve(strict=True)
    if path.name.lower().endswith(".csv"):
        if sample_id is not None:
            raise ValueError("--sample-id applies only to one direct CEL input")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows or not {"sample_id", "cel_path"}.issubset(rows[0]):
            raise ValueError("Batch CSV needs nonempty sample_id,cel_path columns")
        result = [{"sample_id": r["sample_id"], "cel_path": str((path.parent / r["cel_path"]).resolve(strict=True))}
                  for r in rows]
    else:
        stem = re.sub(r"[.]cel(?:[.]gz)?$", "", path.name, flags=re.IGNORECASE)
        default = stem if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", stem) else "sample_000001"
        result = [{"sample_id": sample_id or default, "cel_path": str(path)}]
    seen = set()
    for row in result:
        sid, cel = row["sample_id"], Path(row["cel_path"])
        if not isinstance(sid, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", sid) is None or sid in seen:
            raise ValueError("Sample IDs must be unique safe ASCII identifiers of at most 128 characters")
        seen.add(sid)
        if not cel.is_file() or not re.search(r"[.]cel(?:[.]gz)?$", cel.name, re.IGNORECASE) or cel.stat().st_size < 1:
            raise ValueError(f"Missing, empty or unsupported raw CEL input: {cel}")
    return result


def owned_cel(source: Path, temp_root: Path, helper, sample_id: str):
    before = source.stat()
    source_sha = sha(source)
    owned = Path(tempfile.mkdtemp(prefix=f"fplm9_{sample_id}_", dir=temp_root))
    owner = {"schema": "braintrace.prediction_owned_temp.v1", "pid": os.getpid(),
             "sample_id": sample_id, "source_sha256": source_sha}
    new_json(owned / "OWNER.json", owner)
    local = owned / "sample.CEL"
    if source.name.lower().endswith(".cel.gz"):
        try:
            expansion = helper.expand(source, local, owned / "EXPANSION.json", source_sha)
        except Exception as exc:
            raise RuntimeError(f"Gzip materialization failed for {source}; owned partial preserved at {owned}: {exc}") from exc
        expected = {"OWNER.json", "sample.CEL", "EXPANSION.json"}
    else:
        with source.open("rb") as src, local.open("xb") as dest:
            shutil.copyfileobj(src, dest, length=2**20)
        if sha(local) != source_sha:
            raise ValueError(f"Copied raw CEL SHA mismatch; owned partial preserved: {owned}")
        expansion = {"schema": "braintrace.raw_cel_snapshot.v1", "source_sha256": source_sha,
                     "expanded_sha256": source_sha, "expanded_bytes": local.stat().st_size,
                     "gzip_crc_through_eof": None, "scope": "byte-identical owned ASCII raw CEL snapshot"}
        new_json(owned / "SNAPSHOT.json", expansion)
        expected = {"OWNER.json", "sample.CEL", "SNAPSHOT.json"}
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or sha(source) != source_sha:
        raise ValueError(f"Input changed while materializing; owned snapshot preserved: {owned}")
    return local, owned, owner, expected, {"source_path": str(source), "source_bytes": before.st_size,
        "source_sha256": source_sha, "owned_ASCII_CEL": str(local), "expansion": expansion}


def clean_owned(owned: Path, owner: dict, expected: set):
    if read_json(owned / "OWNER.json") != owner or {p.name for p in owned.iterdir()} != expected:
        raise ValueError(f"Owned temp identity/content changed; cleanup refused: {owned}")
    for name in expected:
        path = owned / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Unexpected owned temporary member; cleanup refused")
    for name in expected:
        (owned / name).unlink()
    owned.rmdir()


def select_programs(models, program="RAW_FIXED"):
    if program not in PROGRAM_CHOICES:
        raise ValueError("Unknown explicitly selected prediction program")
    names = ("RAW_FIXED", "RANK_FIXED") if program == "BOTH" else (program,)
    if any(name not in models for name in names):
        raise ValueError("Requested prediction program is not available")
    return {name: models[name] for name in names}


def predict_features(helper, models, feature, genes, program="RAW_FIXED"):
    models = select_programs(models, program)
    feature = np.asarray(feature, dtype=np.float64)
    if feature.shape != (1, len(genes)) or not np.isfinite(feature).all():
        raise ValueError("Expected exactly one finite full-axis frozen-PLM gene row")
    result = {}
    with threadpool_limits(limits=1):
        for program, model in models.items():
            prediction, score = helper.predict_array(model, feature, genes)
            if score.shape != (1, 9) or not np.isfinite(score).all():
                raise ValueError("Classifier returned invalid nine-score array")
            result[program] = {"prediction": str(prediction[0]), "class_ids": LABELS,
                               "score9": score[0].tolist()}
    return result


def run(args):
    bundle_path = Path(args.bundle).resolve(strict=True)
    bundle, files, genes, helper, models = validate_bundle(bundle_path)
    training_model = models["RAW_FIXED"]
    # Both bound artifacts are validated, then only the predeclared requested
    # program(s) reach predict_array. No score is used to choose this routing.
    models = select_programs(models, args.program)
    records = input_records(Path(args.input), args.sample_id)
    rscript = Path(args.rscript).resolve(strict=True)
    if not rscript.is_file():
        raise ValueError("Explicit Rscript executable is required")
    temp_root = Path(args.temp_root).resolve()
    if not str(temp_root).isascii():
        raise ValueError("--temp-root must be ASCII for the native CEL reader")
    temp_root.mkdir(parents=True, exist_ok=True)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    new_json(out / "START.json", {"schema": "braintrace.rawcel.prediction_run.v1",
        "method": "frozenPLM9", "status": "STARTED_NO_FITTING", "pid": os.getpid(),
        "bundle_path": str(bundle_path), "bundle_sha256": sha(bundle_path),
        "inputs": records, "runtime": bundle["runtime"], "warnings": WARNINGS,
        "chosen_program": args.program, "executed_programs": list(models),
        "program_selection": "explicit_predeclared_no_score_selection",
        "input_or_cohort_reference_fit": False})
    gzip_spec = importlib.util.spec_from_file_location("braintrace_locked_gzip_expander", files["gzip_helper"])
    gzip_helper = importlib.util.module_from_spec(gzip_spec)
    gzip_spec.loader.exec_module(gzip_helper)
    all_rows = []
    active = None
    try:
        for i, record in enumerate(records, 1):
            active = record
            sample_dir = out / f"sample_{i:06d}_{record['sample_id']}"
            sample_dir.mkdir(exist_ok=False)
            local, owned, owner, expected, materialized = owned_cel(Path(record["cel_path"]), temp_root,
                                                                   gzip_helper, record["sample_id"])
            new_json(sample_dir / "INPUT_RECEIPT.json", materialized)
            request = {"schema": "braintrace.rawcel.frozen_prediction_request.v1", "sample_id": record["sample_id"],
                "CEL_path": str(local), "CEL_sha256": materialized["expansion"]["expanded_sha256"],
                "files": {key: {"path": str(value), **{k: v for k, v in bundle["files"][key].items() if k != "path"}}
                          for key, value in files.items()},
                "runtime_R": bundle["runtime"]["R"], "dimensions": bundle["dimensions"],
                "protocol_sha256": bundle["protocol_sha256"],
                "training_sample_ids": training_model["training_sample_ids"].tolist(),
                "training_donor_ids": training_model["training_donor_ids"].tolist(),
                "chosen_program": args.program, "executed_programs": list(models),
                "gene_ids": genes, "upstream_fit_allowed": False, "synthetic_fixture": False}
            request_path = sample_dir / "REQUEST.json"
            new_json(request_path, request)
            command = [str(rscript), "--vanilla", str(files["r_driver"]), "--request", str(request_path), "--out", str(sample_dir)]
            if args.rlib:
                command += ["--library", str(Path(args.rlib).resolve(strict=True))]
            env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "LC_CTYPE": "en_US.UTF-8",
                   **{key: "1" for key in THREAD_ENV}}
            child = subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
            with (sample_dir / "R_STDOUT.txt").open("x", encoding="utf-8") as stream:
                stream.write(child.stdout)
            with (sample_dir / "R_STDERR.txt").open("x", encoding="utf-8") as stream:
                stream.write(child.stderr)
            if child.returncode != 0:
                raise RuntimeError(f"R frozen application failed for {record['sample_id']}; owned CEL preserved: {owned}; {child.stderr[-2000:]}")
            qc = read_json(sample_dir / "UPSTREAM_QC.json")
            feature_path = sample_dir / "GENE_FEATURES.f64le"
            if qc.get("status") != "PASS_SINGLE_SAMPLE_FROZEN_APPLICATION" or qc.get("sample_id") != record["sample_id"] or qc.get("upstream_fit_allowed") is not False or qc.get("gene_ids") != genes:
                raise ValueError("R application receipt/identity contract differs")
            if feature_path.stat().st_size != 8 * len(genes) or qc.get("feature_sha256") != sha(feature_path):
                raise ValueError("R exported gene feature hash/size mismatch")
            feature = np.fromfile(feature_path, dtype="<f8").reshape(1, len(genes))
            predictions = predict_features(helper, models, feature, genes, program=args.program)
            new_json(sample_dir / "PREDICTION.json", {"schema": "braintrace.rawcel.frozen_plm9.prediction.v1",
                "status": "RESEARCH_PREDICTION_COMPLETE", "sample_id": record["sample_id"],
                "bundle_sha256": sha(bundle_path), "feature_sha256": sha(feature_path),
                "chosen_program": args.program, "executed_programs": list(models),
                "predictions": predictions, "warnings": WARNINGS, "new_fit_count": 0})
            clean_owned(owned, owner, expected)
            for program, prediction in predictions.items():
                all_rows.append({"sample_id": record["sample_id"], "program": program,
                    "chosen_program": args.program,
                    "prediction": prediction["prediction"],
                    **{f"score_{label}": value for label, value in zip(LABELS, prediction["score9"])},
                    "status": "RESEARCH_ONLY"})
            print(json.dumps({"sample_id": record["sample_id"], "status": "RESEARCH_PREDICTION_COMPLETE"}), flush=True)
        with (out / "PREDICTIONS.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]), lineterminator="\n")
            writer.writeheader(); writer.writerows(all_rows)
        new_json(out / "COMPLETE.json", {"schema": "braintrace.rawcel.prediction_complete.v1",
            "status": "RESEARCH_PREDICTIONS_COMPLETE", "samples": len(records), "rows": len(all_rows),
            "bundle_sha256": sha(bundle_path), "new_fit_count": 0,
            "chosen_program": args.program, "executed_programs": list(models),
            "batch_policy": "ordered repetition of the identical single-sample application", "warnings": WARNINGS})
    except Exception as exc:
        new_json(out / "FAILED.json", {"status": "FAILED_PARTIAL_OUTPUT_PRESERVED", "sample": active,
            "error_type": type(exc).__name__, "error": str(exc), "new_fit_count": 0,
            "chosen_program": args.program, "executed_programs": list(models),
            "traceback": traceback.format_exc(), "pending_inputs_are_not_silently_skipped": True})
        raise
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="Locked prediction bundle JSON")
    parser.add_argument("--input", required=True, help="One .CEL/.CEL.gz or CSV with sample_id,cel_path")
    parser.add_argument("--sample-id", help="Optional explicit ID for one direct CEL")
    parser.add_argument("--program", choices=PROGRAM_CHOICES, default="RAW_FIXED",
                        help="Explicit predeclared program; default RAW_FIXED; never selected from cohort scores")
    parser.add_argument("--out", required=True, help="New output directory; existing path refused")
    parser.add_argument("--rscript", required=True, help="Explicit compatible Rscript executable")
    parser.add_argument("--rlib", help="Optional explicit compatible R library directory")
    parser.add_argument("--temp-root", required=True, help="ASCII root for one owned temporary CEL at a time")
    args = parser.parse_args()
    try:
        out = run(args)
    except Exception as exc:
        print(json.dumps({"status": "REJECTED_OR_FAILED", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"status": "RESEARCH_PREDICTIONS_COMPLETE", "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
