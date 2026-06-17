from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib.provenance import write_csv_with_provenance
from scripts.check_sources import TICKSEQ_V4_SOURCES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "outputs" / "closure_candidate_calendar_audit.csv"
CHUNK_ROWS = 1_000_000
TS_FORMAT = "%Y-%m-%d  %H:%M:%S.%f"
USECOLS = ["StartDateTime", "EndDateTime", "GapUsBefore"]
CLOSURE_CANDIDATE_US = 3_600_000_000
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# sequence-duration-ok: reads StartDateTime/EndDateTime only to locate closure boundaries.


def empty_source_row(path: Path | str) -> dict[str, object]:
    row: dict[str, object] = {
        "source": str(path),
        "ok": False,
        "error": "",
        "source_size_bytes": None,
        "source_modified_utc": None,
        "rows": 0,
        "gap_invalid_count": 0,
        "closure_candidate_count": 0,
        "closure_boundary_parse_error_count": 0,
        "closure_gap_min_hours": None,
        "closure_gap_max_hours": None,
        "prev_end_missing_for_closure_count": 0,
        "same_calendar_date_count": 0,
        "weekday_changed_count": 0,
        "weekend_crossing_count": 0,
        "prev_end_hour_min": None,
        "prev_end_hour_max": None,
        "start_hour_min": None,
        "start_hour_max": None,
        "sample_prev_end": "",
        "sample_start": "",
        "sample_gap_hours": "",
    }
    for day in WEEKDAYS:
        row[f"prev_end_{day}_count"] = 0
        row[f"start_{day}_count"] = 0
    return row


def update_min_max(row: dict[str, object], field_min: str, field_max: str, values: np.ndarray) -> None:
    if values.size == 0:
        return
    current_min = row[field_min]
    current_max = row[field_max]
    value_min = float(values.min())
    value_max = float(values.max())
    row[field_min] = value_min if current_min is None else min(float(current_min), value_min)
    row[field_max] = value_max if current_max is None else max(float(current_max), value_max)


def count_weekend_crossing(prev_dates: pd.Series, start_dates: pd.Series) -> int:
    count = 0
    for prev_date, start_date in zip(prev_dates, start_dates, strict=True):
        if pd.isna(prev_date) or pd.isna(start_date):
            continue
        days = pd.date_range(prev_date.normalize(), start_date.normalize(), freq="D")
        if any(int(day.weekday()) >= 5 for day in days):
            count += 1
    return count


def audit_source(path: Path) -> dict[str, object]:
    row = empty_source_row(path)
    if not path.exists():
        row["error"] = "missing_source"
        return row

    stat = path.stat()
    row["source_size_bytes"] = stat.st_size
    row["source_modified_utc"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()

    prev_end_text: str | None = None

    for chunk in pd.read_csv(
        path,
        chunksize=CHUNK_ROWS,
        usecols=USECOLS,
        dtype={"StartDateTime": "string", "EndDateTime": "string", "GapUsBefore": "int64"},
        na_filter=False,
    ):
        chunk_len = len(chunk)
        row["rows"] = int(row["rows"]) + chunk_len
        if chunk_len == 0:
            continue

        gap = pd.to_numeric(chunk["GapUsBefore"], errors="coerce").to_numpy()
        gap_valid = np.isfinite(gap) & (gap >= -1)
        row["gap_invalid_count"] = int(row["gap_invalid_count"]) + int((~gap_valid).sum())

        closure = gap_valid & (gap >= CLOSURE_CANDIDATE_US)
        closure_count = int(closure.sum())
        row["closure_candidate_count"] = int(row["closure_candidate_count"]) + closure_count

        if closure_count:
            end_text = chunk["EndDateTime"].astype(str).to_numpy()
            prev_end_text_values = np.empty(chunk_len, dtype=object)
            prev_end_text_values[0] = prev_end_text
            if chunk_len > 1:
                prev_end_text_values[1:] = end_text[:-1]

            prev_text = pd.Series(prev_end_text_values[closure], dtype="object")
            start_text = chunk.loc[closure, "StartDateTime"].astype(str).reset_index(drop=True)
            gap_closure = gap[closure]

            missing_prev = prev_text.isna() | (prev_text == "None") | (prev_text == "")
            row["prev_end_missing_for_closure_count"] = int(row["prev_end_missing_for_closure_count"]) + int(
                missing_prev.sum()
            )

            prev_dt = pd.to_datetime(prev_text, format=TS_FORMAT, errors="coerce")
            start_dt = pd.to_datetime(start_text, format=TS_FORMAT, errors="coerce")
            parse_ok = prev_dt.notna() & start_dt.notna()
            row["closure_boundary_parse_error_count"] = int(row["closure_boundary_parse_error_count"]) + int(
                (~parse_ok).sum()
            )

            if bool(parse_ok.any()):
                prev_ok = prev_dt[parse_ok].reset_index(drop=True)
                start_ok = start_dt[parse_ok].reset_index(drop=True)
                gap_ok = gap_closure[parse_ok.to_numpy()]
                gap_hours = gap_ok / CLOSURE_CANDIDATE_US
                update_min_max(row, "closure_gap_min_hours", "closure_gap_max_hours", gap_hours)

                same_date = prev_ok.dt.normalize() == start_ok.dt.normalize()
                row["same_calendar_date_count"] = int(row["same_calendar_date_count"]) + int(same_date.sum())

                prev_weekday = prev_ok.dt.weekday
                start_weekday = start_ok.dt.weekday
                weekday_changed = prev_weekday != start_weekday
                row["weekday_changed_count"] = int(row["weekday_changed_count"]) + int(weekday_changed.sum())
                row["weekend_crossing_count"] = int(row["weekend_crossing_count"]) + count_weekend_crossing(
                    prev_ok, start_ok
                )

                update_min_max(row, "prev_end_hour_min", "prev_end_hour_max", prev_ok.dt.hour.to_numpy(dtype=float))
                update_min_max(row, "start_hour_min", "start_hour_max", start_ok.dt.hour.to_numpy(dtype=float))

                prev_counts = prev_weekday.value_counts(dropna=True)
                start_counts = start_weekday.value_counts(dropna=True)
                for idx, day in enumerate(WEEKDAYS):
                    row[f"prev_end_{day}_count"] = int(row[f"prev_end_{day}_count"]) + int(prev_counts.get(idx, 0))
                    row[f"start_{day}_count"] = int(row[f"start_{day}_count"]) + int(start_counts.get(idx, 0))

                if not row["sample_prev_end"]:
                    row["sample_prev_end"] = str(prev_ok.iloc[0])
                    row["sample_start"] = str(start_ok.iloc[0])
                    row["sample_gap_hours"] = f"{gap_ok[0] / CLOSURE_CANDIDATE_US:.6f}"

        prev_end_text = str(chunk["EndDateTime"].iloc[-1])

    row["ok"] = (
        int(row["rows"]) > 0
        and int(row["gap_invalid_count"]) == 0
        and int(row["prev_end_missing_for_closure_count"]) == 0
        and int(row["closure_boundary_parse_error_count"]) == 0
    )
    return row


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    agg = empty_source_row("__ALL_REFERENCED_FILES__")
    agg["ok"] = all(bool(row["ok"]) for row in rows)
    agg["error"] = "" if bool(agg["ok"]) else "one_or_more_sources_failed"
    agg["source_size_bytes"] = sum(int(row["source_size_bytes"] or 0) for row in rows)
    agg["source_modified_utc"] = ""

    count_fields = [
        "rows",
        "gap_invalid_count",
        "closure_candidate_count",
        "closure_boundary_parse_error_count",
        "prev_end_missing_for_closure_count",
        "same_calendar_date_count",
        "weekday_changed_count",
        "weekend_crossing_count",
    ]
    for day in WEEKDAYS:
        count_fields.append(f"prev_end_{day}_count")
        count_fields.append(f"start_{day}_count")

    for field in count_fields:
        agg[field] = sum(int(row[field]) for row in rows)

    min_max_pairs = [
        ("closure_gap_min_hours", "closure_gap_max_hours"),
        ("prev_end_hour_min", "prev_end_hour_max"),
        ("start_hour_min", "start_hour_max"),
    ]
    for field_min, field_max in min_max_pairs:
        mins = [float(row[field_min]) for row in rows if row[field_min] is not None]
        maxs = [float(row[field_max]) for row in rows if row[field_max] is not None]
        agg[field_min] = min(mins) if mins else None
        agg[field_max] = max(maxs) if maxs else None

    for row in rows:
        if row["sample_prev_end"]:
            agg["sample_prev_end"] = row["sample_prev_end"]
            agg["sample_start"] = row["sample_start"]
            agg["sample_gap_hours"] = row["sample_gap_hours"]
            break

    return agg


def main() -> int:
    rows = [audit_source(path) for path in TICKSEQ_V4_SOURCES]
    rows.append(aggregate(rows))
    result = pd.DataFrame(rows)

    write_csv_with_provenance(
        result,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": (
                "Calendar audit of closure candidates only. This does not define a session calendar "
                "and does not analyze hourly or weekday market behavior."
            ),
            "chunk_rows": CHUNK_ROWS,
            "columns_read": USECOLS,
            "input_paths": [str(path) for path in TICKSEQ_V4_SOURCES],
            "input_hashing": "disabled_for_multi_gb_sources",
            "timestamp_format": TS_FORMAT,
            "closure_candidate_us": CLOSURE_CANDIDATE_US,
            "scope": "core feasibility audit for future session/calendar rule; no trading signal",
            "overlap_guard": (
                "Referenced CSV files can overlap in calendar coverage. The aggregate row is over files, "
                "not a de-duplicated historical union; validate per source."
            ),
        },
    )
    print(f"Wrote {OUTPUT}")
    if not bool(result["ok"].all()):
        print("ERROR: at least one source failed closure-candidate calendar audit.")
        return 1
    print("OK: closure-candidate calendar audit completed on all referenced sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
