"""Resource bounds for untrusted containers, before frozen scientific parsing."""
import csv
import gzip
import io
import math
import struct
import zipfile
import numpy as np

MAX_EXPANDED_CEL = 256 * 1024**2
MAX_NPZ_BYTES = 16 * 1024**2
SHAPES = {
    'x': {(21668, 1)}, 'observed_logcpm': {(1, 5000)},
    'observed': {(5000,), (21668,)}, 'genes': {(5000,), (21668,)},
    'samples': {(1,)}, 'full_library_counts': {(1,)},
    'public_common_annotation_counts_total': {(1,)},
    'contract_version': {()}, 'mapping_version': {()},
    'normalization': {()}, 'full_count_rows': {()},
}


def check_npz(data):
    """Read bounded NPY headers before numpy can allocate a declared array."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (not entries or len(entries) > 12 or len(set(names)) != len(names)
                or sum(e.file_size for e in entries) > MAX_NPZ_BYTES):
            raise ValueError('NPZ exceeds the single-sample container limits.')
        for entry in entries:
            key = entry.filename.removesuffix('.npy')
            if (entry.filename != key + '.npy' or key not in SHAPES
                    or entry.flag_bits & 1 or entry.is_dir()
                    or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError('NPZ must contain unique supported NPY fields only.')
            with archive.open(entry) as stream:
                version = np.lib.format.read_magic(stream)
                length_size = 2 if version == (1, 0) else 4
                length_bytes = stream.read(length_size)
                if len(length_bytes) != length_size:
                    raise ValueError('Truncated NPY header.')
                header_length = struct.unpack('<H' if length_size == 2 else '<I', length_bytes)[0]
                if header_length > 10000 or header_length > entry.file_size - stream.tell():
                    raise ValueError('NPY header exceeds the single-sample limit.')
                header = stream.read(header_length)
                bounded_header = io.BytesIO(length_bytes + header)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(bounded_header, max_header_size=10000)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(bounded_header, max_header_size=10000)
                else:
                    raise ValueError('Use NPY version 1 or 2 inside the prepared NPZ.')
                if (shape not in SHAPES[key] or dtype.hasobject or dtype.fields
                        or dtype.subdtype or dtype.kind not in 'biufSU'
                        or not 0 < dtype.itemsize <= 1024):
                    raise ValueError('NPZ field shape or dtype exceeds its input contract.')
                byte_count = math.prod(shape) * dtype.itemsize
                if byte_count > MAX_NPZ_BYTES or stream.tell() + byte_count != entry.file_size:
                    raise ValueError('NPY declared array bytes do not match its bounded ZIP entry.')


def check_text(data, suffix):
    """Stream records; never materialize an attacker-controlled number of rows."""
    reader = csv.reader(io.StringIO(data.decode('utf-8-sig')),
                        delimiter='\t' if suffix == '.tsv' else ',')
    header = next(reader, None)
    if (not header or len(header) > 12 or len(set(header)) != len(header)
            or any(not cell or len(cell) > 1024 for cell in header)):
        raise ValueError('Use a unique single-sample CSV/TSV header with at most 12 columns.')
    for count, row in enumerate(reader, 1):
        if count > 26514 or len(row) != len(header) or any(len(cell) > 1024 for cell in row):
            raise ValueError('CSV/TSV exceeds single-sample row, column or field bounds.')


def check_macaque_container(data, suffix):
    if suffix.lower() == '.npz':
        check_npz(data)
    elif suffix.lower() in ('.csv', '.tsv'):
        check_text(data, suffix.lower())


def check_cel_expansion(data, suffix, limit=MAX_EXPANDED_CEL):
    """Preflight gzip in the timed worker; do not alter the bound gzip helper."""
    if suffix.lower() != '.cel.gz':
        return
    total = 0
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        while True:
            block = stream.read(min(1024**2, limit - total + 1))
            if not block:
                return
            total += len(block)
            if total > limit:
                raise ValueError('Expanded CEL exceeds the 256 MiB application limit.')
