"""Expand exactly one supplied public CEL gzip into a new owned file.

No downloads, path discovery or archive-name extraction. Reading gzip through
EOF verifies the CRC/length of every gzip member. Existing outputs are refused.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def expand(source: Path, output: Path, receipt: Path, expected_sha: str) -> dict:
    if output.exists() or receipt.exists():
        raise FileExistsError("Refusing existing expanded CEL or receipt")
    if not source.is_file() or not source.name.lower().endswith(".cel.gz"):
        raise ValueError("Expected one existing .CEL.gz source")
    if output.parent.resolve() != receipt.parent.resolve():
        raise ValueError("CEL and receipt must use the same owned temporary directory")
    before = source.stat()
    observed_sha = file_sha(source)
    if observed_sha != expected_sha:
        raise ValueError("Compressed source SHA256 differs from caller's verified value")
    h = hashlib.sha256()
    expanded_bytes = 0
    with gzip.open(source, "rb") as compressed, output.open("xb") as dest:
        for block in iter(lambda: compressed.read(2**20), b""):
            dest.write(block)
            h.update(block)
            expanded_bytes += len(block)
        dest.flush()
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Compressed input changed while expanding")
    if expanded_bytes < 1:
        raise ValueError("Empty expanded CEL")
    result = {
        "schema": "braintrace.single_cel_gzip_expansion.v1",
        "status": "PASS_GZIP_CRC_AND_SHA256",
        "compressed_path": str(source.resolve()),
        "compressed_bytes": before.st_size,
        "compressed_sha256": observed_sha,
        "expanded_path": str(output.resolve()),
        "expanded_bytes": expanded_bytes,
        "expanded_sha256": h.hexdigest(),
        "gzip_crc_through_eof": True,
        "python_version": sys.version,
        "scope": "one explicitly supplied file; not CEL platform or biological QC",
    }
    with receipt.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=True, indent=2)
        stream.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    if len(args.expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.expected_sha256):
        parser.error("expected SHA256 must be 64 lowercase hex characters")
    try:
        expand(args.input, args.output, args.receipt, args.expected_sha256)
    except Exception as exc:
        print(json.dumps({"status": "FAILED_PRESERVED_OWNED_PARTIAL_IF_ANY",
                          "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=True),
              file=sys.stderr)
        return 2
    print("PASS_GZIP_CRC_AND_SHA256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
