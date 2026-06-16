from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance
from lib.time_utils import to_ns
from scripts.check_sources import REQUIRED_COLUMNS, TICKSEQ_V4_SOURCES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "outputs" / "tickseq_v4_time_sanity_sample.csv"
SAMPLE_ROWS = 50_000
TOLERANCE_US = 1
TS_FORMAT = "%Y-%m-%d  %H:%M:%S.%f"

USECOLS = [
    "StartDateTime",
    "EndDateTime",
    "DurationUS",
    "GapUsBefore",
    "CutReason",
]


def example_lines(csv_lines: np.ndarray, limit: int = 3) -> str:
    return ";".join(str(int(x)) for x in csv_lines[:limit])


def summarize_source(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "path": str(path),
            "rows_read": 0,
            "ok": False,
            "error": "missing_source",
        }

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in pd.read_csv(path, nrows=0).columns]
    if missing_columns:
        return {
            "path": str(path),
            "rows_read": 0,
            "ok": False,
            "error": "missing_columns",
            "missing_columns": ";".join(missing_columns),
        }

    df = pd.read_csv(path, nrows=SAMPLE_ROWS, usecols=USECOLS)
    start = pd.to_datetime(df["StartDateTime"], format=TS_FORMAT, errors="coerce")
    end = pd.to_datetime(df["EndDateTime"], format=TS_FORMAT, errors="coerce")
    parse_ok = start.notna() & end.notna()
    parse_error_count = int((~parse_ok).sum())

    duration_native = pd.to_numeric(df["DurationUS"], errors="coerce").to_numpy()
    duration_calc = (to_ns(end) - to_ns(start)) // 1_000
    duration_mask = parse_ok.to_numpy() & ~pd.isna(duration_native)
    duration_errors = np.abs(duration_calc[duration_mask] - duration_native[duration_mask])
    duration_mismatch = duration_errors > TOLERANCE_US
    duration_checked = int(duration_mask.sum())
    duration_mismatch_count = int(duration_mismatch.sum())
    duration_max_abs_error_us = int(duration_errors.max()) if duration_errors.size else 0
    duration_positions = np.where(duration_mask)[0][duration_mismatch]
    duration_example_csv_lines = example_lines(duration_positions + 2)

    gap_native = pd.to_numeric(df["GapUsBefore"], errors="coerce").to_numpy()
    if len(df) > 1:
        gap_calc = (to_ns(start.iloc[1:]) - to_ns(end.iloc[:-1])) // 1_000
        gap_native_tail = gap_native[1:]
        gap_parse_ok = parse_ok.iloc[1:].to_numpy() & end.iloc[:-1].notna().to_numpy()
        gap_mask = gap_parse_ok & ~pd.isna(gap_native_tail) & (gap_native_tail >= 0)
        gap_errors = np.abs(gap_calc[gap_mask] - gap_native_tail[gap_mask])
        gap_mismatch = gap_errors > TOLERANCE_US
        gap_checked = int(gap_mask.sum())
        gap_mismatch_count = int(gap_mismatch.sum())
        gap_max_abs_error_us = int(gap_errors.max()) if gap_errors.size else 0
        gap_positions = np.where(gap_mask)[0][gap_mismatch] + 1
        gap_example_csv_lines = example_lines(gap_positions + 2)
    else:
        gap_checked = 0
        gap_mismatch_count = 0
        gap_max_abs_error_us = 0
        gap_example_csv_lines = ""

    ok = (
        parse_error_count == 0
        and duration_checked == len(df)
        and duration_mismatch_count == 0
        and gap_mismatch_count == 0
    )

    return {
        "path": str(path),
        "rows_read": len(df),
        "sample_rows_requested": SAMPLE_ROWS,
        "ok": ok,
        "error": "",
        "parse_error_count": parse_error_count,
        "duration_checked": duration_checked,
        "duration_mismatch_count": duration_mismatch_count,
        "duration_max_abs_error_us": duration_max_abs_error_us,
        "duration_example_csv_lines": duration_example_csv_lines,
        "gap_checked": gap_checked,
        "gap_mismatch_count": gap_mismatch_count,
        "gap_max_abs_error_us": gap_max_abs_error_us,
        "gap_example_csv_lines": gap_example_csv_lines,
        "tolerance_us": TOLERANCE_US,
    }


def main() -> int:
    rows = [summarize_source(path) for path in TICKSEQ_V4_SOURCES]
    result = pd.DataFrame(rows)
    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": "Reads the first SAMPLE_ROWS only. PASS/FAIL unit sanity, not market analysis.",
            "sample_rows": SAMPLE_ROWS,
            "tolerance_us": TOLERANCE_US,
            "input_paths": [str(path) for path in TICKSEQ_V4_SOURCES],
            "input_hashing": "disabled_for_multi_gb_sources",
        },
    )
    print(f"Wrote {OUTPUT}")
    if not bool(result["ok"].all()):
        print("ERROR: at least one TICKSEQ_V4 source failed the time sanity check.")
        return 1
    print("OK: sampled DurationUS and GapUsBefore checks match timestamp-derived values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
