from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance
from scripts.check_sources import REQUIRED_COLUMNS, TICKSEQ_V4_SOURCES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "outputs" / "tickseq_v4_gap_domain_certify.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["GapUsBefore"]
REAL_TIME_THRESHOLD_US = 1_000


def empty_result(path: Path | str, error: str = "", missing_columns: list[str] | None = None) -> dict[str, object]:
    return {
        "source": str(path),
        "ok": False,
        "error": error,
        "missing_columns": ";".join(missing_columns or []),
        "source_size_bytes": None,
        "source_modified_utc": None,
        "rows": 0,
        "gap_missing_count": 0,
        "gap_invalid_negative_count": 0,
        "gap_minus_one_count": 0,
        "gap_minus_one_not_first_count": 0,
        "first_gap_not_minus_one": 0,
        "gap_valid_non_initial_count": 0,
        "gap_zero_count": 0,
        "gap_sub_ms_positive_count": 0,
        "gap_sub_ms_total_count": 0,
        "gap_ge_1000_count": 0,
        "gap_max_us": None,
    }


def read_header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def source_result(path: Path) -> dict[str, object]:
    if not path.exists():
        return empty_result(path, "missing_source")

    header = read_header(path)
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in header]
    if missing_columns:
        return empty_result(path, "missing_columns", missing_columns)

    stat = path.stat()
    state = empty_result(path)
    state.update(
        {
            "ok": True,
            "source_size_bytes": stat.st_size,
            "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "gap_max_us": -1,
        }
    )

    for chunk in pd.read_csv(path, chunksize=CHUNK_ROWS, usecols=USECOLS):
        offset = int(state["rows"])
        chunk_len = len(chunk)
        state["rows"] = offset + chunk_len

        gap = pd.to_numeric(chunk["GapUsBefore"], errors="coerce").to_numpy()
        missing = ~np.isfinite(gap)
        numeric = ~missing
        invalid_negative = numeric & (gap < -1)
        minus_one = numeric & (gap == -1)
        row_numbers = offset + np.arange(chunk_len)
        non_initial = numeric & (gap >= 0)
        zero = non_initial & (gap == 0)
        sub_ms_positive = non_initial & (gap > 0) & (gap < REAL_TIME_THRESHOLD_US)
        ge_1000 = non_initial & (gap >= REAL_TIME_THRESHOLD_US)

        state["gap_missing_count"] = int(state["gap_missing_count"]) + int(missing.sum())
        state["gap_invalid_negative_count"] = int(state["gap_invalid_negative_count"]) + int(invalid_negative.sum())
        state["gap_minus_one_count"] = int(state["gap_minus_one_count"]) + int(minus_one.sum())
        state["gap_minus_one_not_first_count"] = int(state["gap_minus_one_not_first_count"]) + int(
            (minus_one & (row_numbers != 0)).sum()
        )
        if offset == 0 and chunk_len and numeric[0] and gap[0] != -1:
            state["first_gap_not_minus_one"] = int(state["first_gap_not_minus_one"]) + 1
        state["gap_valid_non_initial_count"] = int(state["gap_valid_non_initial_count"]) + int(non_initial.sum())
        state["gap_zero_count"] = int(state["gap_zero_count"]) + int(zero.sum())
        state["gap_sub_ms_positive_count"] = int(state["gap_sub_ms_positive_count"]) + int(sub_ms_positive.sum())
        state["gap_sub_ms_total_count"] = int(state["gap_sub_ms_total_count"]) + int((zero | sub_ms_positive).sum())
        state["gap_ge_1000_count"] = int(state["gap_ge_1000_count"]) + int(ge_1000.sum())
        if non_initial.any():
            state["gap_max_us"] = max(int(state["gap_max_us"]), int(gap[non_initial].max()))

    state["ok"] = (
        int(state["rows"]) > 0
        and int(state["gap_missing_count"]) == 0
        and int(state["gap_invalid_negative_count"]) == 0
        and int(state["gap_minus_one_count"]) == 1
        and int(state["gap_minus_one_not_first_count"]) == 0
        and int(state["first_gap_not_minus_one"]) == 0
    )
    return add_domain_fields(state)


def add_domain_fields(row: dict[str, object]) -> dict[str, object]:
    denominator = int(row["gap_valid_non_initial_count"])
    sub_ms = int(row["gap_sub_ms_total_count"])
    ge_1000 = int(row["gap_ge_1000_count"])
    row["gap_sub_ms_total_share"] = sub_ms / denominator if denominator else np.nan
    row["gap_ge_1000_share"] = ge_1000 / denominator if denominator else np.nan
    row["time_domain_rule"] = "GapUsBefore >= 1000 us is elapsed-time eligible; 0..999 us is sub-ms censored"
    return row


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    agg = empty_result("__ALL_TICKSEQ_V4_SOURCES__")
    agg["ok"] = all(bool(row["ok"]) for row in rows)
    agg["error"] = "" if bool(agg["ok"]) else "one_or_more_sources_failed"
    agg["source_size_bytes"] = sum(int(row["source_size_bytes"] or 0) for row in rows)
    agg["source_modified_utc"] = ""
    agg["gap_max_us"] = max(int(row["gap_max_us"] or -1) for row in rows)

    count_fields = [
        "rows",
        "gap_missing_count",
        "gap_invalid_negative_count",
        "gap_minus_one_count",
        "gap_minus_one_not_first_count",
        "first_gap_not_minus_one",
        "gap_valid_non_initial_count",
        "gap_zero_count",
        "gap_sub_ms_positive_count",
        "gap_sub_ms_total_count",
        "gap_ge_1000_count",
    ]
    for field in count_fields:
        agg[field] = sum(int(row[field]) for row in rows)
    return add_domain_fields(agg)


def main() -> int:
    rows = [source_result(path) for path in TICKSEQ_V4_SOURCES]
    rows.append(aggregate(rows))
    result = pd.DataFrame(rows)
    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": (
                "Full-file GapUsBefore domain certification. This classifies the field; "
                "it does not analyze respiration or market behavior."
            ),
            "chunk_rows": CHUNK_ROWS,
            "columns_read": USECOLS,
            "input_paths": [str(path) for path in TICKSEQ_V4_SOURCES],
            "input_hashing": "disabled_for_multi_gb_sources",
            "real_time_threshold_us": REAL_TIME_THRESHOLD_US,
            "domain_rule": "Treat GapUsBefore as elapsed time only when GapUsBefore >= 1000 us.",
            "sub_ms_rule": (
                "GapUsBefore in [0, 999] us is tracked as sub-ms/censored; "
                "it must not be interpreted as zero silence."
            ),
            "resolution_floor_rule": "Future respiration analysis must not claim structure below 1 ms.",
            "known_limit": (
                "A pure 1000 us threshold assumes intra-ms synthetic counters do not spill above 999 us; "
                "keep this as a known boundary condition."
            ),
            "future_segmentation_rule": "Apply minimum sample-size guards before reporting segmented results.",
        },
    )
    print(f"Wrote {OUTPUT}")
    if not bool(result["ok"].all()):
        print("ERROR: at least one TICKSEQ_V4 source failed GapUsBefore domain certification.")
        return 1
    print("OK: all TICKSEQ_V4 sources passed GapUsBefore domain certification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
