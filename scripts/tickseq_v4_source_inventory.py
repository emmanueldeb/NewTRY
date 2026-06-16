from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance
from lib.time_utils import to_ns
from scripts.check_sources import REQUIRED_COLUMNS, TICKSEQ_V4_SOURCES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "outputs" / "tickseq_v4_source_inventory.csv"
CHUNK_ROWS = 500_000
TS_FORMAT = "%Y-%m-%d  %H:%M:%S.%f"
TOLERANCE_US = 1

USECOLS = [
    "StartDateTime",
    "EndDateTime",
    "Symbol",
    "Prints",
    "Volume",
    "DurationUS",
    "GapUsBefore",
    "PriceStart",
    "PriceEnd",
    "PriceMin",
    "PriceMax",
    "TickSize",
    "CutReason",
]

CUT_REASONS = ["SIDE", "PAUSE", "SESSION", "EOF"]


def read_header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def ns_for_valid(datetimes: pd.Series, valid: np.ndarray) -> np.ndarray:
    out = np.zeros(len(datetimes), dtype=np.int64)
    if valid.any():
        out[valid] = to_ns(datetimes[valid])
    return out


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


def inventory_source(path: Path) -> dict[str, object]:
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
        "first_start": "",
        "last_end": "",
        "start_dtype_seen": set(),
        "end_dtype_seen": set(),
        "parse_error_count": 0,
        "start_after_end_count": 0,
        "start_monotonic_decrease_count": 0,
        "duration_missing_count": 0,
        "duration_negative_count": 0,
        "duration_mismatch_count": 0,
        "duration_max_abs_error_us": 0,
        "gap_missing_count": 0,
        "gap_invalid_negative_count": 0,
        "gap_minus_one_count": 0,
        "gap_minus_one_not_first_count": 0,
        "first_gap_not_minus_one": 0,
        "gap_mismatch_count": 0,
        "gap_max_abs_error_us": 0,
        "prints_missing_count": 0,
        "prints_lt1_count": 0,
        "volume_missing_count": 0,
        "volume_lt1_count": 0,
        "price_min_gt_max_count": 0,
        "price_start_outside_minmax_count": 0,
        "price_end_outside_minmax_count": 0,
        "tick_size_missing_count": 0,
        "tick_size_le0_count": 0,
        "symbol_count": 0,
        "symbols": set(),
        "cutreason_unknown_count": 0,
    }
    for reason in CUT_REASONS:
        state[f"cutreason_{reason}_count"] = 0

    prev_start_ns: int | None = None
    prev_start_valid = False
    prev_end_ns: int | None = None
    prev_end_valid = False

    for chunk in pd.read_csv(path, chunksize=CHUNK_ROWS, usecols=USECOLS):
        chunk_len = len(chunk)
        offset = int(state["rows"])
        state["rows"] = offset + chunk_len

        start = pd.to_datetime(chunk["StartDateTime"], format=TS_FORMAT, errors="coerce")
        end = pd.to_datetime(chunk["EndDateTime"], format=TS_FORMAT, errors="coerce")
        state["start_dtype_seen"].add(str(start.dtype))
        state["end_dtype_seen"].add(str(end.dtype))

        parse_ok = (start.notna() & end.notna()).to_numpy()
        state["parse_error_count"] += int((~parse_ok).sum())

        start_ns = ns_for_valid(start, parse_ok)
        end_ns = ns_for_valid(end, parse_ok)

        if chunk_len and not state["first_start"]:
            state["first_start"] = str(chunk["StartDateTime"].iloc[0])
        if chunk_len:
            state["last_end"] = str(chunk["EndDateTime"].iloc[-1])

        start_after_end = parse_ok & (start_ns > end_ns)
        state["start_after_end_count"] += int(start_after_end.sum())

        if chunk_len:
            prev_start_values = np.empty(chunk_len, dtype=np.int64)
            prev_start_valids = np.empty(chunk_len, dtype=bool)
            prev_start_values[0] = prev_start_ns if prev_start_ns is not None else 0
            prev_start_valids[0] = prev_start_valid
            if chunk_len > 1:
                prev_start_values[1:] = start_ns[:-1]
                prev_start_valids[1:] = parse_ok[:-1]
            monotonic_mask = parse_ok & prev_start_valids
            state["start_monotonic_decrease_count"] += int(
                (start_ns[monotonic_mask] < prev_start_values[monotonic_mask]).sum()
            )

            prev_end_values = np.empty(chunk_len, dtype=np.int64)
            prev_end_valids = np.empty(chunk_len, dtype=bool)
            prev_end_values[0] = prev_end_ns if prev_end_ns is not None else 0
            prev_end_valids[0] = prev_end_valid
            if chunk_len > 1:
                prev_end_values[1:] = end_ns[:-1]
                prev_end_valids[1:] = parse_ok[:-1]

        duration = to_numeric(chunk["DurationUS"])
        duration_missing = duration.isna().to_numpy()
        state["duration_missing_count"] += int(duration_missing.sum())
        duration_values = duration.to_numpy()
        duration_valid = parse_ok & ~duration_missing
        duration_negative = duration_valid & (duration_values < 0)
        state["duration_negative_count"] += int(duration_negative.sum())
        duration_errors = np.abs(((end_ns[duration_valid] - start_ns[duration_valid]) // 1_000) - duration_values[duration_valid])
        if duration_errors.size:
            state["duration_mismatch_count"] += int((duration_errors > TOLERANCE_US).sum())
            state["duration_max_abs_error_us"] = max(
                int(state["duration_max_abs_error_us"]),
                int(duration_errors.max()),
            )

        gap = to_numeric(chunk["GapUsBefore"])
        gap_missing = gap.isna().to_numpy()
        state["gap_missing_count"] += int(gap_missing.sum())
        gap_values = gap.to_numpy()
        gap_valid_numeric = ~gap_missing
        gap_minus_one = gap_valid_numeric & (gap_values == -1)
        state["gap_minus_one_count"] += int(gap_minus_one.sum())
        row_numbers = offset + np.arange(chunk_len)
        state["gap_minus_one_not_first_count"] += int((gap_minus_one & (row_numbers != 0)).sum())
        if offset == 0 and chunk_len and gap_valid_numeric[0] and gap_values[0] != -1:
            state["first_gap_not_minus_one"] += 1
        gap_invalid_negative = gap_valid_numeric & (gap_values < -1)
        state["gap_invalid_negative_count"] += int(gap_invalid_negative.sum())
        gap_compare = parse_ok & prev_end_valids & gap_valid_numeric & (gap_values >= 0)
        gap_errors = np.abs(((start_ns[gap_compare] - prev_end_values[gap_compare]) // 1_000) - gap_values[gap_compare])
        if gap_errors.size:
            state["gap_mismatch_count"] += int((gap_errors > TOLERANCE_US).sum())
            state["gap_max_abs_error_us"] = max(
                int(state["gap_max_abs_error_us"]),
                int(gap_errors.max()),
            )

        prints = to_numeric(chunk["Prints"])
        prints_missing = prints.isna().to_numpy()
        state["prints_missing_count"] += int(prints_missing.sum())
        state["prints_lt1_count"] += int((~prints_missing & (prints.to_numpy() < 1)).sum())

        volume = to_numeric(chunk["Volume"])
        volume_missing = volume.isna().to_numpy()
        state["volume_missing_count"] += int(volume_missing.sum())
        state["volume_lt1_count"] += int((~volume_missing & (volume.to_numpy() < 1)).sum())

        price_start = to_numeric(chunk["PriceStart"])
        price_end = to_numeric(chunk["PriceEnd"])
        price_min = to_numeric(chunk["PriceMin"])
        price_max = to_numeric(chunk["PriceMax"])
        price_valid = ~(price_start.isna() | price_end.isna() | price_min.isna() | price_max.isna()).to_numpy()
        price_start_values = price_start.to_numpy()
        price_end_values = price_end.to_numpy()
        price_min_values = price_min.to_numpy()
        price_max_values = price_max.to_numpy()
        state["price_min_gt_max_count"] += int((price_valid & (price_min_values > price_max_values)).sum())
        state["price_start_outside_minmax_count"] += int(
            (price_valid & ((price_start_values < price_min_values) | (price_start_values > price_max_values))).sum()
        )
        state["price_end_outside_minmax_count"] += int(
            (price_valid & ((price_end_values < price_min_values) | (price_end_values > price_max_values))).sum()
        )

        tick_size = to_numeric(chunk["TickSize"])
        tick_missing = tick_size.isna().to_numpy()
        state["tick_size_missing_count"] += int(tick_missing.sum())
        state["tick_size_le0_count"] += int((~tick_missing & (tick_size.to_numpy() <= 0)).sum())

        symbols = chunk["Symbol"].dropna().astype(str).unique().tolist()
        state["symbols"].update(symbols)
        cut_counts = chunk["CutReason"].fillna("").astype(str).value_counts()
        for reason in CUT_REASONS:
            state[f"cutreason_{reason}_count"] += int(cut_counts.get(reason, 0))
        known_cut_count = sum(int(cut_counts.get(reason, 0)) for reason in CUT_REASONS)
        state["cutreason_unknown_count"] += int(chunk_len - known_cut_count)

        if chunk_len:
            prev_start_valid = bool(parse_ok[-1])
            prev_start_ns = int(start_ns[-1]) if prev_start_valid else None
            prev_end_valid = bool(parse_ok[-1])
            prev_end_ns = int(end_ns[-1]) if prev_end_valid else None

    state["symbol_count"] = len(state["symbols"])
    state["symbols"] = ";".join(sorted(state["symbols"]))
    state["start_dtype_seen"] = ";".join(sorted(state["start_dtype_seen"]))
    state["end_dtype_seen"] = ";".join(sorted(state["end_dtype_seen"]))

    fail_fields = [
        "parse_error_count",
        "start_after_end_count",
        "start_monotonic_decrease_count",
        "duration_missing_count",
        "duration_negative_count",
        "duration_mismatch_count",
        "gap_missing_count",
        "gap_invalid_negative_count",
        "gap_minus_one_not_first_count",
        "first_gap_not_minus_one",
        "gap_mismatch_count",
        "prints_missing_count",
        "prints_lt1_count",
        "volume_missing_count",
        "volume_lt1_count",
        "price_min_gt_max_count",
        "price_start_outside_minmax_count",
        "price_end_outside_minmax_count",
        "tick_size_missing_count",
        "tick_size_le0_count",
        "cutreason_unknown_count",
    ]
    state["ok"] = (
        int(state["rows"]) > 0
        and state["start_dtype_seen"] == "datetime64[ns]"
        and state["end_dtype_seen"] == "datetime64[ns]"
        and int(state["symbol_count"]) == 1
        and int(state["gap_minus_one_count"]) == 1
        and all(int(state[field]) == 0 for field in fail_fields)
    )
    return state


def main() -> int:
    rows = [inventory_source(path) for path in TICKSEQ_V4_SOURCES]
    result = pd.DataFrame(rows)
    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": "Full-file chunked source integrity inventory. No market distribution statistics.",
            "chunk_rows": CHUNK_ROWS,
            "tolerance_us": TOLERANCE_US,
            "input_paths": [str(path) for path in TICKSEQ_V4_SOURCES],
            "input_hashing": "disabled_for_multi_gb_sources",
            "domain_contract": {
                "rows": ">0",
                "timestamp_dtype": "datetime64[ns]",
                "StartDateTime": "nondecreasing and <= EndDateTime",
                "DurationUS": ">=0 and matches timestamps within tolerance",
                "GapUsBefore": "-1 only on first row, otherwise >=0 and matches previous EndDateTime",
                "Prints": ">=1",
                "Volume": ">=1",
                "PriceMin_PriceMax": "PriceMin <= PriceStart/PriceEnd <= PriceMax",
                "TickSize": ">0",
                "Symbol": "single symbol per source",
                "CutReason": CUT_REASONS,
            },
        },
    )
    print(f"Wrote {OUTPUT}")
    if not bool(result["ok"].all()):
        print("ERROR: at least one TICKSEQ_V4 source failed the source inventory.")
        return 1
    print("OK: all TICKSEQ_V4 sources pass full-file chunked integrity inventory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
