"""Shared value semantics for NumPy and HDF5 (no file I/O)."""
from fractions import Fraction
import numpy as np


def array_difference(left, right, *, atol=0, rtol=0, equal_nan=False,
                     check_dtype=True, string_objects=False):
    """Return a mismatch description, or None. Unsupported values raise ValueError."""
    a, b = np.asarray(left), np.asarray(right)
    for value in (a, b):
        if value.dtype.fields or value.dtype.kind == 'V':
            raise ValueError('Structured/opaque arrays are unsupported; export separate arrays or tables.')
        if value.dtype.kind == 'O' and not (
            string_objects and all(isinstance(x, (str, bytes)) for x in value.flat)
        ):
            raise ValueError('Object/reference arrays are unsupported; export numeric arrays or strings.')
    if a.shape != b.shape:
        return f'shape differs: {a.shape} vs {b.shape}'
    if check_dtype and a.dtype != b.dtype:
        return f'dtype differs: {a.dtype} vs {b.dtype}'
    ak, bk = a.dtype.kind, b.dtype.kind
    if (ak == 'b') != (bk == 'b'):
        return 'boolean and non-boolean types differ'
    if ak in 'iub' and bk in 'iub':
        # NumPy's signed/unsigned promotion can otherwise round 64-bit IDs.
        equal = np.array_equal(a.astype(object), b.astype(object))
    elif (ak in 'iu' and bk == 'f') or (bk in 'iu' and ak == 'f'):
        # Compare mixed integer/float values exactly before applying tolerance.
        abs_tol, rel_tol = Fraction(float(atol)), Fraction(float(rtol))
        def close(x, y):
            if not np.isfinite(x) or not np.isfinite(y):
                return False
            x = Fraction(int(x)) if isinstance(x, np.integer) else Fraction(*x.as_integer_ratio())
            y = Fraction(int(y)) if isinstance(y, np.integer) else Fraction(*y.as_integer_ratio())
            return abs(x-y) <= abs_tol + rel_tol * max(abs(x), abs(y))
        equal = all(close(x, y) for x, y in zip(a.flat, b.flat))
    elif (ak in 'iu' and bk == 'c') or (bk in 'iu' and ak == 'c'):
        raise ValueError('Mixed integer/complex arrays are unsupported; export consistent dtypes.')
    elif ak in 'fc' and bk in 'fc':
        dtype = np.result_type(a.dtype, b.dtype, np.float64)
        a, b = a.astype(dtype), b.astype(dtype)
        if atol == 0 and rtol == 0:
            equal = (a == b)
            if equal_nan:
                equal |= np.isnan(a) & np.isnan(b)
            return None if np.all(equal) else f'{np.count_nonzero(~equal)} values differ'
        # Scale before subtraction: huge finite differences/tolerances must not
        # overflow to an accidental inf <= inf match.
        scale = np.maximum.reduce([np.abs(a.real), np.abs(a.imag), np.abs(b.real), np.abs(b.imag)])
        scale = np.where(scale == 0, 1, scale)
        with np.errstate(invalid='ignore', over='ignore', divide='ignore'):
            x, y = a / scale, b / scale
            close = (a == b) | (np.isfinite(a) & np.isfinite(b) &
                     (np.abs(x-y) <= atol / scale + rtol * np.maximum(np.abs(x), np.abs(y))))
        if equal_nan:
            close |= np.isnan(a) & np.isnan(b)
        return None if np.all(close) else f'{np.count_nonzero(~close)} values differ'
    elif ak != bk:
        return f'value types differ: {a.dtype} vs {b.dtype}'
    else:
        equal = np.array_equal(a, b)
    return None if equal else 'values differ'
