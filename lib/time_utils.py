from __future__ import annotations

import numpy as np
import pandas as pd


NS_PER_MS = 1_000_000
NS_PER_100MS = 100_000_000
NS_PER_S = 1_000_000_000


def to_ns(values) -> np.ndarray:
    """Return int64 nanoseconds for pandas/numpy datetimes, independent of dtype."""
    if isinstance(values, pd.Series):
        arr = values.to_numpy(dtype="datetime64[ns]")
    else:
        arr = np.asarray(values, dtype="datetime64[ns]")
    return arr.astype(np.int64)


def normalize_to_ns(values) -> np.ndarray:
    """Return midnight-normalized timestamps as int64 nanoseconds."""
    if isinstance(values, pd.Series):
        normalized = values.dt.normalize()
        return normalized.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    arr = pd.Series(np.asarray(values, dtype="datetime64[ns]")).dt.normalize()
    return arr.to_numpy(dtype="datetime64[ns]").astype(np.int64)


def bucket_100ms(values) -> np.ndarray:
    ts_ns = to_ns(values)
    midnight_ns = normalize_to_ns(values)
    return ((ts_ns - midnight_ns) // NS_PER_100MS).astype(np.int64)


def assert_default_to_datetime_ns() -> None:
    dtype = str(pd.to_datetime(["2025-01-01 00:00:00.123456"]).dtype)
    if dtype != "datetime64[ns]":
        raise RuntimeError(f"pd.to_datetime default dtype is {dtype}, expected datetime64[ns]")
