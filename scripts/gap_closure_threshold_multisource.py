from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance
from scripts.check_sources import TICKSEQ_V4_SOURCES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "outputs" / "gap_closure_threshold_multisource.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["GapUsBefore"]
REAL_TIME_THRESHOLD_US = 1_000

GAP_BUCKETS = [
    ("1_9ms", "1-9ms", 1_000, 9_999),
    ("10_99ms", "10-99ms", 10_000, 99_999),
    ("100_999ms", "100-999ms", 100_000, 999_999),
    ("1_9s", "1-9s", 1_000_000, 9_999_999),
    ("10_59s", "10-59s", 10_000_000, 59_999_999),
    ("1_9min", "1-9min", 60_000_000, 599_999_999),
    ("10_59min", "10-59min", 600_000_000, 3_599_999_999),
    ("ge_1h", ">=1h", 3_600_000_000, None),
]


def empty_row(path: Path | str) -> dict[str, object]:
    row: dict[str, object] = {
        "source": str(path),
        "ok": False,
        "error": "",
        "source_size_bytes": None,
        "source_modified_utc": None,
        "rows": 0,
        "gap_missing_count": 0,
        "gap_invalid_negative_count": 0,
        "gap_minus_one_count": 0,
        "sub_ms_censored_count": 0,
        "real_gap_count": 0,
        "real_gap_max_us": None,
        "real_gap_max_s": None,
    }
    for key, _label, _lower, _upper in GAP_BUCKETS:
        row[f"{key}_count"] = 0
        row[f"{key}_share_of_real_gaps"] = np.nan
        row[f"{key}_max_us"] = None
        row[f"{key}_max_s"] = None
    row["candidate_threshold_ge_1h_supported"] = False
    row["candidate_threshold_status"] = ""
    row["time_domain_rule"] = "Only GapUsBefore >= 1000 us is real elapsed time; sub-ms is censored, not zero."
    row["scope"] = "Closure threshold validation only; no G-to-G respiration analysis."
    return row


def update_bucket(row: dict[str, object], key: str, selected_gap: np.ndarray) -> None:
    count = int(selected_gap.size)
    row[f"{key}_count"] = int(row[f"{key}_count"]) + count
    if count:
        current = row[f"{key}_max_us"]
        row[f"{key}_max_us"] = max(int(current or -1), int(selected_gap.max()))


def source_result(path: Path) -> dict[str, object]:
    row = empty_row(path)
    if not path.exists():
        row["error"] = "missing_source"
        return row

    stat = path.stat()
    row["source_size_bytes"] = stat.st_size
    row["source_modified_utc"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()

    for chunk in pd.read_csv(path, chunksize=CHUNK_ROWS, usecols=USECOLS):
        rows_before = int(row["rows"])
        row["rows"] = rows_before + len(chunk)

        gap = pd.to_numeric(chunk["GapUsBefore"], errors="coerce").to_numpy()
        missing = ~np.isfinite(gap)
        numeric = ~missing
        invalid_negative = numeric & (gap < -1)
        minus_one = numeric & (gap == -1)
        sub_ms = numeric & (gap >= 0) & (gap < REAL_TIME_THRESHOLD_US)
        real = numeric & (gap >= REAL_TIME_THRESHOLD_US)

        row["gap_missing_count"] = int(row["gap_missing_count"]) + int(missing.sum())
        row["gap_invalid_negative_count"] = int(row["gap_invalid_negative_count"]) + int(invalid_negative.sum())
        row["gap_minus_one_count"] = int(row["gap_minus_one_count"]) + int(minus_one.sum())
        row["sub_ms_censored_count"] = int(row["sub_ms_censored_count"]) + int(sub_ms.sum())
        row["real_gap_count"] = int(row["real_gap_count"]) + int(real.sum())

        if real.any():
            real_gap = gap[real].astype(np.int64)
            row["real_gap_max_us"] = max(int(row["real_gap_max_us"] or -1), int(real_gap.max()))

        for key, _label, lower, upper in GAP_BUCKETS:
            if upper is None:
                mask = numeric & (gap >= lower)
            else:
                mask = numeric & (gap >= lower) & (gap <= upper)
            if mask.any():
                update_bucket(row, key, gap[mask].astype(np.int64))

    row["ok"] = (
        int(row["rows"]) > 0
        and int(row["gap_missing_count"]) == 0
        and int(row["gap_invalid_negative_count"]) == 0
        and int(row["gap_minus_one_count"]) == 1
    )
    return finalize_row(row)


def finalize_row(row: dict[str, object]) -> dict[str, object]:
    real_count = int(row["real_gap_count"])
    if row["real_gap_max_us"] is not None:
        row["real_gap_max_s"] = int(row["real_gap_max_us"]) / 1_000_000

    for key, _label, _lower, _upper in GAP_BUCKETS:
        count = int(row[f"{key}_count"])
        row[f"{key}_share_of_real_gaps"] = count / real_count if real_count else np.nan
        if row[f"{key}_max_us"] is not None:
            row[f"{key}_max_s"] = int(row[f"{key}_max_us"]) / 1_000_000

    gap_10_59min = int(row["10_59min_count"])
    gap_ge_1h = int(row["ge_1h_count"])
    row["candidate_threshold_ge_1h_supported"] = gap_10_59min == 0 and gap_ge_1h > 0
    if gap_10_59min:
        row["candidate_threshold_status"] = "ambiguous_10_59min_present"
    elif gap_ge_1h:
        row["candidate_threshold_status"] = "clean_empty_10_59min"
    else:
        row["candidate_threshold_status"] = "no_ge_1h_events"
    return row


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    agg = empty_row("__ALL_REFERENCED_FILES__")
    agg["ok"] = all(bool(row["ok"]) for row in rows)
    agg["error"] = "" if bool(agg["ok"]) else "one_or_more_sources_failed"
    agg["source_size_bytes"] = sum(int(row["source_size_bytes"] or 0) for row in rows)
    agg["source_modified_utc"] = ""

    count_fields = [
        "rows",
        "gap_missing_count",
        "gap_invalid_negative_count",
        "gap_minus_one_count",
        "sub_ms_censored_count",
        "real_gap_count",
    ]
    for field in count_fields:
        agg[field] = sum(int(row[field]) for row in rows)

    max_fields = ["real_gap_max_us"] + [f"{key}_max_us" for key, _label, _lower, _upper in GAP_BUCKETS]
    for field in max_fields:
        values = [int(row[field]) for row in rows if row[field] is not None]
        agg[field] = max(values) if values else None

    for key, _label, _lower, _upper in GAP_BUCKETS:
        agg[f"{key}_count"] = sum(int(row[f"{key}_count"]) for row in rows)

    return finalize_row(agg)


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
                "Multi-source closure-threshold validation for GapUsBefore. This checks whether "
                "the 10-59min bucket remains empty before treating >=1h as a closure candidate."
            ),
            "chunk_rows": CHUNK_ROWS,
            "columns_read": USECOLS,
            "input_paths": [str(path) for path in TICKSEQ_V4_SOURCES],
            "input_hashing": "disabled_for_multi_gb_sources",
            "gap_buckets": [
                {"key": key, "label": label, "lower_us": lower, "upper_us": upper}
                for key, label, lower, upper in GAP_BUCKETS
            ],
            "domain_rule": "GapUsBefore >= 1000 us is elapsed-time eligible; 0..999 us is censored/sub-ms.",
            "closure_guard": "Closures must be separated by gap magnitude, not by CutReason.",
            "mean_guard": "This script does not use aggregate mean as a respiration descriptor.",
            "overlap_guard": (
                "Referenced CSV files can overlap in calendar coverage. The aggregate row is over files, "
                "not a de-duplicated historical union; validate the threshold per source."
            ),
            "scope": "descriptive threshold validation only; no G-to-G and no trading signal",
        },
    )
    print(f"Wrote {OUTPUT}")
    if not bool(result["ok"].all()):
        print("ERROR: at least one source failed GapUsBefore threshold validation input checks.")
        return 1
    supported = result.loc[result["source"] != "__ALL_REFERENCED_FILES__", "candidate_threshold_ge_1h_supported"]
    if bool(supported.all()):
        print("OK: all sources show an empty 10-59min bucket with >=1h closure candidates.")
    else:
        print("OK: threshold scan completed; at least one source needs review before generalization.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
