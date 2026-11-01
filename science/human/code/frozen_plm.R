# New frozen probe-level model research method. This is not old UKBEC RMA/fRMA.
# Dependencies: preprocessCore; affxparser only for the CEL reader.
# No function below knows validation labels or chooses features/parameters.

fplm_stop <- function(...) stop(..., call. = FALSE)
fplm_need <- function(package) {
  if (!requireNamespace(package, quietly = TRUE)) fplm_stop("Missing package: ", package)
}
fplm_ids <- function(x, label) {
  if (!is.character(x) || !length(x) || anyNA(x) || any(!nzchar(x)) || anyDuplicated(x))
    fplm_stop(label, " must be unique, nonempty character identifiers")
  invisible(x)
}
fplm_numeric <- function(x, n, label, positive = FALSE) {
  if (!is.numeric(x) || length(x) != n || any(!is.finite(x)))
    fplm_stop(label, " has wrong length/type or nonfinite values")
  if (positive && any(x <= 0)) fplm_stop(label, " must be strictly positive")
  as.double(x)
}

# The parent orchestration must construct these fixed, expression-independent
# groups from hashed official design/MPS assets before touching outcomes.
fplm_axis <- function(probe_ids, cel_indices, groups, expected_chiptypes,
                      expected_rows, expected_cols, annotation_binding) {
  fplm_ids(probe_ids, "probe_ids")
  if (!is.numeric(cel_indices) || length(cel_indices) != length(probe_ids) ||
      anyNA(cel_indices) || any(cel_indices != as.integer(cel_indices)) ||
      any(cel_indices < 1) || anyDuplicated(cel_indices))
    fplm_stop("Invalid CEL one-based indices")
  if (!is.numeric(expected_rows) || length(expected_rows) != 1L ||
      !is.numeric(expected_cols) || length(expected_cols) != 1L ||
      expected_rows < 1 || expected_cols < 1 ||
      expected_rows != as.integer(expected_rows) || expected_cols != as.integer(expected_cols) ||
      any(cel_indices > expected_rows * expected_cols)) fplm_stop("Invalid chip dimensions")
  fplm_ids(expected_chiptypes, "expected_chiptypes")
  if (!is.list(groups) || !length(groups)) fplm_stop("groups must be a named list")
  fplm_ids(names(groups), "group names")
  for (g in seq_along(groups)) {
    ix <- groups[[g]]
    if (!is.numeric(ix) || length(ix) < 2L || anyNA(ix) ||
        any(ix != as.integer(ix)) || any(ix < 1 | ix > length(probe_ids)) || anyDuplicated(ix))
      fplm_stop("Invalid fixed group: ", names(groups)[g])
    groups[[g]] <- as.integer(ix)
  }
  if (!is.list(annotation_binding) || !length(annotation_binding))
    fplm_stop("A nonempty official annotation/hash binding is required")
  structure(list(schema = "braintrace.fixed_cel_axis.v1", probe_ids = probe_ids,
    cel_indices = as.integer(cel_indices), groups = groups,
    expected_chiptypes = expected_chiptypes, expected_rows = as.integer(expected_rows),
    expected_cols = as.integer(expected_cols), annotation_binding = annotation_binding),
    class = "fplm_axis")
}

fplm_validate_axis <- function(axis) {
  if (!inherits(axis, "fplm_axis")) fplm_stop("Expected frozen fplm_axis")
  # Re-run construction validation after deserialization.
  rebuilt <- do.call(fplm_axis, axis[c("probe_ids", "cel_indices", "groups",
    "expected_chiptypes", "expected_rows", "expected_cols", "annotation_binding")])
  if (!identical(rebuilt, axis)) fplm_stop("Frozen axis content/schema changed")
  invisible(axis)
}

fplm_read_cel <- function(filename, axis) {
  fplm_need("affxparser")
  fplm_validate_axis(axis)
  if (!is.character(filename) || length(filename) != 1L || !file.exists(filename) ||
      is.na(file.info(filename)$size) || file.info(filename)$size < 1)
    fplm_stop("CEL file missing/empty")
  if (grepl("[.]gz$", filename, ignore.case = TRUE))
    fplm_stop("Provide a verified, decompressed CEL; gzip acquisition belongs to the caller")
  hdr <- tryCatch(affxparser::readCelHeader(filename),
    error = function(e) fplm_stop("CEL header rejected: ", conditionMessage(e)))
  if (length(hdr$chiptype) != 1L || !hdr$chiptype %in% axis$expected_chiptypes ||
      !identical(as.integer(hdr$rows), axis$expected_rows) ||
      !identical(as.integer(hdr$cols), axis$expected_cols) ||
      !identical(as.double(hdr$total), as.double(axis$expected_rows) * axis$expected_cols))
    fplm_stop("CEL platform/dimensions do not match the frozen input contract")
  cel <- tryCatch(affxparser::readCel(filename, indices = axis$cel_indices,
    readHeader = TRUE, readXY = FALSE, readIntensities = TRUE, readStdvs = FALSE,
    readPixels = FALSE, readOutliers = TRUE, readMasked = TRUE),
    error = function(e) fplm_stop("CEL data rejected: ", conditionMessage(e)))
  pm <- fplm_numeric(cel$intensities, length(axis$probe_ids), "CEL intensities")
  if (any(pm < 0)) fplm_stop("Negative raw CEL intensities")
  names(pm) <- axis$probe_ids
  list(pm = pm, header = hdr, outlier_indices = cel$outliers, masked_indices = cel$masked,
       flag_policy = "record only; fixed annotation axis is never changed per sample")
}

fplm_background_one <- function(pm, probe_ids) {
  fplm_need("preprocessCore")
  fplm_ids(probe_ids, "probe_ids")
  if (!identical(names(pm), probe_ids)) fplm_stop("Raw PM probe axis/order mismatch")
  pm <- fplm_numeric(pm, length(probe_ids), "raw PM")
  if (any(pm < 0)) fplm_stop("Negative raw PM intensities")
  ans <- preprocessCore::rma.background.correct(matrix(pm, ncol = 1L), copy = TRUE)[, 1L]
  ans <- fplm_numeric(ans, length(probe_ids), "background-corrected PM", positive = TRUE)
  names(ans) <- probe_ids
  ans
}

# Only training sample IDs may reach this function. Each reader call returns one
# background-corrected vector in exactly the fixed PM axis. Streaming avoids a
# P-by-N double matrix. With complete axes the API's one-column target is the
# sorted column, and the multi-column target is their arithmetic mean.
fplm_target_from_training <- function(background_reader, training_sample_ids, probe_ids) {
  fplm_need("preprocessCore")
  fplm_ids(training_sample_ids, "training_sample_ids")
  fplm_ids(probe_ids, "probe_ids")
  if (!is.function(background_reader)) fplm_stop("background_reader must be a function")
  target <- numeric(length(probe_ids))
  for (sid in training_sample_ids) {
    x <- background_reader(sid)
    if (!identical(names(x), probe_ids)) fplm_stop("Training background cache axis/order mismatch: ", sid)
    x <- fplm_numeric(x, length(probe_ids), "training background PM", positive = TRUE)
    one <- preprocessCore::normalize.quantiles.determine.target(matrix(x, ncol = 1L),
                                                               target.length = length(probe_ids))
    target <- target + as.double(one) / length(training_sample_ids)
  }
  if (any(!is.finite(target)) || any(target <= 0) || is.unsorted(target))
    fplm_stop("Invalid fitted quantile target")
  target
}

fplm_normalize_one <- function(background_pm, probe_ids, target) {
  fplm_need("preprocessCore")
  if (!identical(names(background_pm), probe_ids)) fplm_stop("Background PM probe axis/order mismatch")
  x <- fplm_numeric(background_pm, length(probe_ids), "background PM", positive = TRUE)
  target <- fplm_numeric(target, length(probe_ids), "frozen target", positive = TRUE)
  if (is.unsorted(target)) fplm_stop("Frozen quantile target is not sorted")
  ans <- preprocessCore::normalize.quantiles.use.target(matrix(x, ncol = 1L),
                                                       target = target, copy = TRUE)[, 1L]
  ans <- log2(fplm_numeric(ans, length(probe_ids), "normalized PM", positive = TRUE))
  names(ans) <- probe_ids
  ans
}

fplm_zero_sum <- function(x) {
  x <- as.double(x)
  x <- x - mean(x)
  # Correct only floating point residual, for preprocessCore's strict zero-sum check.
  x[length(x)] <- -sum(x[-length(x)])
  x[length(x)] <- x[length(x)] - sum(x)
  if (abs(sum(x)) > length(x) * .Machine$double.eps) fplm_stop("Cannot center probe effects")
  x
}

# This contract is intentionally strict and must be checked against the installed
# package in the synthetic smoke test. No unknown estimate layout is guessed.
fplm_extract_training_effects <- function(fit, n_probes, n_samples) {
  e <- fit$Estimates
  if (!is.numeric(e) || length(e) != n_probes + n_samples || any(!is.finite(e)))
    fplm_stop("Unexpected/nonfinite rcModelPLM Estimates layout; validate installed API")
  effects <- e[n_samples + seq_len(n_probes)]
  centered <- fplm_zero_sum(effects)
  scale <- fplm_numeric(fit$Scale, 1L, "training PLM residual scale", positive = TRUE)
  list(effects = centered, scale = scale, centering_max_delta = max(abs(centered - effects)),
       output_layout = "n_samples column effects followed by n_probes row effects")
}

# group_reader(indices, sample_ids) must return only requested TRAINING columns,
# rows named with the requested probe IDs and columns with those exact sample IDs.
# The caller can group adjacent groups into disk blocks for economical I/O, but
# each group is fitted independently and the callback may not add validation data.
fplm_fit_effects <- function(group_reader, axis, training_sample_ids, target,
                             training_donor_ids, provenance_binding) {
  fplm_need("preprocessCore")
  fplm_validate_axis(axis)
  fplm_ids(training_sample_ids, "training_sample_ids")
  if (length(training_sample_ids) < 3L) fplm_stop("At least three training samples required")
  if (!is.character(training_donor_ids) || length(training_donor_ids) != length(training_sample_ids) ||
      anyNA(training_donor_ids) || any(!nzchar(training_donor_ids))) fplm_stop("Invalid training donor ledger")
  if (!is.function(group_reader)) fplm_stop("group_reader must be a function")
  target <- fplm_numeric(target, length(axis$probe_ids), "frozen target", positive = TRUE)
  if (is.unsorted(target)) fplm_stop("Frozen quantile target is not sorted")
  if (!is.list(provenance_binding) || !length(provenance_binding))
    fplm_stop("Training input/code/protocol provenance binding required")
  effects <- vector("list", length(axis$groups)); names(effects) <- names(axis$groups)
  center_delta <- numeric(length(effects)); names(center_delta) <- names(effects)
  scales <- numeric(length(effects)); names(scales) <- names(effects)
  for (g in seq_along(effects)) {
    ix <- axis$groups[[g]]
    y <- group_reader(ix, training_sample_ids)
    if (!is.matrix(y) || !is.numeric(y) ||
        !identical(dim(y), c(length(ix), length(training_sample_ids))) ||
        !identical(rownames(y), axis$probe_ids[ix]) ||
        !identical(colnames(y), training_sample_ids) || any(!is.finite(y)))
      fplm_stop("Training group cache IDs/shape/content mismatch: ", names(effects)[g])
    storage.mode(y) <- "double"
    fit <- preprocessCore::rcModelPLM(y, row.effects = NULL, input.scale = NULL)
    extracted <- fplm_extract_training_effects(fit, nrow(y), ncol(y))
    effects[[g]] <- extracted$effects
    center_delta[g] <- extracted$centering_max_delta
    scales[g] <- extracted$scale
  }
  structure(list(schema = "braintrace.frozen_plm_reference.v2", axis = axis,
    target = target, row_effects = effects, residual_scales = scales, training_sample_ids = training_sample_ids,
    training_donor_ids = training_donor_ids, centering_max_delta = center_delta,
    method = list(background = "preprocessCore::rma.background.correct; one column",
      quantile = "arithmetic mean of complete sorted training columns; apply target per column",
      transform = "log2", probe_model = "preprocessCore::rcModelPLM Huber default; training only",
      application = "rcModelPLM with frozen row.effects; exactly one column per call",
      input_scale = "per-group residual scale fitted on training samples and frozen",
      batch_policy = "repeat the identical single-sample application"),
    package_version = as.character(utils::packageVersion("preprocessCore")),
    r_version = R.version.string, provenance_binding = provenance_binding), class = "fplm_reference")
}

fplm_validate_reference <- function(reference) {
  if (!inherits(reference, "fplm_reference") ||
      !identical(reference$schema, "braintrace.frozen_plm_reference.v2")) fplm_stop("Invalid reference/schema")
  fplm_validate_axis(reference$axis)
  target <- fplm_numeric(reference$target, length(reference$axis$probe_ids), "reference target", TRUE)
  if (is.unsorted(target)) fplm_stop("Reference target is not sorted")
  if (!is.list(reference$row_effects) ||
      !identical(names(reference$row_effects), names(reference$axis$groups)))
    fplm_stop("Reference effect group axis mismatch")
  for (g in seq_along(reference$row_effects)) {
    a <- fplm_numeric(reference$row_effects[[g]], length(reference$axis$groups[[g]]), "row effects")
    if (abs(sum(a)) > length(a) * .Machine$double.eps) fplm_stop("Reference effects not zero-sum")
  }
  if (!identical(names(reference$residual_scales), names(reference$axis$groups)))
    fplm_stop("Reference residual scale group axis mismatch")
  fplm_numeric(reference$residual_scales, length(reference$axis$groups), "frozen residual scales", TRUE)
  fplm_ids(reference$training_sample_ids, "reference training sample IDs")
  invisible(reference)
}

fplm_summarize_one <- function(normalized_log_pm, reference) {
  fplm_need("preprocessCore")
  fplm_validate_reference(reference)
  if (!identical(as.character(utils::packageVersion("preprocessCore")), reference$package_version))
    fplm_stop("preprocessCore version differs from frozen reference")
  if (!identical(names(normalized_log_pm), reference$axis$probe_ids))
    fplm_stop("Normalized PM probe axis/order mismatch")
  x <- fplm_numeric(normalized_log_pm, length(reference$axis$probe_ids), "normalized log2 PM")
  ans <- numeric(length(reference$axis$groups)); names(ans) <- names(reference$axis$groups)
  for (g in seq_along(ans)) {
    y <- matrix(x[reference$axis$groups[[g]]], ncol = 1L)
    fit <- preprocessCore::rcModelPLM(y, row.effects = reference$row_effects[[g]],
                                     input.scale = reference$residual_scales[g])
    if (!is.numeric(fit$Estimates) || !length(fit$Estimates) || !is.finite(fit$Estimates[1L]))
      fplm_stop("Frozen PLM application failed for ", names(ans)[g])
    ans[g] <- fit$Estimates[1L]
  }
  ans
}

fplm_transform_background_one <- function(background_pm, reference) {
  y <- fplm_normalize_one(background_pm, reference$axis$probe_ids, reference$target)
  fplm_summarize_one(y, reference)
}

fplm_transform_raw_one <- function(pm, reference) {
  bg <- fplm_background_one(pm, reference$axis$probe_ids)
  fplm_transform_background_one(bg, reference)
}

# Batch is intentionally an order-preserving loop over the same function used
# for a single new sample. It never estimates a target/effect/scale from peers.
fplm_transform_raw_batch <- function(pm_reader, sample_ids, reference) {
  fplm_ids(sample_ids, "query sample_ids")
  if (!is.function(pm_reader)) fplm_stop("pm_reader must be a function")
  ans <- matrix(NA_real_, length(reference$axis$groups), length(sample_ids),
                dimnames = list(names(reference$axis$groups), sample_ids))
  for (j in seq_along(sample_ids)) ans[, j] <- fplm_transform_raw_one(pm_reader(sample_ids[j]), reference)
  ans
}

fplm_save_reference <- function(reference, path) {
  fplm_validate_reference(reference)
  if (file.exists(path)) fplm_stop("Refusing to overwrite existing reference")
  saveRDS(reference, path, version = 3L, compress = "xz")
  reloaded <- readRDS(path)
  fplm_validate_reference(reloaded)
  if (!identical(reference, reloaded)) fplm_stop("Reference serialization mismatch")
  invisible(path)
}

fplm_load_reference <- function(path) {
  out <- readRDS(path)
  fplm_validate_reference(out)
  out
}
