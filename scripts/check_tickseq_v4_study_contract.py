from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUDY_PATH = PROJECT_ROOT / "studies" / "TRY_TickSequenceExport_v4.cpp"

REQUIRED_SNIPPETS = {
    "study_name": 'SCDLLName("TRY Tick Sequence Export v4")',
    "suffix_default": 'In_OutputSuffix.SetString("TICKSEQ_V4");',
    "max_pause_default_us": "In_MaxPauseUS.SetInt(1);",
    "max_pause_input_name": 'In_MaxPauseUS.Name = "Max Pause Between Same-Side Prints (us)";',
    "microsecond_clock": "AsMicrosecondsSinceBaseDate()",
    "duration_column": "DurationUS",
    "gap_column": "GapUsBefore",
    "cut_reason_column": "CutReason",
    "one_trade_chart_warning": "Number of Trades Per Bar = 1",
}


def main() -> int:
    if not STUDY_PATH.exists():
        print(f"ERROR: missing study source: {STUDY_PATH}")
        return 1

    text = STUDY_PATH.read_text(encoding="utf-8")
    missing = [name for name, snippet in REQUIRED_SNIPPETS.items() if snippet not in text]
    if missing:
        print("ERROR: TICKSEQ_V4 study contract changed or missing expected snippets:")
        for name in missing:
            print(f"- {name}: {REQUIRED_SNIPPETS[name]}")
        return 1

    print("OK: TICKSEQ_V4 study contract matches NewTRY expectations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
