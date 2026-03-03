"""Tests for find_clone_dir() and get_version() fallback logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fmapi_opskit.core import find_clone_dir, get_version


def _make_clone(path: Path) -> Path:
    """Create a minimal fake clone directory with .git/ and VERSION."""
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir(exist_ok=True)
    (path / "VERSION").write_text("1.2.3\n")
    return path


class TestFindCloneDir:
    """Tests for the 3-tier find_clone_dir() resolution."""

    def test_fmapi_home_env_takes_priority(self, tmp_path: Path) -> None:
        clone = _make_clone(tmp_path / "custom-home")
        with patch.dict("os.environ", {"FMAPI_HOME": str(clone)}):
            assert find_clone_dir() == clone

    def test_fmapi_home_ignores_invalid_dir(self, tmp_path: Path) -> None:
        """FMAPI_HOME pointing to a non-clone directory is skipped."""
        bad_dir = tmp_path / "not-a-clone"
        bad_dir.mkdir()
        with patch.dict("os.environ", {"FMAPI_HOME": str(bad_dir)}):
            # Should fall through to tier 2/3 (which may or may not match)
            result = find_clone_dir()
            assert result != bad_dir

    def test_walk_up_finds_clone(self, tmp_path: Path) -> None:
        """Tier 2: walk-up from __file__ finds a parent with .git + VERSION."""
        import fmapi_opskit.core as core_mod

        clone = _make_clone(tmp_path / "repo")
        fake_file = clone / "src" / "fmapi_opskit" / "core.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")

        with (
            patch.dict("os.environ", {"FMAPI_HOME": ""}, clear=False),
            patch.object(core_mod, "__file__", str(fake_file)),
            patch("fmapi_opskit.core._DEFAULT_CLONE_DIR", tmp_path / "nope"),
        ):
            assert find_clone_dir() == clone

    def test_default_clone_dir_found(self, tmp_path: Path) -> None:
        """Tier 3: falls back to the default clone directory."""
        import fmapi_opskit.core as core_mod

        default = tmp_path / ".fmapi-codingagent-setup"
        _make_clone(default)

        # Point __file__ somewhere with no .git ancestor to skip tier 2
        fake_file = tmp_path / "isolated" / "core.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")

        with (
            patch.dict("os.environ", {"FMAPI_HOME": ""}, clear=False),
            patch.object(core_mod, "__file__", str(fake_file)),
            patch("fmapi_opskit.core._DEFAULT_CLONE_DIR", default),
        ):
            assert find_clone_dir() == default

    def test_returns_none_when_nothing_matches(self, tmp_path: Path) -> None:
        """Returns None when no tier resolves."""
        import fmapi_opskit.core as core_mod

        fake_file = tmp_path / "isolated" / "core.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")

        with (
            patch.dict("os.environ", {"FMAPI_HOME": ""}, clear=False),
            patch.object(core_mod, "__file__", str(fake_file)),
            patch("fmapi_opskit.core._DEFAULT_CLONE_DIR", tmp_path / "nope"),
        ):
            assert find_clone_dir() is None


class TestGetVersion:
    """Tests for get_version() with clone dir and importlib fallback."""

    def test_reads_version_from_clone_dir(self, tmp_path: Path) -> None:
        clone = _make_clone(tmp_path / "repo")
        with patch("fmapi_opskit.core.find_clone_dir", return_value=clone):
            assert get_version() == "1.2.3"

    def test_falls_back_to_importlib_metadata(self, tmp_path: Path) -> None:
        with (
            patch("fmapi_opskit.core.find_clone_dir", return_value=None),
            patch("importlib.metadata.version", return_value="4.5.6"),
        ):
            assert get_version() == "4.5.6"

    def test_returns_dev_when_all_fail(self, tmp_path: Path) -> None:
        import importlib.metadata

        with (
            patch("fmapi_opskit.core.find_clone_dir", return_value=None),
            patch(
                "importlib.metadata.version",
                side_effect=importlib.metadata.PackageNotFoundError("test"),
            ),
        ):
            assert get_version() == "dev"

    def test_skips_empty_version_file(self, tmp_path: Path) -> None:
        """An empty VERSION file should trigger the fallback."""
        clone = tmp_path / "repo"
        clone.mkdir()
        (clone / ".git").mkdir()
        (clone / "VERSION").write_text("   \n")

        with (
            patch("fmapi_opskit.core.find_clone_dir", return_value=clone),
            patch("importlib.metadata.version", return_value="7.8.9"),
        ):
            assert get_version() == "7.8.9"


class TestIsCloneDir:
    """Tests for the _is_clone_dir() helper."""

    def test_valid_clone(self, tmp_path: Path) -> None:
        from fmapi_opskit.core import _is_clone_dir

        _make_clone(tmp_path / "clone")
        assert _is_clone_dir(tmp_path / "clone")

    def test_missing_git(self, tmp_path: Path) -> None:
        from fmapi_opskit.core import _is_clone_dir

        d = tmp_path / "no-git"
        d.mkdir()
        (d / "VERSION").write_text("1.0.0")
        assert not _is_clone_dir(d)

    def test_missing_version(self, tmp_path: Path) -> None:
        from fmapi_opskit.core import _is_clone_dir

        d = tmp_path / "no-version"
        d.mkdir()
        (d / ".git").mkdir()
        assert not _is_clone_dir(d)

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        from fmapi_opskit.core import _is_clone_dir

        assert not _is_clone_dir(tmp_path / "does-not-exist")
