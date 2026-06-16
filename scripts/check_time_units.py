from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [PROJECT_ROOT / "scripts", PROJECT_ROOT / "lib", PROJECT_ROOT / "tests"]
ALLOWLIST = {
    PROJECT_ROOT / "scripts" / "check_time_units.py",
    PROJECT_ROOT / "lib" / "time_utils.py",
}

DANGEROUS_PATTERNS = [
    re.compile(r"\.view\(\s*['\"]int64['\"]\s*\)"),
    re.compile(r"\.astype\(\s*['\"]int64['\"]\s*\)"),
]


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_DIRS:
        if root.exists():
            files.extend(sorted(root.rglob("*.py")))
    return files


def main() -> int:
    findings: list[str] = []
    for path in iter_python_files():
        if path in ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in DANGEROUS_PATTERNS):
                rel = path.relative_to(PROJECT_ROOT)
                findings.append(f"{rel}:{lineno}: {line.strip()}")

    if findings:
        print("Dangerous datetime-int casts found:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("OK: no direct .astype(\"int64\") or .view(\"int64\") casts found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
