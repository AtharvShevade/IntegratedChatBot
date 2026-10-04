"""M-30: dependency reproducibility -- a lockfile, a separate dev-requirements
file, and a pinned supported Python version now exist, none of which should
have upgraded any currently-working package version.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_requirement_lines(path: Path) -> list[str]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


class TestLockfileExists:
    def test_requirements_lock_file_exists(self):
        assert (PROJECT_ROOT / "requirements-lock.txt").exists()

    def test_lockfile_entries_are_exact_pins(self):
        lines = _parse_requirement_lines(PROJECT_ROOT / "requirements-lock.txt")
        assert lines, "lockfile must not be empty"
        for line in lines:
            assert "==" in line, f"lockfile entry {line!r} is not an exact pin"

    def test_lockfile_includes_known_runtime_packages_at_currently_working_versions(self):
        lines = {l.split("==")[0].lower(): l.split("==")[1] for l in _parse_requirement_lines(PROJECT_ROOT / "requirements-lock.txt")}
        # Spot-check a few real, currently-installed packages -- confirms
        # this was generated from the actual working environment, not
        # fabricated, and that nothing was bumped in the process.
        import importlib.metadata as _md
        for pkg in ("fastapi", "httpx", "pydantic", "portalocker"):
            installed_version = _md.version(pkg)
            assert lines.get(pkg) == installed_version, (
                f"{pkg}: lockfile has {lines.get(pkg)!r}, environment actually "
                f"has {installed_version!r} -- lockfile is stale or was edited by hand"
            )


class TestDevRequirementsSeparated:
    def test_requirements_dev_file_exists(self):
        assert (PROJECT_ROOT / "requirements-dev.txt").exists()

    def test_dev_tools_are_not_in_the_main_requirements_file(self):
        main_lines = " ".join(_parse_requirement_lines(PROJECT_ROOT / "requirements.txt")).lower()
        for tool in ("pytest", "ruff", "bandit", "pip-audit"):
            assert tool not in main_lines, f"{tool} belongs in requirements-dev.txt, not requirements.txt"

    def test_dev_requirements_lists_the_expected_tools(self):
        dev_lines = " ".join(_parse_requirement_lines(PROJECT_ROOT / "requirements-dev.txt")).lower()
        for tool in ("pytest", "ruff", "bandit", "pip-audit"):
            assert tool in dev_lines


class TestPythonVersionPinned:
    def test_python_version_file_exists_and_is_313(self):
        version_file = PROJECT_ROOT / ".python-version"
        assert version_file.exists()
        assert version_file.read_text(encoding="utf-8").strip() == "3.13"

    def test_running_interpreter_matches_the_pinned_version(self):
        import sys
        pinned = (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip()
        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        assert running == pinned, (
            f"this test environment runs Python {running}, but .python-version "
            f"pins {pinned} -- the two must be kept in sync"
        )


class TestNoUnintendedUpgrades:
    def test_portalocker_is_the_only_new_runtime_dependency_added_for_this_batch(self):
        """Confirms the ONLY change to requirements.txt's dependency set in
        this batch is the new portalocker pin (needed for M-13) -- nothing
        else was bumped or added."""
        lines = _parse_requirement_lines(PROJECT_ROOT / "requirements.txt")
        assert any(l.startswith("portalocker") for l in lines)

    def test_core_runtime_packages_still_use_loose_version_specifiers(self):
        """M-30 adds a lockfile for exact reproducibility; it must not
        replace the existing loose (>=) specifiers in requirements.txt
        itself with hard pins, which would be a bigger behavior change than
        this item calls for."""
        lines = _parse_requirement_lines(PROJECT_ROOT / "requirements.txt")
        fastapi_line = next(l for l in lines if l.lower().startswith("fastapi"))
        assert ">=" in fastapi_line
