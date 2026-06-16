from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv")
OUTPUT = PROJECT_ROOT / "outputs" / "tick_vr_beta_probe_1t2025.csv"
CHUNK_ROWS = 1_000_000
USECOLS = ["Volume", "PriceMin", "PriceMax", "TickSize", "CutReason"]
MIN_BETA_N = 50


def empty_state(section: str, group: str) -> dict[str, object]:
    return {
        "section": section,
        "group": group,
        "valid_sequence_count": 0,
        "r_zero_count": 0,
        "r_positive_count": 0,
        "volume_sum_all": 0,
        "volume_sum_r_zero": 0,
        "volume_sum_r_positive": 0,
        "beta_n": 0,
        "sum_log_v": 0.0,
        "sum_log_r": 0.0,
        "sum_log_v2": 0.0,
        "sum_log_r2": 0.0,
        "sum_log_v_log_r": 0.0,
    }


def add_group(
    states: dict[tuple[str, str], dict[str, object]],
    section: str,
    group: str,
    mask: np.ndarray,
    volume: np.ndarray,
    range_ticks: np.ndarray,
) -> None:
    count = int(mask.sum())
    if count == 0:
        return

    key = (section, group)
    if key not in states:
        states[key] = empty_state(section, group)

    selected_volume = volume[mask]
    selected_range = range_ticks[mask]
    r_zero = selected_range == 0
    r_positive = selected_range > 0

    state = states[key]
    state["valid_sequence_count"] = int(state["valid_sequence_count"]) + count
    state["r_zero_count"] = int(state["r_zero_count"]) + int(r_zero.sum())
    state["r_positive_count"] = int(state["r_positive_count"]) + int(r_positive.sum())
    state["volume_sum_all"] = int(state["volume_sum_all"]) + int(selected_volume.sum())
    state["volume_sum_r_zero"] = int(state["volume_sum_r_zero"]) + int(selected_volume[r_zero].sum())
    state["volume_sum_r_positive"] = int(state["volume_sum_r_positive"]) + int(selected_volume[r_positive].sum())

    if r_positive.any():
        log_v = np.log(selected_volume[r_positive])
        log_r = np.log(selected_range[r_positive])
        state["beta_n"] = int(state["beta_n"]) + int(r_positive.sum())
        state["sum_log_v"] = float(state["sum_log_v"]) + float(log_v.sum())
        state["sum_log_r"] = float(state["sum_log_r"]) + float(log_r.sum())
        state["sum_log_v2"] = float(state["sum_log_v2"]) + float((log_v * log_v).sum())
        state["sum_log_r2"] = float(state["sum_log_r2"]) + float((log_r * log_r).sum())
        state["sum_log_v_log_r"] = float(state["sum_log_v_log_r"]) + float((log_v * log_r).sum())


def finalize(states: dict[tuple[str, str], dict[str, object]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_sequences = max(int(states[("all", "all")]["valid_sequence_count"]), 1)

    for state in states.values():
        n = int(state["beta_n"])
        sum_x = float(state["sum_log_v"])
        sum_y = float(state["sum_log_r"])
        sum_x2 = float(state["sum_log_v2"])
        sum_y2 = float(state["sum_log_r2"])
        sum_xy = float(state["sum_log_v_log_r"])
        valid_sequence_count = int(state["valid_sequence_count"])
        r_zero_count = int(state["r_zero_count"])
        r_positive_count = int(state["r_positive_count"])

        denominator_x = n * sum_x2 - sum_x * sum_x
        denominator_y = n * sum_y2 - sum_y * sum_y
        numerator = n * sum_xy - sum_x * sum_y

        if n >= MIN_BETA_N and denominator_x > 0:
            beta = numerator / denominator_x
            intercept = (sum_y - beta * sum_x) / n
        else:
            beta = np.nan
            intercept = np.nan

        if n >= MIN_BETA_N and denominator_x > 0 and denominator_y > 0:
            r2 = (numerator * numerator) / (denominator_x * denominator_y)
        else:
            r2 = np.nan

        if n == 0:
            beta_status = "no_r_positive"
        elif n < MIN_BETA_N:
            beta_status = "n_below_min"
        else:
            beta_status = "ok"

        rows.append(
            {
                "section": state["section"],
                "group": state["group"],
                "valid_sequence_count": valid_sequence_count,
                "sequence_share": valid_sequence_count / total_sequences,
                "r_zero_count": r_zero_count,
                "r_zero_share_within_group": r_zero_count / valid_sequence_count if valid_sequence_count else np.nan,
                "r_positive_count": r_positive_count,
                "r_positive_share_within_group": (
                    r_positive_count / valid_sequence_count if valid_sequence_count else np.nan
                ),
                "volume_sum_all": state["volume_sum_all"],
                "volume_sum_r_zero": state["volume_sum_r_zero"],
                "volume_sum_r_positive": state["volume_sum_r_positive"],
                "beta_n": n,
                "beta_status": beta_status,
                "log_r_on_log_v_beta": beta,
                "log_r_on_log_v_intercept": intercept,
                "log_r_on_log_v_r2": r2,
            }
        )

    order = {"all": 0, "cut_reason": 1}
    result = pd.DataFrame(rows)
    result["_order"] = result["section"].map(order).fillna(99)
    result = result.sort_values(["_order", "section", "group"]).drop(columns=["_order"])
    return result


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: missing source: {SOURCE}")
        return 1

    states: dict[tuple[str, str], dict[str, object]] = {("all", "all"): empty_state("all", "all")}
    invalid_rows = 0
    rows_read = 0

    for chunk in pd.read_csv(SOURCE, chunksize=CHUNK_ROWS, usecols=USECOLS):
        rows_read += len(chunk)
        volume = pd.to_numeric(chunk["Volume"], errors="coerce").to_numpy()
        price_min = pd.to_numeric(chunk["PriceMin"], errors="coerce").to_numpy()
        price_max = pd.to_numeric(chunk["PriceMax"], errors="coerce").to_numpy()
        tick_size = pd.to_numeric(chunk["TickSize"], errors="coerce").to_numpy()

        valid = (
            np.isfinite(volume)
            & np.isfinite(price_min)
            & np.isfinite(price_max)
            & np.isfinite(tick_size)
            & (volume >= 1)
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
        range_valid_ticks = range_ticks[range_valid]
        cut_reason = chunk["CutReason"].astype(str).to_numpy()[valid][range_valid]
        all_mask = np.ones(len(range_valid_ticks), dtype=bool)

        add_group(states, "all", "all", all_mask, volume_valid, range_valid_ticks)

        for reason in sorted(np.unique(cut_reason)):
            mask = cut_reason == reason
            add_group(states, "cut_reason", reason, mask, volume_valid, range_valid_ticks)

    if rows_read == 0:
        print(f"ERROR: empty source: {SOURCE}")
        return 1
    if invalid_rows:
        print(f"ERROR: invalid non-temporal rows: {invalid_rows}")
        return 1

    stat = SOURCE.stat()
    result = finalize(states)
    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": (
                "Event-level non-temporal beta probe on one TICKSEQ_V4 source. "
                "Regression is log(R) ~ log(V) on R>0 only; R=0 is tracked separately."
            ),
            "source": str(SOURCE),
            "source_size_bytes": stat.st_size,
            "source_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "input_hashing": "disabled_for_multi_gb_source",
            "chunk_rows": CHUNK_ROWS,
            "columns_read": USECOLS,
            "min_beta_n": MIN_BETA_N,
            "range_ticks": "round((PriceMax - PriceMin) / TickSize)",
            "r_zero_policy": "R=0 is excluded from log-log beta and tracked as its own population",
            "beta_model": "ordinary least squares slope of log(R) on log(V), events with R>0 only",
            "beta_status": "beta/r2 are reported only when beta_n >= min_beta_n",
            "scope": "descriptive probe; no trading signal or conclusion",
        },
    )
    print(f"Wrote {OUTPUT}")
    print(f"OK: event-level V/R beta probe completed on {rows_read} sequences without temporal columns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
