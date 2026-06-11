# Import standard library packages.
import sys
from pathlib import Path


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _external_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path.cwd()


def _bundled_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", _source_root()))


def resource_candidates(relative_path: str | Path) -> list[Path]:
    path = Path(relative_path)
    if path.is_absolute():
        return [path]

    candidates = [
        _external_root() / path,
        _bundled_root() / path,
        Path.cwd() / path,
    ]

    unique_candidates = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(candidate)

    return unique_candidates


def resource_path(relative_path: str | Path) -> Path:
    candidates = resource_candidates(relative_path)
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]
