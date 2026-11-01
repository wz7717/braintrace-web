#!/usr/bin/env bash
# Isolated scientific runtime; no sudo, apt changes, model fitting or prediction.
set -euo pipefail
prefix="${1:?Give a new or partially built private runtime directory}"
case "$prefix" in /*) ;; *) echo 'Use an absolute ASCII path' >&2; exit 2;; esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p "$prefix/downloads" "$prefix/build" "$prefix/rlib"
fetch() { test -s "$2" || curl --fail --location --retry 2 --connect-timeout 20 --max-time 300 "$1" --output "$2.part"; if test -f "$2.part"; then mv "$2.part" "$2"; fi; }
fetch https://cran.r-project.org/src/base/R-4/R-4.6.1.tar.gz "$prefix/downloads/R-4.6.1.tar.gz"
if ! test -x "$prefix/R/bin/Rscript"; then
  tar -xzf "$prefix/downloads/R-4.6.1.tar.gz" -C "$prefix/build"
  cd "$prefix/build/R-4.6.1"
  ./configure --prefix="$prefix/R" --with-x=no --without-recommended-packages --disable-java --with-blas=no --with-lapack=no
  make -j2
  make install
fi
declare -A urls=(
  [preprocessCore_1.74.0.tar.gz]=https://bioconductor.org/packages/3.23/bioc/src/contrib/preprocessCore_1.74.0.tar.gz
  [affxparser_1.84.0.tar.gz]=https://bioconductor.org/packages/3.23/bioc/src/contrib/affxparser_1.84.0.tar.gz
  [digest_0.6.39.tar.gz]=https://cran.r-project.org/src/contrib/digest_0.6.39.tar.gz
  [jsonlite_2.0.0.tar.gz]=https://cran.r-project.org/src/contrib/jsonlite_2.0.0.tar.gz
)
for name in "${!urls[@]}"; do
  fetch "${urls[$name]}" "$prefix/downloads/$name"
  "$prefix/R/bin/R" CMD INSTALL --library="$prefix/rlib" "$prefix/downloads/$name"
done
# uv must be installed in the hosting/UI environment, not in the old scientific environment.
export UV_PYTHON_INSTALL_DIR="$prefix/python" UV_CACHE_DIR="$prefix/uv-cache"
uv python install 3.11.9
uv venv --python 3.11.9 "$prefix/worker"
uv pip install --python "$prefix/worker/bin/python" numpy==1.26.4 pandas==2.2.3 scipy==1.13.1 scikit-learn==1.5.2 joblib==1.5.3 threadpoolctl==3.6.0
"$prefix/worker/bin/python" -c 'import platform,numpy,scipy,sklearn; assert (platform.python_version(),numpy.__version__,scipy.__version__,sklearn.__version__)==("3.11.9","1.26.4","1.13.1","1.5.2")'
R_LIBS_USER="$prefix/rlib" "$prefix/R/bin/Rscript" --vanilla -e 'stopifnot(getRversion()=="4.6.1"); expected <- c(preprocessCore="1.74.0",affxparser="1.84.0",digest="0.6.39",jsonlite="2.0.0"); for(p in names(expected)) stopifnot(as.character(packageVersion(p))==expected[[p]])'
echo 'DEPENDENCIES_INSTALLED; scientific portability checks must pass separately.'
