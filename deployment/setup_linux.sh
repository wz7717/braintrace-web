#!/usr/bin/env bash
# Incremental fixed environment setup. No training or model inference.
set -euo pipefail
prefix="${1:?Give an absolute private runtime directory}"
case "$prefix" in /*) ;; *) echo 'Use an absolute ASCII path' >&2; exit 2;; esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p "$prefix/downloads" "$prefix/build" "$prefix/rlib"
stage() { echo "[braintrace:stage] $1"; }
stage cache
echo 'Waiting for exclusive access to the dependency cache, if needed.'
exec 9>"$prefix/setup.lock"
flock -w 1750 9
trap 'echo "Installation failed at line $LINENO (exit $?). Completed components are retained." >&2' ERR
fetch() {
  if test -s "$2"; then echo "Using cached archive: $(basename "$2")"; return; fi
  echo "Downloading $(basename "$2")"
  curl --fail --location --retry 2 --connect-timeout 20 --max-time 300 "$1" --output "$2.part"
  mv "$2.part" "$2"
}
stage r
if test -x "$prefix/R/bin/Rscript" && "$prefix/R/bin/Rscript" --vanilla -e 'stopifnot(getRversion()=="4.6.1")' >/dev/null 2>&1; then
  echo 'Using cached R 4.6.1; compilation skipped.'
else
  fetch https://cran.r-project.org/src/base/R-4/R-4.6.1.tar.gz "$prefix/downloads/R-4.6.1.tar.gz"
  if ! test -f "$prefix/build/R-4.6.1/configure"; then
    tar -xzf "$prefix/downloads/R-4.6.1.tar.gz" -C "$prefix/build"
  fi
  cd "$prefix/build/R-4.6.1"
  if ! test -f config.status || ! test -f etc/Makeconf; then
    ./configure --prefix="$prefix/R" --with-x=no --without-recommended-packages --disable-java --with-blas=no --with-lapack=no
  else
    echo 'Resuming the existing R build.'
  fi
  make -j2
  make install
fi
export R_LIBS_USER="$prefix/rlib" R_LIBS_SITE="$prefix/rlib"
stage r_packages
install_package() {
  local name="$1" version="$2" url="$3"
  if "$prefix/R/bin/Rscript" --vanilla -e "stopifnot(as.character(packageVersion('$name'))=='$version'); loadNamespace('$name')" >/dev/null 2>&1; then
    echo "Using cached $name $version; installation skipped."
    return
  fi
  # Remove only this package's interrupted staging lock, under the cache lock.
  rm -rf -- "$prefix/rlib/00LOCK-$name"
  fetch "$url" "$prefix/downloads/${name}_${version}.tar.gz"
  "$prefix/R/bin/R" CMD INSTALL --library="$prefix/rlib" "$prefix/downloads/${name}_${version}.tar.gz"
}
install_package preprocessCore 1.74.0 https://bioconductor.org/packages/3.23/bioc/src/contrib/preprocessCore_1.74.0.tar.gz
install_package affxparser 1.84.0 https://bioconductor.org/packages/3.23/bioc/src/contrib/affxparser_1.84.0.tar.gz
install_package digest 0.6.39 https://cran.r-project.org/src/contrib/digest_0.6.39.tar.gz
install_package jsonlite 2.0.0 https://cran.r-project.org/src/contrib/jsonlite_2.0.0.tar.gz
stage python
python_check='import platform,numpy,pandas,scipy,sklearn,joblib,threadpoolctl; assert (platform.python_version(),numpy.__version__,pandas.__version__,scipy.__version__,sklearn.__version__,joblib.__version__,threadpoolctl.__version__)==("3.11.9","1.26.4","2.2.3","1.13.1","1.5.2","1.5.3","3.6.0")'
if test -x "$prefix/worker/bin/python" && "$prefix/worker/bin/python" -c "$python_check" >/dev/null 2>&1; then
  echo 'Using cached scientific Python 3.11.9 and all six packages; installation skipped.'
else
  export UV_PYTHON_INSTALL_DIR="$prefix/python" UV_CACHE_DIR="$prefix/uv-cache"
  uv python install 3.11.9
  if ! test -x "$prefix/worker/bin/python"; then uv venv --python 3.11.9 "$prefix/worker"; fi
  uv pip install --python "$prefix/worker/bin/python" numpy==1.26.4 pandas==2.2.3 scipy==1.13.1 scikit-learn==1.5.2 joblib==1.5.3 threadpoolctl==3.6.0
fi
stage verify
"$prefix/worker/bin/python" -c "$python_check"
"$prefix/R/bin/Rscript" --vanilla -e 'stopifnot(getRversion()=="4.6.1"); expected <- c(preprocessCore="1.74.0",affxparser="1.84.0",digest="0.6.39",jsonlite="2.0.0"); for(p in names(expected)) {stopifnot(as.character(packageVersion(p))==expected[[p]]); loadNamespace(p)}'
echo 'DEPENDENCIES_READY; no model inference or training was performed.'
