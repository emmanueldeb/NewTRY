from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from lib.provenance import write_csv_with_provenance


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "outputs" / "source_check_tickseq_v4.csv"

TICKSEQ_V4_SOURCES = [
    Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4.csv"),
    Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_jan2025.csv"),
    Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_fev2025.csv"),
    Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv"),
    Path(r"C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_Apr_and_Mai.csv"),
]

REQUIRED_COLUMNS = [
    "StartDateTime",
    "EndDateTime",
    "Symbol",
    "Side",
    "Prints",
    "Volume",
    "DurationUS",
    "GapUsBefore",
    "PriceStart",
    "PriceEnd",
    "PriceMin",
    "PriceMax",
    "VWAP",
    "StartBarIndex",
    "EndBarIndex",
    "TickSize",
    "CutReason",
    "VolProfile",
]


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        return next(reader)


def main() -> int:
    rows = []
    ok = True
    for path in TICKSEQ_V4_SOURCES:
        exists = path.exists()
        header: list[str] = []
        missing_columns: list[str] = []
        size_bytes = None
        modified_utc = None

        if exists:
            stat = path.stat()
            size_bytes = stat.st_size
            modified_utc = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            header = read_header(path)
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in header]

        source_ok = exists and not missing_columns
        ok = ok and source_ok
        rows.append(
            {
                "path": str(path),
                "exists": exists,
                "size_bytes": size_bytes,
                "modified_utc": modified_utc,
                "column_count": len(header),
                "missing_columns": ";".join(missing_columns),
                "ok": source_ok,
            }
        )

    df = pd.DataFrame(rows)
    write_csv_with_provenance(
        df,
        OUTPUT,
        script=Path(__file__).resolve(),
        project_root=PROJECT_ROOT,
        extra={
            "note": "Reads CSV headers only; no full-file hashing of multi-GB sources.",
            "required_columns": REQUIRED_COLUMNS,
        },
    )
    print(f"Wrote {OUTPUT}")
    if not ok:
        print("ERROR: at least one source is missing or has an unexpected header.")
        return 1
    print("OK: all TICKSEQ_V4 sources exist and expose required columns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
