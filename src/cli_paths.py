"""Host-configured CLI boundaries for accidental agent-supplied paths and options."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def allowed_path(value: Path, root: Path | None = None) -> Path:
    """The host sets the approved root outside the agent's CLI arguments."""
    base = (root or Path(os.environ.get("CLAIMTRAIL_ALLOWED_ROOT", Path.cwd()))).resolve(strict=True)
    candidate = value.expanduser().resolve()
    if not candidate.is_relative_to(base):
        raise ValueError("path is outside the host-approved root: " + str(value))
    return candidate


def executable(value: str | Path, tool: str) -> str:
    text = str(value)
    if not text or text.startswith("-") or "\0" in text:
        raise ValueError("invalid executable argument")
    found = shutil.which(text)
    if not found:
        raise ValueError("executable is not installed: " + text)
    path = Path(found).absolute()
    pattern = r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?" if tool == "python" else r"goose(?:\.exe)?"
    if not re.fullmatch(pattern, path.name) or not path.is_file():
        raise ValueError("expected an installed " + tool + " executable")
    return str(path)


def model_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value):
        raise ValueError("model must be a model identifier, not CLI options")
    return value
