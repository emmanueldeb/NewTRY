from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [PROJECT_ROOT / "scripts", PROJECT_ROOT / "lib", PROJECT_ROOT / "tests"]

ALLOWLIST = {
    PROJECT_ROOT / "scripts" / "check_durationus_semantics.py",
    PROJECT_ROOT / "scripts" / "check_sources.py",
    PROJECT_ROOT / "scripts" / "tickseq_v4_duration_prints_certify.py",
    PROJECT_ROOT / "scripts" / "tickseq_v4_source_inventory.py",
    PROJECT_ROOT / "scripts" / "tickseq_v4_time_sanity_sample.py",
    PROJECT_ROOT / "tests" / "test_durationus_semantics.py",
}

JUSTIFICATION_MARKER = "durationus-ok"
SEQUENCE_DURATION_MARKER = "sequence-duration-ok"

FORBIDDEN_PATTERNS = [
    (
        "DurationUS_to_D_mapping",
        re.compile(r"['\"]DurationUS['\"]\s*:\s*['\"]D['\"]"),
    ),
    (
        "D_column_from_DurationUS",
        re.compile(r"\[['\"]D['\"]\]\s*=\s*.*['\"]DurationUS['\"]"),
    ),
    (
        "D_variable_from_DurationUS",
        re.compile(r"\bD\s*=\s*.*['\"]DurationUS['\"]"),
    ),
    (
        "rename_DurationUS_to_D",
        re.compile(r"rename\s*\(.*['\"]DurationUS['\"].*['\"]D['\"]"),
    ),
]

RAW_SEQUENCE_TIME_COLUMNS = ("StartDateTime", "EndDateTime")
RAW_SEQUENCE_DURATION_TRIGGERS = (
    "to_ns(",
    "pd.to_datetime",
    "Timedelta",
    ".total_seconds(",
)


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_DIRS:
        if root.exists():
            files.extend(sorted(root.rglob("*.py")))
    return files


def scan_text(rel: Path, text: str) -> list[str]:
    findings: list[str] = []

    for lineno, line in enumerate(text.splitlines(), start=1):
        if "DurationUS" not in line:
            continue

        stripped = line.strip()
        for name, pattern in FORBIDDEN_PATTERNS:
            if pattern.search(line):
                findings.append(f"{rel}:{lineno}: forbidden {name}: {stripped}")

        if JUSTIFICATION_MARKER not in line:
            findings.append(f"{rel}:{lineno}: direct DurationUS use requires #{JUSTIFICATION_MARKER}: {stripped}")

    has_raw_sequence_bounds = all(column in text for column in RAW_SEQUENCE_TIME_COLUMNS)
    has_duration_trigger = any(trigger in text for trigger in RAW_SEQUENCE_DURATION_TRIGGERS)
    if has_raw_sequence_bounds and has_duration_trigger and SEQUENCE_DURATION_MARKER not in text:
        findings.append(
            f"{rel}: raw StartDateTime/EndDateTime duration reconstruction requires "
            f"#{SEQUENCE_DURATION_MARKER}: reason"
        )

    return findings


def main() -> int:
    findings: list[str] = []
    for path in iter_python_files():
        if path in ALLOWLIST:
            continue

        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(PROJECT_ROOT)
        findings.extend(scan_text(rel, text))

    if findings:
        print("Unsafe DurationUS semantics found:")
        for finding in findings:
            print(f"- {finding}")
        print(
            "Use GapUsBefore or an explicitly reconstructed composed duration. "
            f"If a technical DurationUS read is intentional, add #{JUSTIFICATION_MARKER}: reason. "
            f"If raw StartDateTime/EndDateTime duration reconstruction is intentional, add "
            f"#{SEQUENCE_DURATION_MARKER}: reason."
        )
        return 1

    print("OK: no unsafe DurationUS semantics found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
