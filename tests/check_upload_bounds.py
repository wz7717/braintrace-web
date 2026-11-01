"""Small hostile-container regressions; no inference or large allocations."""
from pathlib import Path
import gzip
import io
import struct
import sys
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import bounded_uploads as bounds


def container(payload, name='x.npy'):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, payload)
    return out.getvalue()


def header(shape, dtype='<f4'):
    out = io.BytesIO()
    np.lib.format.write_array_header_1_0(out, dict(descr=dtype, fortran_order=False, shape=shape))
    return out.getvalue()


class UploadBounds(unittest.TestCase):
    def test_declared_huge_array_rejected_before_allocation(self):
        data = container(header((10**12, 1)))
        with patch.object(np, 'empty', side_effect=AssertionError('Untrusted array allocated')):
            with self.assertRaises(ValueError): bounds.check_npz(data)

    def test_header_length_and_truncated_payload_rejected(self):
        huge = b'\x93NUMPY\x02\x00' + struct.pack('<I', 2**32-1)
        for data in (container(huge), container(header((21668, 1)))):
            with self.assertRaises(ValueError): bounds.check_npz(data)

    def test_object_structured_and_oversize_dtype_rejected(self):
        for dtype in ('|O', '<U1000000', [('nested', '|O')]):
            with self.assertRaises(ValueError): bounds.check_npz(container(header((21668, 1), dtype)))

    def test_zip_paths_unknown_fields_and_duplicate_fields_rejected(self):
        for name in ('../x.npy', 'arbitrary.npy', 'x.npy/child'):
            with self.assertRaises(ValueError): bounds.check_npz(container(header((21668, 1)), name))
        out = io.BytesIO()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(out, 'w') as archive:
                archive.writestr('x.npy', header((21668, 1)))
                archive.writestr('x.npy', header((21668, 1)))
        with self.assertRaises(ValueError): bounds.check_npz(out.getvalue())

    def test_valid_numerical_container_remains_unchanged(self):
        out = io.BytesIO()
        values = np.arange(21668, dtype=np.float32).reshape(-1, 1)
        np.savez_compressed(out, x=values, samples=np.array(['sample']))
        data = out.getvalue(); bounds.check_npz(data)
        with np.load(io.BytesIO(data), allow_pickle=False) as loaded:
            np.testing.assert_array_equal(loaded['x'], values)

    def test_text_limits_precede_list_materialization(self):
        bad = [b'gene,value\n' + b'a,1\n'*26515,
               b'gene,gene\na,1\n', b'gene,value\na,1,extra\n',
               b'gene,value\n'+b'a'*1025+b',1\n',
               (','.join(str(i) for i in range(13))+'\n').encode()]
        for data in bad:
            with self.assertRaises(ValueError): bounds.check_text(data, '.csv')
        bounds.check_text(b'gene_id\tcount\nENSG0001\t3\n', '.tsv')

    def test_gzip_size_crc_and_truncation(self):
        small = gzip.compress(b'CEL fixture'*10)
        bounds.check_cel_expansion(small, '.cel.gz', limit=110)
        for data in (small, small[:-3], small[:-8]+b'\x00'*8):
            with self.assertRaises((ValueError, EOFError, OSError)):
                bounds.check_cel_expansion(data, '.cel.gz', limit=100 if data == small else 200)

    def test_concatenated_gzip_members_share_one_limit(self):
        with self.assertRaises(ValueError):
            bounds.check_cel_expansion(gzip.compress(b'a'*60)+gzip.compress(b'b'*60), '.cel.gz', limit=100)


if __name__ == '__main__': unittest.main(verbosity=2)
