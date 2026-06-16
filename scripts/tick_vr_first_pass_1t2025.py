from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv")
OUTPUT = PROJECT_ROOT / "outputs" / "tick_vr_first_pass_1t2025.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["Prints", "Volume", "PriceMin", "PriceMax", "TickSize", "CutReason"]

RANGE_BUCKETS = [
    ("R=0", 0, 0),
    ("R=1", 1, 1),
    ("R=2", 2, 2),
    ("R=3-4", 3, 4),
    ("R=5-9", 5, 9),
    ("R>=10", 10, None),
]


def empty_stats(section: str, group: str) -> dict[str, object]:
    return {
        "section": section,
        "group": group,
        "sequence_count": 0,
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

    item = stats[key]
    selected_volume = volume[mask]
    selected_prints = prints[mask]
    selected_range = range_ticks[mask]
    r_positive = selected_range > 0
    item["sequence_count"] = int(item["sequence_count"]) + count
    item["volume_sum"] = int(item["volume_sum"]) + int(selected_volume.sum())
    item["prints_sum"] = int(item["prints_sum"]) + int(selected_prints.sum())
    item["range_ticks_sum"] = int(item["range_ticks_sum"]) + int(selected_range.sum())
    item["range_zero_count"] = int(item["range_zero_count"]) + int((selected_range == 0).sum())
    item["range_positive_count"] = int(item["range_positive_count"]) + int(r_positive.sum())
    item["volume_r_positive_sum"] = int(item["volume_r_positive_sum"]) + int(selected_volume[r_positive].sum())
    item["prints_r_positive_sum"] = int(item["prints_r_positive_sum"]) + int(selected_prints[r_positive].sum())


def finalize(stats: dict[tuple[str, str], dict[str, object]]) -> pd.DataFrame:
    rows = list(stats.values())
    total_sequences = max(int(stats[("all", "all")]["sequence_count"]), 1)

    for row in rows:
        sequence_count = int(row["sequence_count"])
        volume_sum = int(row["volume_sum"])
        prints_sum = int(row["prints_sum"])
        range_ticks_sum = int(row["range_ticks_sum"])
        volume_r_positive_sum = int(row["volume_r_positive_sum"])
        prints_r_positive_sum = int(row["prints_r_positive_sum"])

        row["sequence_share"] = sequence_count / total_sequences
        row["volume_per_sequence"] = volume_sum / sequence_count if sequence_count else np.nan
        row["prints_per_sequence"] = prints_sum / sequence_count if sequence_count else np.nan
        row["range_ticks_per_sequence"] = range_ticks_sum / sequence_count if sequence_count else np.nan
        row["volume_per_print"] = volume_sum / prints_sum if prints_sum else np.nan
        row["volume_per_range_tick"] = volume_r_positive_sum / range_ticks_sum if range_ticks_sum else np.nan
        row["prints_per_range_tick"] = prints_r_positive_sum / range_ticks_sum if range_ticks_sum else np.nan

    order = {"all": 0, "range_bucket": 1, "cut_reason": 2}
    result = pd.DataFrame(rows)
    result["_order"] = result["section"].map(order).fillna(99)
    result = result.sort_values(["_order", "section", "group"]).drop(columns=["_order"])
    return result


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: missing source: {SOURCE}")
        return 1

    stats: dict[tuple[str, str], dict[str, object]] = {("all", "all"): empty_stats("all", "all")}
    invalid_rows = 0
    rows_read = 0

    for chunk in pd.read_csv(SOURCE, chunksize=CHUNK_ROWS, usecols=USECOLS):
        rows_read += len(chunk)
        volume = pd.to_numeric(chunk["Volume"], errors="coerce").to_numpy()
        prints = pd.to_numeric(chunk["Prints"], errors="coerce").to_numpy()
        price_min = pd.to_numeric(chunk["PriceMin"], errors="coerce").to_numpy()
        price_max = pd.to_numeric(chunk["PriceMax"], errors="coerce").to_numpy()
        tick_size = pd.to_numeric(chunk["TickSize"], errors="coerce").to_numpy()

        valid = (
            np.isfinite(volume)
            & np.isfinite(prints)
            & np.isfinite(price_min)
            & np.isfinite(price_max)
            & np.isfinite(tick_size)
            & (volume >= 1)
            & (prints >= 1)
            & (tick_size > 0)
            & (price_max >= price_min)
        )
        invalid_rows += int((~valid).sum())
        if not valid.any():
            continue

        range_ticks = np.rint((price_max[valid] - price_min[valid]) / tick_size[valid]).astype(np.int64)
        range_valid = range_ticks >= 0
        invalid_rows += int((~range_valid).sum())
        if not range_valid.any():
            continue

        volume_valid = volume[valid][range_valid].astype(np.int64)
        prints_valid = prints[valid][range_valid].astype(np.int64)
        range_valid_ticks = range_ticks[range_valid]
        cut_reason = chunk["CutReason"].astype(str).to_numpy()[valid][range_valid]
        all_mask = np.ones(len(range_valid_ticks), dtype=bool)

        add_stats(stats, "all", "all", all_mask, volume_valid, prints_valid, range_valid_ticks)

        for label, lower, upper in RANGE_BUCKETS:
            if upper is None:
                mask = range_valid_ticks >= lower
            else:
                mask = (range_valid_ticks >= lower) & (range_valid_ticks <= upper)
            add_stats(stats, "range_bucket", label, mask, volume_valid, prints_valid, range_valid_ticks)

        for reason in sorted(np.unique(cut_reason)):
            mask = cut_reason == reason
            add_stats(stats, "cut_reason", reason, mask, volume_valid, prints_valid, range_valid_ticks)

    if rows_read == 0:
        print(f"ERROR: empty source: {SOURCE}")
        return 1
    if invalid_rows:
        print(f"ERROR: invalid non-temporal rows: {invalid_rows}")
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
                "First non-temporal V/R descriptor pass on one TICKSEQ_V4 source. "
                "No temporal columns are read. This does not test event-level beta or a power-law relation."
            ),
            "source": str(SOURCE),
            "source_size_bytes": stat.st_size,
            "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "input_hashing": "disabled_for_multi_gb_source",
            "chunk_rows": CHUNK_ROWS,
            "range_ticks": "round((PriceMax - PriceMin) / TickSize)",
            "r_zero_policy": "R=0 is tracked as a separate population and excluded from volume_per_range_tick",
            "volume_per_range_tick_field": (
                "aggregate Volume sum / range tick sum on rows where R>0; "
                "descriptive only, not event-level beta"
            ),
        },
    )
    print(f"Wrote {OUTPUT}")
    print(f"OK: first V/R descriptor pass completed on {rows_read} sequences without temporal columns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
