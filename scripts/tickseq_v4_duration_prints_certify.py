from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance
from scripts.check_sources import REQUIRED_COLUMNS, TICKSEQ_V4_SOURCES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "outputs" / "tickseq_v4_duration_prints_certify.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["Prints", "DurationUS"]


def read_header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def to_numeric_array(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series, errors="coerce").to_numpy()


def empty_result(path: Path, error: str, missing_columns: list[str] | None = None) -> dict[str, object]:
    return {
        "path": str(path),
        "ok": False,
        "error": error,
        "missing_columns": ";".join(missing_columns or []),
        "source_size_bytes": None,
        "source_modified_utc": None,
        "rows": 0,
    }


def certify_source(path: Path) -> dict[str, object]:
    if not path.exists():
        return empty_result(path, "missing_source")

    header = read_header(path)
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in header]
    if missing_columns:
        return empty_result(path, "missing_columns", missing_columns)

    stat = path.stat()
    state: dict[str, object] = {
        "path": str(path),
        "ok": True,
        "error": "",
        "missing_columns": "",
        "source_size_bytes": stat.st_size,
        "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "rows": 0,
        "prints_missing_count": 0,
        "duration_missing_count": 0,
        "prints_lt1_count": 0,
        "duration_negative_count": 0,
        "duration_eq_prints_minus_one_count": 0,
        "duration_lt_prints_minus_one_count": 0,
        "duration_gt_prints_minus_one_count": 0,
        "duration_prints_mismatch_count": 0,
        "duration_prints_max_abs_diff": 0,
        "duration_999_with_prints_gt_1000_count": 0,
        "duration_ge_1000_count": 0,
        "duration_max_us": 0,
    }

    for chunk in pd.read_csv(path, chunksize=CHUNK_ROWS, usecols=USECOLS):
        chunk_len = len(chunk)
        state["rows"] = int(state["rows"]) + chunk_len

        prints = to_numeric_array(chunk["Prints"])
        duration = to_numeric_array(chunk["DurationUS"])

        prints_missing = np.isnan(prints)
        duration_missing = np.isnan(duration)
        valid_pair = ~prints_missing & ~duration_missing

        state["prints_missing_count"] = int(state["prints_missing_count"]) + int(prints_missing.sum())
        state["duration_missing_count"] = int(state["duration_missing_count"]) + int(duration_missing.sum())
        state["prints_lt1_count"] = int(state["prints_lt1_count"]) + int((valid_pair & (prints < 1)).sum())
        state["duration_negative_count"] = int(state["duration_negative_count"]) + int((valid_pair & (duration < 0)).sum())

        if valid_pair.any():
            diff = duration[valid_pair] - (prints[valid_pair] - 1)
            abs_diff = np.abs(diff)
            mismatch = abs_diff != 0
            state["duration_eq_prints_minus_one_count"] = int(state["duration_eq_prints_minus_one_count"]) + int(
                (~mismatch).sum()
            )
            state["duration_lt_prints_minus_one_count"] = int(state["duration_lt_prints_minus_one_count"]) + int(
                (diff < 0).sum()
            )
            state["duration_gt_prints_minus_one_count"] = int(state["duration_gt_prints_minus_one_count"]) + int(
                (diff > 0).sum()
            )
            state["duration_prints_mismatch_count"] = int(state["duration_prints_mismatch_count"]) + int(
                mismatch.sum()
            )
            state["duration_prints_max_abs_diff"] = max(
                int(state["duration_prints_max_abs_diff"]),
                int(abs_diff.max()),
            )
            state["duration_ge_1000_count"] = int(state["duration_ge_1000_count"]) + int(
                (duration[valid_pair] >= 1000).sum()
            )
            state["duration_999_with_prints_gt_1000_count"] = int(
                state["duration_999_with_prints_gt_1000_count"]
            ) + int(((duration[valid_pair] == 999) & (prints[valid_pair] > 1000)).sum())
            state["duration_max_us"] = max(
                int(state["duration_max_us"]),
                int(duration[valid_pair].max()),
            )

    fail_fields = [
        "prints_missing_count",
        "duration_missing_count",
        "prints_lt1_count",
        "duration_negative_count",
        "duration_gt_prints_minus_one_count",
    ]
    state["ok"] = int(state["rows"]) > 0 and all(int(state[field]) == 0 for field in fail_fields)
    return state


def main() -> int:
    rows = [certify_source(path) for path in TICKSEQ_V4_SOURCES]
    result = pd.DataFrame(rows)
    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": (
                "Full-file chunked certification of the TICKSEQ_V4 sequence-level "
                "DurationUS semantics. This is an integrity check, not a market statistic."
            ),
            "chunk_rows": CHUNK_ROWS,
            "input_paths": [str(path) for path in TICKSEQ_V4_SOURCES],
            "input_hashing": "disabled_for_multi_gb_sources",
            "domain_contract": {
                "DurationUS": "must be a non-negative native technical span compatible with Prints",
                "DurationUS_upper_bound": "with MaxPauseUS=1, must not exceed Prints - 1",
                "interpretation": (
                    "At raw sequence level, DurationUS is the native endUS-startUS span, "
                    "not an independent elapsed-time variable. Equality with Prints - 1 "
                    "is a common case, not a universal invariant."
                ),
            },
        },
    )
    print(f"Wrote {OUTPUT}")
    if not bool(result["ok"].all()):
        print("ERROR: at least one TICKSEQ_V4 source violates DurationUS/Prints certification.")
        return 1
    print("OK: all TICKSEQ_V4 sources pass DurationUS/Prints compatibility certification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
