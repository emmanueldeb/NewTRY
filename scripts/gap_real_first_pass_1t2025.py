from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv")
OUTPUT = PROJECT_ROOT / "outputs" / "gap_real_first_pass_1t2025.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["GapUsBefore", "CutReason"]
REAL_TIME_THRESHOLD_US = 1_000

REAL_GAP_BUCKETS = [
    ("1-9ms", 1_000, 9_999),
    ("10-99ms", 10_000, 99_999),
    ("100-999ms", 100_000, 999_999),
    ("1-9s", 1_000_000, 9_999_999),
    ("10-59s", 10_000_000, 59_999_999),
    ("1-9min", 60_000_000, 599_999_999),
    ("10-59min", 600_000_000, 3_599_999_999),
    (">=1h", 3_600_000_000, None),
]


def empty_stats(section: str, group: str) -> dict[str, object]:
    return {
        "section": section,
        "group": group,
        "row_count": 0,
        "sentinel_count": 0,
        "sub_ms_censored_count": 0,
        "real_gap_count": 0,
        "real_gap_us_sum": 0,
        "real_gap_us_max": None,
    }


def add_stats(
    stats: dict[tuple[str, str], dict[str, object]],
    section: str,
    group: str,
    mask: np.ndarray,
    gap: np.ndarray,
) -> None:
    count = int(mask.sum())
    if count == 0:
        return

    key = (section, group)
    if key not in stats:
        stats[key] = empty_stats(section, group)

    selected_gap = gap[mask]
    sentinel = selected_gap == -1
    sub_ms = (selected_gap >= 0) & (selected_gap < REAL_TIME_THRESHOLD_US)
    real = selected_gap >= REAL_TIME_THRESHOLD_US

    item = stats[key]
    item["row_count"] = int(item["row_count"]) + count
    item["sentinel_count"] = int(item["sentinel_count"]) + int(sentinel.sum())
    item["sub_ms_censored_count"] = int(item["sub_ms_censored_count"]) + int(sub_ms.sum())
    item["real_gap_count"] = int(item["real_gap_count"]) + int(real.sum())
    if real.any():
        real_gap = selected_gap[real]
        item["real_gap_us_sum"] = int(item["real_gap_us_sum"]) + int(real_gap.sum())
        item["real_gap_us_max"] = max(int(item["real_gap_us_max"] or -1), int(real_gap.max()))


def finalize(stats: dict[tuple[str, str], dict[str, object]]) -> pd.DataFrame:
    rows = list(stats.values())
    total_rows = max(int(stats[("all", "all")]["row_count"]), 1)
    total_real = max(int(stats[("all", "all")]["real_gap_count"]), 1)
    bucket_order = {label: index for index, (label, _lower, _upper) in enumerate(REAL_GAP_BUCKETS)}

    for row in rows:
        row_count = int(row["row_count"])
        real_count = int(row["real_gap_count"])
        real_sum = int(row["real_gap_us_sum"])

        row["row_share"] = row_count / total_rows
        row["real_gap_share_of_all_rows"] = real_count / total_rows
        row["real_gap_share_of_real_gaps"] = real_count / total_real
        row["sub_ms_censored_share_within_group"] = (
            int(row["sub_ms_censored_count"]) / row_count if row_count else np.nan
        )
        row["real_gap_share_within_group"] = real_count / row_count if row_count else np.nan
        row["real_gap_mean_ms"] = (real_sum / real_count / 1_000) if real_count else np.nan
        row["real_gap_max_ms"] = (int(row["real_gap_us_max"]) / 1_000) if row["real_gap_us_max"] is not None else np.nan
        row["time_domain_rule"] = "Only real_gap_count uses GapUsBefore >= 1000 us; sub-ms is censored, not zero."

    order = {"all": 0, "cut_reason": 1, "real_gap_bucket": 2}
    result = pd.DataFrame(rows)
    result["_order"] = result["section"].map(order).fillna(99)
    result["_group_order"] = [
        bucket_order.get(group, group) if section == "real_gap_bucket" else group
        for section, group in zip(result["section"], result["group"], strict=True)
    ]
    result = result.sort_values(["_order", "section", "_group_order"]).drop(columns=["_order", "_group_order"])
    return result


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: missing source: {SOURCE}")
        return 1

    stats: dict[tuple[str, str], dict[str, object]] = {("all", "all"): empty_stats("all", "all")}
    for label, _lower, _upper in REAL_GAP_BUCKETS:
        stats[("real_gap_bucket", label)] = empty_stats("real_gap_bucket", label)
    invalid_rows = 0
    rows_read = 0

    for chunk in pd.read_csv(SOURCE, chunksize=CHUNK_ROWS, usecols=USECOLS):
        rows_read += len(chunk)
        gap = pd.to_numeric(chunk["GapUsBefore"], errors="coerce").to_numpy()
        valid = np.isfinite(gap) & (gap >= -1)
        invalid_rows += int((~valid).sum())
        if not valid.any():
            continue

        gap_valid = gap[valid].astype(np.int64)
        cut_reason = chunk["CutReason"].astype(str).to_numpy()[valid]
        all_mask = np.ones(len(gap_valid), dtype=bool)

        add_stats(stats, "all", "all", all_mask, gap_valid)

        for reason in sorted(np.unique(cut_reason)):
            mask = cut_reason == reason
            add_stats(stats, "cut_reason", reason, mask, gap_valid)

        for label, lower, upper in REAL_GAP_BUCKETS:
            if upper is None:
                mask = gap_valid >= lower
            else:
                mask = (gap_valid >= lower) & (gap_valid <= upper)
            add_stats(stats, "real_gap_bucket", label, mask, gap_valid)

    if rows_read == 0:
        print(f"ERROR: empty source: {SOURCE}")
        return 1
    if invalid_rows:
        print(f"ERROR: invalid GapUsBefore rows: {invalid_rows}")
        return 1

    stat = SOURCE.stat()
    result = finalize(stats)
    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": (
                "First real-gap descriptor pass on one TICKSEQ_V4 source. "
                "This is not a G-to-G respiration analysis."
            ),
            "source": str(SOURCE),
            "source_size_bytes": stat.st_size,
            "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "input_hashing": "disabled_for_multi_gb_source",
            "chunk_rows": CHUNK_ROWS,
            "columns_read": USECOLS,
            "real_gap_buckets": [label for label, _lower, _upper in REAL_GAP_BUCKETS],
            "real_time_threshold_us": REAL_TIME_THRESHOLD_US,
            "sub_ms_rule": "GapUsBefore in [0, 999] us is censored/sub-ms and never treated as zero silence.",
            "resolution_floor_rule": "No structure below 1 ms is analyzed or claimed.",
            "scope": "descriptive first pass; no trading signal or conclusion",
        },
    )
    print(f"Wrote {OUTPUT}")
    print(f"OK: first real-gap descriptor pass completed on {rows_read} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
