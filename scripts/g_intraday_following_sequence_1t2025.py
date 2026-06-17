from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv")
OUTPUT = PROJECT_ROOT / "outputs" / "g_intraday_following_sequence_1t2025.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["GapUsBefore", "Prints", "Volume", "PriceMin", "PriceMax", "TickSize"]
G_MIN_US = 1_000
CLOSURE_CANDIDATE_US = 3_600_000_000
MIN_GROUP_N = 50

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
        "sequence_count": 0,
        "gap_us_sum": 0,
        "gap_us_max": None,
        "volume_sum": 0,
        "prints_sum": 0,
        "range_ticks_sum": 0,
        "range_zero_count": 0,
        "range_positive_count": 0,
        "volume_r_positive_sum": 0,
        "prints_r_positive_sum": 0,
    }


def add_stats(
    stats: dict[tuple[str, str], dict[str, object]],
    section: str,
    group: str,
    mask: np.ndarray,
    gap: np.ndarray,
    volume: np.ndarray,
    prints: np.ndarray,
    range_ticks: np.ndarray,
) -> None:
    count = int(mask.sum())
    if count == 0:
        return

    key = (section, group)
    if key not in stats:
        stats[key] = empty_stats(section, group)

    selected_gap = gap[mask]
    selected_volume = volume[mask]
    selected_prints = prints[mask]
    selected_range = range_ticks[mask]
    r_positive = selected_range > 0

    item = stats[key]
    item["sequence_count"] = int(item["sequence_count"]) + count
    item["gap_us_sum"] = int(item["gap_us_sum"]) + int(selected_gap.sum())
    item["gap_us_max"] = max(int(item["gap_us_max"] or -1), int(selected_gap.max()))
    item["volume_sum"] = int(item["volume_sum"]) + int(selected_volume.sum())
    item["prints_sum"] = int(item["prints_sum"]) + int(selected_prints.sum())
    item["range_ticks_sum"] = int(item["range_ticks_sum"]) + int(selected_range.sum())
    item["range_zero_count"] = int(item["range_zero_count"]) + int((selected_range == 0).sum())
    item["range_positive_count"] = int(item["range_positive_count"]) + int(r_positive.sum())
    item["volume_r_positive_sum"] = int(item["volume_r_positive_sum"]) + int(selected_volume[r_positive].sum())
    item["prints_r_positive_sum"] = int(item["prints_r_positive_sum"]) + int(selected_prints[r_positive].sum())


def finalize(stats: dict[tuple[str, str], dict[str, object]]) -> pd.DataFrame:
    rows = list(stats.values())
    total_g = max(int(stats[("all_g", "all_g")]["sequence_count"]), 1)
    total_volume = max(int(stats[("all_g", "all_g")]["volume_sum"]), 1)
    total_prints = max(int(stats[("all_g", "all_g")]["prints_sum"]), 1)
    bucket_order = {label: index for index, (label, _lower, _upper) in enumerate(G_BUCKETS)}

    for row in rows:
        sequence_count = int(row["sequence_count"])
        gap_sum = int(row["gap_us_sum"])
        volume_sum = int(row["volume_sum"])
        prints_sum = int(row["prints_sum"])
        range_ticks_sum = int(row["range_ticks_sum"])
        range_zero_count = int(row["range_zero_count"])
        volume_r_positive_sum = int(row["volume_r_positive_sum"])
        prints_r_positive_sum = int(row["prints_r_positive_sum"])

        row["sequence_share_of_g"] = sequence_count / total_g
        row["volume_share_of_g"] = volume_sum / total_volume
        row["prints_share_of_g"] = prints_sum / total_prints
        row["g_mean_ms_descriptive_only"] = gap_sum / sequence_count / 1_000 if sequence_count else np.nan
        row["g_max_ms"] = int(row["gap_us_max"]) / 1_000 if row["gap_us_max"] is not None else np.nan
        row["volume_per_sequence"] = volume_sum / sequence_count if sequence_count else np.nan
        row["prints_per_sequence"] = prints_sum / sequence_count if sequence_count else np.nan
        row["range_ticks_per_sequence"] = range_ticks_sum / sequence_count if sequence_count else np.nan
        row["range_zero_share"] = range_zero_count / sequence_count if sequence_count else np.nan
        row["volume_per_print"] = volume_sum / prints_sum if prints_sum else np.nan
        row["volume_per_range_tick"] = volume_r_positive_sum / range_ticks_sum if range_ticks_sum else np.nan
        row["prints_per_range_tick"] = prints_r_positive_sum / range_ticks_sum if range_ticks_sum else np.nan
        row["sample_status"] = "ok" if sequence_count >= MIN_GROUP_N else "n_below_min"
        row["g_definition"] = "G = intraday gap only: 1000 us <= GapUsBefore < 1h."
        row["sequence_after_g_rule"] = (
            "Volume, Prints, and R describe the sequence starting after the row's GapUsBefore."
        )

    order = {"all_g": 0, "g_bucket": 1}
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

    stats: dict[tuple[str, str], dict[str, object]] = {("all_g", "all_g"): empty_stats("all_g", "all_g")}
    for label, _lower, _upper in G_BUCKETS:
        stats[("g_bucket", label)] = empty_stats("g_bucket", label)

    invalid_rows = 0
    rows_read = 0

    for chunk in pd.read_csv(SOURCE, chunksize=CHUNK_ROWS, usecols=USECOLS):
        rows_read += len(chunk)
        gap = pd.to_numeric(chunk["GapUsBefore"], errors="coerce").to_numpy()
        volume = pd.to_numeric(chunk["Volume"], errors="coerce").to_numpy()
        prints = pd.to_numeric(chunk["Prints"], errors="coerce").to_numpy()
        price_min = pd.to_numeric(chunk["PriceMin"], errors="coerce").to_numpy()
        price_max = pd.to_numeric(chunk["PriceMax"], errors="coerce").to_numpy()
        tick_size = pd.to_numeric(chunk["TickSize"], errors="coerce").to_numpy()

        valid = (
            np.isfinite(gap)
            & np.isfinite(volume)
            & np.isfinite(prints)
            & np.isfinite(price_min)
            & np.isfinite(price_max)
            & np.isfinite(tick_size)
            & (gap >= -1)
            & (volume >= 1)
            & (prints >= 1)
            & (tick_size > 0)
            & (price_max >= price_min)
        )
        invalid_rows += int((~valid).sum())
        if not valid.any():
            continue

        gap_valid = gap[valid].astype(np.int64)
        volume_valid = volume[valid].astype(np.int64)
        prints_valid = prints[valid].astype(np.int64)
        range_ticks = np.rint((price_max[valid] - price_min[valid]) / tick_size[valid]).astype(np.int64)

        range_valid = range_ticks >= 0
        invalid_rows += int((~range_valid).sum())
        if not range_valid.any():
            continue

        gap_valid = gap_valid[range_valid]
        volume_valid = volume_valid[range_valid]
        prints_valid = prints_valid[range_valid]
        range_valid_ticks = range_ticks[range_valid]

        g_mask = (gap_valid >= G_MIN_US) & (gap_valid < CLOSURE_CANDIDATE_US)
        add_stats(stats, "all_g", "all_g", g_mask, gap_valid, volume_valid, prints_valid, range_valid_ticks)

        for label, lower, upper in G_BUCKETS:
            mask = (gap_valid >= lower) & (gap_valid <= upper)
            add_stats(stats, "g_bucket", label, mask, gap_valid, volume_valid, prints_valid, range_valid_ticks)

    if rows_read == 0:
        print(f"ERROR: empty source: {SOURCE}")
        return 1
    if invalid_rows:
        print(f"ERROR: invalid rows for G-following-sequence descriptor: {invalid_rows}")
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
                "First descriptor pass for sequences following intraday G buckets on one TICKSEQ_V4 source. "
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
            "min_group_n": MIN_GROUP_N,
            "g_definition": "G means intraday elapsed gap: 1000 us <= GapUsBefore < 1h.",
            "closure_rule": "GapUsBefore >= 1h is a closure candidate and excluded from G.",
            "sub_ms_rule": "GapUsBefore in [0, 999] us is censored/sub-ms and excluded from G.",
            "range_ticks": "round((PriceMax - PriceMin) / TickSize)",
            "cut_reason_guard": "CutReason is not read in this first descriptor pass.",
            "sample_guard": "Rows with sequence_count < 50 are flagged n_below_min and must not be interpreted.",
            "scope": "descriptive first pass; no G-to-G, no trading signal, no conclusion",
        },
    )
    print(f"Wrote {OUTPUT}")
    print(f"OK: G-following-sequence descriptor pass completed on {rows_read} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
