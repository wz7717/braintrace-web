# Single-CEL, application-only R worker for the portable frozenPLM9 entry.
# It never calls a reference-fitting function and never accepts cohort peers.

fp_stop <- function(...) stop(..., call. = FALSE)
fp_chr <- function(x) {
  if (is.character(x)) return(x)
  if (is.list(x) && all(vapply(x, function(z) is.character(z) && length(z) == 1L, logical(1))))
    return(unlist(x, use.names = FALSE))
  fp_stop("Expected JSON string array")
}
fp_new_json <- function(x, path) {
  if (file.exists(path)) fp_stop("Refusing existing prediction output: ", path)
  jsonlite::write_json(x, path, pretty = TRUE, auto_unbox = TRUE, digits = NA, na = "null", null = "null")
}
fp_sha <- function(path) digest::digest(file = path, algo = "sha256")
fp_summary <- function(x) list(n = length(x), minimum = min(x), maximum = max(x),
  mean = mean(x), SD = stats::sd(x), finite_n = sum(is.finite(x)))

fp_apply_one <- function(request_file, outdir) {
  for (p in c("digest", "jsonlite", "affxparser", "preprocessCore"))
    if (!requireNamespace(p, quietly = TRUE)) fp_stop("Missing pinned package: ", p)
  r <- jsonlite::read_json(request_file, simplifyVector = FALSE)
  if (!identical(r$schema, "braintrace.rawcel.frozen_prediction_request.v1") ||
      !identical(r$upstream_fit_allowed, FALSE) || !identical(r$synthetic_fixture, FALSE))
    fp_stop("Only production application requests with fitting disabled are accepted")
  if (!is.character(r$sample_id) || length(r$sample_id) != 1L || !nzchar(r$sample_id) ||
      !is.character(r$CEL_path) || length(r$CEL_path) != 1L || !file.exists(r$CEL_path) ||
      any(as.integer(charToRaw(enc2utf8(r$CEL_path))) > 127L))
    fp_stop("One existing ASCII CEL snapshot and sample ID are required")
  if (!identical(R.version.string, r$runtime_R$version_string)) fp_stop("Pinned R version differs")
  packages <- c("preprocessCore", "affxparser", "digest", "jsonlite")
  if (!identical(sort(names(r$runtime_R$packages)), sort(packages))) fp_stop("Pinned package contract differs")
  for (p in packages) if (!identical(as.character(utils::packageVersion(p)), r$runtime_R$packages[[p]]))
    fp_stop("Pinned package version differs: ", p)
  roles <- c("reference", "annotation", "gene_ids", "protocol", "raw_model", "rank_model", "implementation",
             "classifier_helper", "r_driver", "gzip_helper", "prediction_entry", "upstream_state", "upstream_receipt")
  if (!identical(sort(names(r$files)), sort(roles))) fp_stop("Bundle file roles differ")
  files <- setNames(vector("list", length(roles)), roles)
  for (role in roles) {
    b <- r$files[[role]]
    if (!is.list(b) || !identical(sort(names(b)), sort(c("path", "bytes", "sha256"))) ||
        !is.character(b$path) || length(b$path) != 1L || !file.exists(b$path) || dir.exists(b$path) ||
        !is.numeric(b$bytes) || length(b$bytes) != 1L ||
        !identical(as.double(file.info(b$path)$size), as.double(b$bytes)) ||
        !is.character(b$sha256) || length(b$sha256) != 1L ||
        !identical(fp_sha(b$path), b$sha256)) fp_stop("Bundle hash/size differs: ", role)
    files[[role]] <- b$path
  }
  this <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1L])
  if (length(this) != 1L || is.na(this) || !identical(fp_sha(this), r$files$r_driver$sha256))
    fp_stop("Executing R driver differs from the locked bundle")
  source(files$implementation, local = .GlobalEnv, encoding = "UTF-8")
  if (!identical(fp_sha(files$protocol), r$protocol_sha256)) fp_stop("Protocol SHA differs")
  reference <- fplm_load_reference(files$reference)
  if (!identical(reference$r_version, R.version.string) ||
      !identical(reference$package_version, r$runtime_R$packages$preprocessCore))
    fp_stop("Frozen reference kernel version differs")
  provenance <- reference$provenance_binding
  if (!is.list(provenance) || !identical(provenance$entry_id, "final") ||
      !identical(provenance$synthetic_fixture, FALSE) ||
      !identical(provenance$protocol_sha256, r$protocol_sha256))
    fp_stop("Only the protocol-bound production final reference is allowed")
  if (!identical(provenance$annotation$sha256, fp_sha(files$annotation)) ||
      !identical(provenance$gene_ids$sha256, fp_sha(files$gene_ids)))
    fp_stop("Frozen reference provenance does not bind this annotation/gene axis")
  if (!identical(reference$training_sample_ids, fp_chr(r$training_sample_ids)) ||
      !identical(reference$training_donor_ids, fp_chr(r$training_donor_ids)))
    fp_stop("Reference and final model training identities differ")
  ann <- readRDS(files$annotation)
  genes <- fp_chr(jsonlite::read_json(files$gene_ids, simplifyVector = FALSE))
  if (!is.list(ann) || !identical(ann$schema, "braintrace.fixed_annotation.v1") ||
      !identical(ann$axis, reference$axis) || !identical(ann$cluster_ids, names(reference$axis$groups)) ||
      !identical(ann$entrez_ids, genes) || !identical(genes, fp_chr(r$gene_ids)) ||
      !is.list(ann$gene_cluster_indices) || !identical(names(ann$gene_cluster_indices), genes) ||
      !is.list(ann$gene_cluster_ids) || !identical(names(ann$gene_cluster_ids), genes))
    fp_stop("Reference, annotation and model gene/cluster axes differ")
  if (length(genes) != r$dimensions$genes || length(ann$cluster_ids) != r$dimensions$clusters ||
      length(reference$axis$probe_ids) != r$dimensions$PM_probes)
    fp_stop("Frozen dimensions differ")
  for (g in seq_along(genes)) {
    ix <- ann$gene_cluster_indices[[g]]
    if (!is.numeric(ix) || !length(ix) || anyNA(ix) || any(ix != as.integer(ix)) ||
        any(ix < 1 | ix > length(ann$cluster_ids)) || anyDuplicated(ix) ||
        !identical(ann$cluster_ids[ix], ann$gene_cluster_ids[[g]])) fp_stop("Invalid fixed aggregation membership")
  }
  memberships <- unlist(ann$gene_cluster_indices, use.names = FALSE)
  if (anyDuplicated(memberships) || !identical(sort(as.integer(memberships)), seq_along(ann$cluster_ids)))
    fp_stop("Static gene aggregation must account for every cluster exactly once")
  protocol <- jsonlite::read_json(files$protocol, simplifyVector = FALSE)
  if (!identical(as.integer(protocol$downstream_classifier$n_genes), as.integer(length(genes))) ||
      !identical(protocol$downstream_classifier$gene_ids_json_sha256, fp_sha(files$gene_ids)))
    fp_stop("Protocol gene axis differs")
  destinations <- file.path(outdir, c("GENE_FEATURES.f64le", "UPSTREAM_QC.json"))
  if (!dir.exists(outdir) || any(file.exists(destinations))) fp_stop("Prediction output must be new")
  cel_sha <- fp_sha(r$CEL_path)
  if (!identical(cel_sha, r$CEL_sha256)) fp_stop("Materialized CEL SHA differs")
  start <- proc.time()[[3L]]
  cel <- fplm_read_cel(r$CEL_path, reference$axis)
  # All PMs in the fixed axis are validated. No mask, outlier, sample, probe or
  # class is removed as a function of this input or of a companion sample.
  background <- fplm_background_one(cel$pm, reference$axis$probe_ids)
  normalized <- fplm_normalize_one(background, reference$axis$probe_ids, reference$target)
  cluster <- fplm_summarize_one(normalized, reference)
  if (!identical(names(cluster), ann$cluster_ids) || any(!is.finite(cluster))) fp_stop("Invalid frozen cluster output")
  features <- numeric(length(genes)); names(features) <- genes
  for (g in seq_along(genes))
    features[g] <- rowMeans(matrix(cluster[ann$gene_cluster_indices[[g]]], nrow = 1L))[1L]
  if (any(!is.finite(features))) fp_stop("Nonfinite fixed gene aggregation")
  if (!identical(fp_sha(r$CEL_path), cel_sha)) fp_stop("CEL snapshot changed during application")
  con <- file(destinations[1L], "wb")
  writeBin(as.double(features), con, size = 8L, endian = "little"); close(con)
  if (file.info(destinations[1L])$size != length(genes) * 8) fp_stop("Gene feature byte length differs")
  # Explicit reload verifies the exact serialization consumed by Python.
  con <- file(destinations[1L], "rb")
  loaded <- readBin(con, double(), n = length(features), size = 8L, endian = "little"); close(con)
  if (!identical(loaded, unname(features))) fp_stop("Gene feature serialization differs")
  qc <- list(schema = "braintrace.rawcel.single_frozen_application.v1", status = "PASS_SINGLE_SAMPLE_FROZEN_APPLICATION",
    method = "frozenPLM9", sample_id = r$sample_id, upstream_fit_allowed = FALSE, new_fit_count = 0L,
    request_sha256 = fp_sha(request_file), CEL_sha256 = cel_sha,
    frozen_reference_sha256 = fp_sha(files$reference), annotation_sha256 = fp_sha(files$annotation),
    protocol_sha256 = r$protocol_sha256, feature_sha256 = fp_sha(destinations[1L]),
    gene_ids = genes, full_fixed_PM_axis_finite = TRUE, raw_PM = fp_summary(cel$pm),
    background_PM = fp_summary(background), normalized_log2_PM = fp_summary(normalized),
    frozen_clusters = fp_summary(cluster), gene_features = fp_summary(features),
    raw_CEL_header_as_observed = cel$header,
    returned_outlier_indices_n = length(cel$outlier_indices), returned_masked_indices_n = length(cel$masked_indices),
    mask_outlier_policy = cel$flag_policy, sample_or_probe_exclusions = 0L,
    technical_batch = "unknown; no inference from donor or bank labels",
    eligibility = "not established by CEL; requires independent normal/adult/anatomy metadata",
    application = "one CEL; frozen target, row.effects and training residual scales; fixed arithmetic-mean gene map",
    R_version = R.version.string, packages = lapply(packages, function(p)
      list(package = p, version = as.character(utils::packageVersion(p)))),
    seconds = proc.time()[[3L]] - start)
  fp_new_json(qc, destinations[2L])
  cat("PASS_SINGLE_SAMPLE_FROZEN_APPLICATION ", r$sample_id, "\n", sep = "")
  invisible(qc)
}

if (sys.nframe() == 0L) {
  a <- commandArgs(trailingOnly = TRUE)
  if (!length(a) || length(a) %% 2L || anyDuplicated(a[seq.int(1L, length(a), 2L)])) fp_stop("Expected option/value pairs")
  opt <- as.list(a[seq.int(2L, length(a), 2L)]); names(opt) <- a[seq.int(1L, length(a), 2L)]
  if (!all(c("--request", "--out") %in% names(opt)) || any(!names(opt) %in% c("--request", "--out", "--library")))
    fp_stop("Required --request and --out; optional --library")
  if ("--library" %in% names(opt)) .libPaths(c(opt[["--library"]], .libPaths()))
  Sys.setenv(OMP_NUM_THREADS = "1", OPENBLAS_NUM_THREADS = "1", MKL_NUM_THREADS = "1",
             LANG = "en_US.UTF-8", LC_ALL = "en_US.UTF-8", LC_CTYPE = "en_US.UTF-8")
  fp_apply_one(opt[["--request"]], opt[["--out"]])
}
