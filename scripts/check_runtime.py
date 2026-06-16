from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import scipy


def main() -> int:
    dtype = str(pd.to_datetime(["2025-01-01 00:00:00.123456"]).dtype)
    print(f"python={sys.executable}")
    print(f"python_version={sys.version.split()[0]}")
    print(f"pandas={pd.__version__}")
    print(f"numpy={np.__version__}")
    print(f"scipy={scipy.__version__}")
    print(f"to_datetime_dtype={dtype}")
    if dtype != "datetime64[ns]":
        print("ERROR: runtime datetime dtype is not datetime64[ns]")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
