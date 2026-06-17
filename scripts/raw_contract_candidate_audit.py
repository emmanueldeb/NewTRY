from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from lib.provenance import write_csv_with_provenance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQH25-CME_TICKSEQ_V4.csv")
DEFAULT_CONTRACT = "NQH25-CME"
OUTPUT = PROJECT_ROOT / "outputs" / "raw_contract_candidate_audit.csv"
CHUNK_ROWS = 1_000_000

USECOLS = [
    "StartDateTime",
    "EndDateTime",
    "Symbol",
    "Prints",
    "Volume",
    "DurationUS",  # durationus-ok: technical raw candidate audit; checks DurationUS == Prints - 1 only.
    "GapUsBefore",
    "PriceMin",
    "PriceMax",
    "TickSize",
    "CutReason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit one per-contract raw TICKSEQ_V4 candidate CSV.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--contract", default=DEFAULT_CONTRACT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source)
    expected_contract = str(args.contract)

    if not source.exists():
        print(f"ERROR: missing source: {source}")
        return 1

    stat = source.stat()
    state: dict[str, object] = {
        "source": str(source),
        "expected_contract": expected_contract,
        "ok": False,
        "source_size_bytes": stat.st_size,
        "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "rows": 0,
        "first_start": "",
        "last_end": "",
        "symbol_count": 0,
        "symbols": "",
        "expected_contract_match": False,
        "duration_not_prints_minus_1_count": 0,
        "gap_invalid_count": 0,
        "gap_minus_one_count": 0,
        "price_min": None,
        "price_max": None,
        "price_min_gt_max_count": 0,
        "tick_size_bad_count": 0,
        "cutreason_unknown_count": 0,
        "cutreason_SIDE_count": 0,
        "cutreason_PAUSE_count": 0,
        "cutreason_SESSION_count": 0,
        "cutreason_EOF_count": 0,
    }
    symbols: set[str] = set()
    known_cut_reasons = {"SIDE", "PAUSE", "SESSION", "EOF"}

    for chunk in pd.read_csv(source, usecols=USECOLS, chunksize=CHUNK_ROWS):
        rows_before = int(state["rows"])
        state["rows"] = rows_before + len(chunk)

        if rows_before == 0 and len(chunk):
            state["first_start"] = str(chunk["StartDateTime"].iloc[0])
        if len(chunk):
            state["last_end"] = str(chunk["EndDateTime"].iloc[-1])

        symbols.update(chunk["Symbol"].dropna().astype(str).unique().tolist())

        prints = pd.to_numeric(chunk["Prints"], errors="coerce")
        duration = pd.to_numeric(chunk["DurationUS"], errors="coerce")  # durationus-ok: raw candidate invariant check.
        duration_checkable = prints.notna() & duration.notna()
        state["duration_not_prints_minus_1_count"] = int(state["duration_not_prints_minus_1_count"]) + int(
            (duration_checkable & (duration != prints - 1)).sum()
        )

        gap = pd.to_numeric(chunk["GapUsBefore"], errors="coerce")
        state["gap_invalid_count"] = int(state["gap_invalid_count"]) + int((gap.isna() | (gap < -1)).sum())
        state["gap_minus_one_count"] = int(state["gap_minus_one_count"]) + int((gap == -1).sum())

        price_min = pd.to_numeric(chunk["PriceMin"], errors="coerce")
        price_max = pd.to_numeric(chunk["PriceMax"], errors="coerce")
        price_valid = price_min.notna() & price_max.notna()
        if price_valid.any():
            chunk_min = float(price_min[price_valid].min())
            chunk_max = float(price_max[price_valid].max())
            state["price_min"] = chunk_min if state["price_min"] is None else min(float(state["price_min"]), chunk_min)
            state["price_max"] = chunk_max if state["price_max"] is None else max(float(state["price_max"]), chunk_max)
            state["price_min_gt_max_count"] = int(state["price_min_gt_max_count"]) + int(
                (price_valid & (price_min > price_max)).sum()
            )

        tick_size = pd.to_numeric(chunk["TickSize"], errors="coerce")
        state["tick_size_bad_count"] = int(state["tick_size_bad_count"]) + int(
            (tick_size.isna() | (tick_size <= 0)).sum()
        )

        cut_counts = chunk["CutReason"].fillna("").astype(str).value_counts()
        for reason in known_cut_reasons:
            state[f"cutreason_{reason}_count"] = int(state[f"cutreason_{reason}_count"]) + int(
                cut_counts.get(reason, 0)
            )
        known_count = sum(int(cut_counts.get(reason, 0)) for reason in known_cut_reasons)
        state["cutreason_unknown_count"] = int(state["cutreason_unknown_count"]) + int(len(chunk) - known_count)

    state["symbol_count"] = len(symbols)
    state["symbols"] = ";".join(sorted(symbols))
    state["expected_contract_match"] = symbols == {expected_contract}
    state["ok"] = (
        int(state["rows"]) > 0
        and bool(state["expected_contract_match"])
        and int(state["duration_not_prints_minus_1_count"]) == 0
        and int(state["gap_invalid_count"]) == 0
        and int(state["gap_minus_one_count"]) == 1
        and int(state["price_min_gt_max_count"]) == 0
        and int(state["tick_size_bad_count"]) == 0
        and int(state["cutreason_unknown_count"]) == 0
    )

    result = pd.DataFrame([state])
    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": "First lightweight audit for one raw per-contract TICKSEQ_V4 candidate. No market analysis.",
            "source": str(source),
            "expected_contract": expected_contract,
            "chunk_rows": CHUNK_ROWS,
            "columns_read": USECOLS,
            "input_hashing": "disabled_for_multi_gb_source",
            "raw_policy": "Candidate must be a real per-contract export with Continuous Contract = None.",
            "scope": "raw candidate audit only; no manifest promotion",
        },
    )
    print(f"Wrote {OUTPUT}")
    print(result.to_string(index=False))
    if not bool(state["ok"]):
        print("ERROR: raw contract candidate audit failed.")
        return 1
    print("OK: raw contract candidate audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
