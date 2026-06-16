from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha(project_root: str | Path | None = None) -> str | None:
    root = Path(project_root) if project_root else Path.cwd()
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return None


def runtime_metadata(
    *,
    script: str | Path | None = None,
    inputs: list[str | Path] | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    dtype = str(pd.to_datetime(["2025-01-01 00:00:00.123456"]).dtype)
    input_meta = []
    for item in inputs or []:
        path = Path(item)
        input_meta.append(
            {
                "path": str(path),
                "sha256": file_sha256(path) if path.exists() and path.is_file() else None,
            }
        )

    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "to_datetime_dtype": dtype,
        "git_sha": git_sha(project_root),
        "script": str(script) if script else None,
        "inputs": input_meta,
    }


def write_sidecar(output_path: str | Path, metadata: dict[str, Any]) -> Path:
    output = Path(output_path)
    sidecar = output.with_name(output.name + ".meta.json")
    sidecar.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sidecar


def write_csv_with_provenance(
    dataframe: pd.DataFrame,
    output_path: str | Path,
    *,
    script: str | Path | None = None,
    inputs: list[str | Path] | None = None,
    project_root: str | Path | None = None,
    extra: dict[str, Any] | None = None,
    index: bool = False,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output, index=index)

    metadata = runtime_metadata(script=script, inputs=inputs, project_root=project_root)
    if extra:
        metadata["extra"] = extra
    write_sidecar(output, metadata)
    return output
