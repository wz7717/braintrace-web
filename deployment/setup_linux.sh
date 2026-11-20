#!/usr/bin/env bash
# Install from the checked Linux x86-64 artifact list.
set -euo pipefail

prefix="${1:?Give an absolute private runtime directory}"
case "$prefix" in /*) ;; *) echo 'Use an absolute ASCII path' >&2; exit 2;; esac
case "${2:-}" in
  '') with_app=0 ;;
  --with-app) with_app=1 ;;
  *) echo 'Usage: setup_linux.sh PREFIX [--with-app]' >&2; exit 2 ;;
esac
if [[ "$(uname -m)" != x86_64 || "$(uname -s)" != Linux ]]; then
  echo 'This artifact lock targets Linux x86-64 with glibc.' >&2
  exit 2
fi

lock_file="$(dirname -- "${BASH_SOURCE[0]}")/linux-artifacts.tsv"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p "$prefix/downloads" "$prefix/build" "$prefix/rlib"
stage() { echo "[braintrace:stage] $1"; }
stage cache
echo 'Waiting for exclusive access to the dependency cache, if needed.'
exec 9>"$prefix/setup.lock"
flock -w 1750 9
trap 'echo "Installation failed at line $LINENO (exit $?). Completed components are retained." >&2' ERR

checksum_ok() {
  [[ -f "$2" ]] && printf '%s  %s\n' "$1" "$2" | sha256sum --check --status
}

fetch() {
  local filename="$1" expected="$2" url="$3"
  local target="$prefix/downloads/$filename"
  if checksum_ok "$expected" "$target"; then
    echo "Verified cached $filename"
    return
  fi
  if [[ -f "$target" ]]; then
    echo "Cached SHA-256 mismatch for $filename; downloading again." >&2
  else
    echo "Downloading $filename"
  fi
  curl --silent --show-error --fail --location --proto '=https' --proto-redir '=https' --retry 2 \
    --connect-timeout 20 --max-time 300 "$url" --output "$target.part"
  if ! checksum_ok "$expected" "$target.part"; then
    echo "Downloaded SHA-256 mismatch for $filename" >&2
    return 1
  fi
  mv -- "$target.part" "$target"
  echo "Verified downloaded $filename"
}

locked_stamp() {
  [[ -f "$1" && "$(<"$1")" == "$2" ]]
}

install_r() {
  local filename="$1" version="$2" digest="$3"
  local tree="$prefix/build/$digest"
  local mark="$prefix/R/.braintrace-artifact"
  if locked_stamp "$mark" "$digest" && "$prefix/R/bin/Rscript" --vanilla \
        -e "stopifnot(getRversion()=='$version')" >/dev/null 2>&1; then
    echo "Using R built from the locked $filename"
    return
  fi
  mkdir -p "$tree"
  if [[ ! -f "$tree/R-$version/configure" ]]; then
    tar -xzf "$prefix/downloads/$filename" -C "$tree"
  fi
  (
    cd "$tree/R-$version"
    if [[ ! -f config.status || ! -f etc/Makeconf ]]; then
      ./configure --prefix="$prefix/R" --with-x=no --without-recommended-packages \
        --disable-java --with-blas=no --with-lapack=no
    fi
    make -j2
    make install
  )
  printf '%s\n' "$digest" >"$mark"
}

check_r_package() {
  "$prefix/R/bin/Rscript" --vanilla -e \
    "stopifnot(as.character(packageVersion('$1'))=='$2'); loadNamespace('$1')"
}

install_r_package() {
  local name="$1" version="$2" filename="$3" digest="$4"
  local mark="$prefix/rlib/$name/.braintrace-artifact"
  if locked_stamp "$mark" "$digest" && check_r_package "$name" "$version" >/dev/null 2>&1; then
    echo "Using $name $version installed from the locked archive"
    return
  fi
  # setup.lock serializes writers to this package library.
  "$prefix/R/bin/R" CMD INSTALL --no-lock --library="$prefix/rlib" "$prefix/downloads/$filename"
  check_r_package "$name" "$version"
  printf '%s\n' "$digest" >"$mark"
}

install_python() {
  local filename="$1" digest="$2"
  python_home="$prefix/python/$digest"
  python="$python_home/bin/python3.11"
  local mark="$python_home/.braintrace-artifact"
  if ! locked_stamp "$mark" "$digest" || [[ ! -x "$python" ]]; then
    mkdir -p "$python_home"
    tar -xzf "$prefix/downloads/$filename" -C "$python_home" --strip-components=1
    "$python" -I -c 'import platform; assert platform.python_version()=="3.11.9"'
    printf '%s\n' "$digest" >"$mark"
  fi
  python_digest="$digest"
}

check_environment() {
  "$1" -I -B - "$2" <<'PY'
from importlib.metadata import version
from pathlib import Path
import platform
import sys

assert platform.python_version() == "3.11.9"
for row in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    name, expected = row.split()[0].split("==")
    assert version(name) == expected, name
PY
}

install_environment() {
  local environment="$1" requirements="$2"
  local marker="$environment/.braintrace-artifact"
  local signature
  signature="$(sha256sum "$requirements")"
  signature="${signature%% *}:$python_digest"
  if locked_stamp "$marker" "$signature" && [[ -x "$environment/bin/python" ]] &&
      check_environment "$environment/bin/python" "$requirements" >/dev/null 2>&1; then
    echo "Using verified installed package versions in $(basename "$environment")"
    return
  fi
  "$python" -I -B -m venv --clear "$environment"
  "$environment/bin/python" -I -B -m pip --isolated --disable-pip-version-check --no-cache-dir \
    install --no-index --only-binary=:all: --require-hashes --find-links "$prefix/downloads" -r "$requirements"
  "$environment/bin/python" -I -B -m pip --isolated --disable-pip-version-check check
  check_environment "$environment/bin/python" "$requirements"
  printf '%s\n' "$signature" >"$marker"
}

export R_LIBS_USER="$prefix/rlib" R_LIBS_SITE="$prefix/rlib"
worker_requirements="$prefix/worker-requirements.txt"
app_requirements="$prefix/app-requirements.txt"
: >"$worker_requirements"
: >"$app_requirements"
while IFS=$'\t' read -r component name version filename bytes digest url; do
  [[ "$component" == component ]] && continue
  if [[ "$component" == app_wheel && "$with_app" == 0 ]]; then
    continue
  fi
  case "$component" in
    r) stage r ;;
    r_package) stage r_packages ;;
    *) stage python ;;
  esac
  fetch "$filename" "$digest" "$url"
  case "$component" in
    r) install_r "$filename" "$version" "$digest" ;;
    r_package) install_r_package "$name" "$version" "$filename" "$digest" ;;
    python) install_python "$filename" "$digest" ;;
    worker_wheel)
      printf '%s==%s --hash=sha256:%s\n' "$name" "$version" "$digest" >>"$worker_requirements"
      printf '%s==%s --hash=sha256:%s\n' "$name" "$version" "$digest" >>"$app_requirements"
      ;;
    app_wheel)
      printf '%s==%s --hash=sha256:%s\n' "$name" "$version" "$digest" >>"$app_requirements"
      ;;
  esac
done <"$lock_file"

install_environment "$prefix/worker" "$worker_requirements"
if [[ "$with_app" == 1 ]]; then install_environment "$prefix/app" "$app_requirements"; fi
stage verify
check_environment "$prefix/worker/bin/python" "$worker_requirements"
"$prefix/R/bin/Rscript" --vanilla -e 'stopifnot(getRversion()=="4.6.1"); expected <- c(preprocessCore="1.74.0",affxparser="1.84.0",digest="0.6.39",jsonlite="2.0.0"); for(p in names(expected)) {stopifnot(as.character(packageVersion(p))==expected[[p]]); loadNamespace(p)}'
echo 'DEPENDENCIES_READY'
