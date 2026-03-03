"""Read the project version from the VERSION file."""

from pathlib import Path

# VERSION file is at repo root (4 levels up from this file)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def get_version() -> str:
    """Read version from the VERSION file at the repository root."""
    version_file = _REPO_ROOT / "VERSION"
    if version_file.is_file():
        return version_file.read_text().strip()
    return "dev"
