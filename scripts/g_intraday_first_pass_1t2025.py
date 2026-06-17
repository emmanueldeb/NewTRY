from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv")
OUTPUT = PROJECT_ROOT / "outputs" / "g_intraday_first_pass_1t2025.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["GapUsBefore"]
G_MIN_US = 1_000
CLOSURE_CANDIDATE_US = 3_600_000_000

G_BUCKETS = [
    ("1-9ms", 1_000, 9_999),
    ("10-99ms", 10_000, 99_999),
    ("100-999ms", 100_000, 999_999),
    ("1-9s", 1_000_000, 9_999_999),
    ("10-59s", 10_000_000, 59_999_999),
    ("1-9min", 60_000_000, 599_999_999),
    ("10-59min", 600_000_000, 3_599_999_999),
]


def empty_stats(section: str, group: str) -> dict[str, object]:
    return {
        "section": section,
        "group": group,
        "row_count": 0,
        "sentinel_count": 0,
        "sub_ms_censored_count": 0,
        "closure_candidate_count": 0,
        "g_intraday_count": 0,
        "g_intraday_us_sum": 0,
        "g_intraday_us_max": None,
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
    sub_ms = (selected_gap >= 0) & (selected_gap < G_MIN_US)
    closure = selected_gap >= CLOSURE_CANDIDATE_US
    g_intraday = (selected_gap >= G_MIN_US) & (selected_gap < CLOSURE_CANDIDATE_US)

    item = stats[key]
    item["row_count"] = int(item["row_count"]) + count
    item["sentinel_count"] = int(item["sentinel_count"]) + int(sentinel.sum())
    item["sub_ms_censored_count"] = int(item["sub_ms_censored_count"]) + int(sub_ms.sum())
    item["closure_candidate_count"] = int(item["closure_candidate_count"]) + int(closure.sum())
    item["g_intraday_count"] = int(item["g_intraday_count"]) + int(g_intraday.sum())
    if g_intraday.any():
        intraday_gap = selected_gap[g_intraday]
        item["g_intraday_us_sum"] = int(item["g_intraday_us_sum"]) + int(intraday_gap.sum())
        item["g_intraday_us_max"] = max(int(item["g_intraday_us_max"] or -1), int(intraday_gap.max()))


def finalize(stats: dict[tuple[str, str], dict[str, object]]) -> pd.DataFrame:
    rows = list(stats.values())
    total_rows = max(int(stats[("all", "all")]["row_count"]), 1)
    total_g = max(int(stats[("all", "all")]["g_intraday_count"]), 1)
    bucket_order = {label: index for index, (label, _lower, _upper) in enumerate(G_BUCKETS)}

    for row in rows:
        row_count = int(row["row_count"])
        g_count = int(row["g_intraday_count"])
        g_sum = int(row["g_intraday_us_sum"])

        row["row_share"] = row_count / total_rows
        row["g_intraday_share_of_all_rows"] = g_count / total_rows
        row["g_intraday_share_of_g"] = g_count / total_g
        row["closure_candidate_share_within_group"] = (
            int(row["closure_candidate_count"]) / row_count if row_count else np.nan
        )
        row["sub_ms_censored_share_within_group"] = (
            int(row["sub_ms_censored_count"]) / row_count if row_count else np.nan
        )
        row["g_intraday_share_within_group"] = g_count / row_count if row_count else np.nan
        row["g_intraday_mean_ms_descriptive_only"] = (g_sum / g_count / 1_000) if g_count else np.nan
        row["g_intraday_max_ms"] = (
            int(row["g_intraday_us_max"]) / 1_000 if row["g_intraday_us_max"] is not None else np.nan
        )
        row["g_definition"] = "G = intraday gap only: 1000 us <= GapUsBefore < 1h."
        row["closure_rule"] = "GapUsBefore >= 1h is a closure candidate and is excluded from G."

    order = {"all": 0, "g_bucket": 1}
    result = pd.DataFrame(rows)
    result["_order"] = result["section"].map(order).fillna(99)
    result["_group_order"] = [
        bucket_order.get(group, group) if section == "g_bucket" else group
        for section, group in zip(result["section"], result["group"], strict=True)
    ]
    result = result.sort_values(["_order", "section", "_group_order"]).drop(columns=["_order", "_group_order"])
    return result


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: missing source: {SOURCE}")
        return 1

    stats: dict[tuple[str, str], dict[str, object]] = {("all", "all"): empty_stats("all", "all")}
    for label, _lower, _upper in G_BUCKETS:
        stats[("g_bucket", label)] = empty_stats("g_bucket", label)

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
        all_mask = np.ones(len(gap_valid), dtype=bool)
        add_stats(stats, "all", "all", all_mask, gap_valid)

        for label, lower, upper in G_BUCKETS:
            mask = (gap_valid >= lower) & (gap_valid <= upper)
            add_stats(stats, "g_bucket", label, mask, gap_valid)

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
                "First strict intraday-G descriptor pass on one TICKSEQ_V4 source. "
                "This is not a G-to-G respiration analysis."
            ),
            "source": str(SOURCE),
            "source_size_bytes": stat.st_size,
            "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "input_hashing": "disabled_for_multi_gb_source",
            "chunk_rows": CHUNK_ROWS,
            "columns_read": USECOLS,
            "g_buckets": [label for label, _lower, _upper in G_BUCKETS],
            "g_min_us": G_MIN_US,
            "closure_candidate_us": CLOSURE_CANDIDATE_US,
            "g_definition": "G means intraday elapsed gap: 1000 us <= GapUsBefore < 1h.",
            "sub_ms_rule": "GapUsBefore in [0, 999] us is censored/sub-ms and never treated as zero silence.",
            "closure_rule": "GapUsBefore >= 1h is a closure candidate and excluded from G.",
            "cut_reason_guard": "CutReason is not read; closures are separated by magnitude.",
            "mean_guard": "Means are descriptive only. Use buckets and counts before any interpretation.",
            "scope": "descriptive first pass; no G-to-G, no trading signal, no conclusion",
        },
    )
    print(f"Wrote {OUTPUT}")
    print(f"OK: first strict intraday-G descriptor pass completed on {rows_read} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
