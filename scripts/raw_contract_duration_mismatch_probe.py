from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


CHUNK_ROWS = 1_000_000

USECOLS = [
    "StartDateTime",
    "EndDateTime",
    "Symbol",
    "Prints",
    "Volume",
    "DurationUS",  # durationus-ok: technical counter probe; compares to Prints - 1 only.
    "GapUsBefore",
    "PriceMin",
    "PriceMax",
    "TickSize",
    "CutReason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print rows where the raw technical counter differs from Prints - 1.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source)

    if not source.exists():
        print(f"ERROR: missing source: {source}")
        return 1

    found: list[pd.DataFrame] = []
    scanned = 0
    for chunk in pd.read_csv(source, usecols=USECOLS, chunksize=CHUNK_ROWS):
        scanned += len(chunk)

        prints = pd.to_numeric(chunk["Prints"], errors="coerce")
        duration = pd.to_numeric(chunk["DurationUS"], errors="coerce")  # durationus-ok: technical counter probe.
        expected = prints - 1
        mask = prints.notna() & duration.notna() & (duration != expected)
        if not mask.any():
            continue

        rows = chunk.loc[mask].copy()
        rows.insert(0, "data_row_1based", rows.index.to_series() + 1)
        rows["expected_prints_minus_1"] = expected[mask]
        rows["duration_minus_expected"] = duration[mask] - expected[mask]
        found.append(rows)

        if sum(len(frame) for frame in found) >= args.limit:
            break

    total_found = sum(len(frame) for frame in found)
    print(f"source={source}")
    print(f"scanned_rows={scanned}")
    print(f"printed_mismatch_rows={min(total_found, args.limit)}")

    if not found:
        print("OK: no mismatch rows found.")
        return 0

    result = pd.concat(found, ignore_index=True).head(args.limit)
    print(result.to_string(index=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
