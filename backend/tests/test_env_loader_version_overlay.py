"""APP_VERSION in .env selects the matching .env.<version> overlay (backend/env_loader.py).

Everything runs against throw-away directories - the real .env (which holds
secrets) is never read.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend import env_loader

REPO = Path(__file__).resolve().parents[2]

BASE = "APP_VERSION={v}\nSHARED=from-base\nBACKEND_PORT=7000\nLOG_DIR=logs_base\nSECRET_TOKEN=s3cr3t-do-not-log\n"
OVERLAY_55 = "BACKEND_PORT=8001\nLOG_DIR=logs_5.5\nBASE_REPO_PATH=D:\\RepoCore_5.5\n"
OVERLAY_60 = "BACKEND_PORT=8002\nLOG_DIR=logs_6.0\nAPP_600_REPO_ROOT=D:\\Repo6.0\n"

_KEYS = ("APP_VERSION", "SHARED", "BACKEND_PORT", "LOG_DIR", "BASE_REPO_PATH", "APP_600_REPO_ROOT",
         "SECRET_TOKEN", "ENV_FILE")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in _KEYS:
        monkeypatch.delenv(k, raising=False)
    yield
    for k in _KEYS:
        os.environ.pop(k, None)


def _repo(tmp_path, version, with_overlays=True, base_extra=""):
    (tmp_path / ".env").write_text(BASE.format(v=version) + base_extra, encoding="utf-8")
    if with_overlays:
        (tmp_path / ".env.5.5").write_text(OVERLAY_55, encoding="utf-8")
        (tmp_path / ".env.6.0").write_text(OVERLAY_60, encoding="utf-8")
    return str(tmp_path / ".env")


# ── version selection ────────────────────────────────────────────────────────
@pytest.mark.parametrize("version,port,log,repo_key,absent_key", [
    ("5.5", "8001", "logs_5.5", "BASE_REPO_PATH", "APP_600_REPO_ROOT"),
    ("6.0", "8002", "logs_6.0", "APP_600_REPO_ROOT", "BASE_REPO_PATH"),
])
def test_changing_only_app_version_selects_that_versions_settings(tmp_path, version, port, log, repo_key, absent_key):
    env_loader.load_env(_repo(tmp_path, version))
    assert os.environ["APP_VERSION"] == version
    assert os.environ["BACKEND_PORT"] == port              # overlay beats the base value (7000)
    assert os.environ["LOG_DIR"] == log
    assert repo_key in os.environ and absent_key not in os.environ
    assert os.environ["SHARED"] == "from-base"             # shared settings still come from .env
    assert env_loader.LAST_LOAD["version"] == version


def test_overlay_only_for_the_selected_version(tmp_path):
    env_loader.load_env(_repo(tmp_path, "6.0"))
    assert "BASE_REPO_PATH" not in os.environ              # 5.5's overlay was not read


def test_version_defaults_to_5_5_like_the_backend(tmp_path):
    (tmp_path / ".env").write_text("SHARED=x\n", encoding="utf-8")
    (tmp_path / ".env.5.5").write_text(OVERLAY_55, encoding="utf-8")
    env_loader.load_env(str(tmp_path / ".env"))
    assert os.environ["BACKEND_PORT"] == "8001"


# ── compatibility ────────────────────────────────────────────────────────────
def test_missing_overlay_changes_nothing(tmp_path):
    env_loader.load_env(_repo(tmp_path, "6.0", with_overlays=False))
    assert os.environ["BACKEND_PORT"] == "7000" and os.environ["LOG_DIR"] == "logs_base"
    assert env_loader.LAST_LOAD["overlay"] is None and env_loader.LAST_LOAD["overridden"] == []


def test_real_environment_variables_win_over_both_files(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND_PORT", "9999")
    env_loader.load_env(_repo(tmp_path, "5.5"))
    assert os.environ["BACKEND_PORT"] == "9999"
    assert "BACKEND_PORT" not in env_loader.LAST_LOAD["overridden"]


def test_overlay_cannot_change_app_version(tmp_path):
    base = _repo(tmp_path, "5.5")
    (tmp_path / ".env.5.5").write_text(OVERLAY_55 + "APP_VERSION=6.0\n", encoding="utf-8")
    env_loader.load_env(base)
    assert os.environ["APP_VERSION"] == "5.5"
    assert "ignored" in env_loader.LAST_LOAD["note"]


def test_env_file_keeps_its_old_meaning_and_skips_overlays(tmp_path, monkeypatch):
    base = _repo(tmp_path, "5.5")                          # an overlay exists next to it...
    other = tmp_path / ".env.custom"
    other.write_text("APP_VERSION=6.0\nBACKEND_PORT=8123\nAPP_600_REPO_ROOT=D:\\X\n", encoding="utf-8")
    monkeypatch.setenv("ENV_FILE", str(other))
    env_loader.load_env(base)
    assert os.environ["APP_VERSION"] == "6.0" and os.environ["BACKEND_PORT"] == "8123"
    assert env_loader.LAST_LOAD["overlay"] is None          # ...but ENV_FILE is authoritative on its own
    assert "SHARED" not in os.environ                       # the normal .env was not read at all


def test_env_file_overrides_the_real_environment_as_before(tmp_path, monkeypatch):
    other = tmp_path / ".env.custom"
    other.write_text("BACKEND_PORT=8123\n", encoding="utf-8")
    monkeypatch.setenv("BACKEND_PORT", "1")
    monkeypatch.setenv("ENV_FILE", str(other))
    env_loader.load_env()
    assert os.environ["BACKEND_PORT"] == "8123"             # load_dotenv(..., override=True), unchanged


def test_loading_twice_is_stable(tmp_path):
    base = _repo(tmp_path, "6.0")
    env_loader.load_env(base)
    env_loader.load_env(base)                               # e.g. dev_server then the reload subprocess
    assert os.environ["BACKEND_PORT"] == "8002" and os.environ["LOG_DIR"] == "logs_6.0"


# ── merged_values (SQL agent bootstrap) ──────────────────────────────────────
def test_merged_values_applies_the_overlay_without_touching_the_environment(tmp_path):
    values = env_loader.merged_values(_repo(tmp_path, "6.0"))
    assert values["BACKEND_PORT"] == "8002" and values["SHARED"] == "from-base"
    assert "BACKEND_PORT" not in os.environ and "SHARED" not in os.environ


def test_merged_values_without_a_file_is_empty(tmp_path):
    assert env_loader.merged_values(str(tmp_path / "nope.env")) == {}


# ── secrets ──────────────────────────────────────────────────────────────────
def test_the_log_line_lists_key_names_but_never_values(tmp_path):
    env_loader.load_env(_repo(tmp_path, "5.5"))
    line = env_loader.describe()
    assert "BACKEND_PORT" in line and "LOG_DIR" in line
    for leaked in ("8001", "logs_5.5", "s3cr3t-do-not-log", "RepoCore"):
        assert leaked not in line


# ── the config modules really follow the selected version ────────────────────
def _probe(tmp_path, version):
    base = _repo(tmp_path, version)
    code = (
        "import os\n"
        "from backend.env_loader import load_env\n"
        f"load_env(r'{base}')\n"
        "from backend import version_config, config\n"
        "print(version_config.IS_V6, config.BACKEND_PORT, os.environ['LOG_DIR'], config._USER_FILENAME)\n"
    )
    clean = {k: v for k, v in os.environ.items() if k not in _KEYS}
    out = subprocess.run([sys.executable, "-c", code], cwd=str(REPO), env=clean,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-600:]
    return out.stdout.strip().splitlines()[-1].split()


def test_backend_config_follows_app_version_5_5(tmp_path):
    assert _probe(tmp_path, "5.5") == ["False", "8001", "logs_5.5", "XML_User.xml"]


def test_backend_config_follows_app_version_6_0(tmp_path):
    assert _probe(tmp_path, "6.0") == ["True", "8002", "logs_6.0", "User.xml"]


# ── the shipped examples stay in step with the frontend profiles ─────────────
def _kv(path):
    from dotenv import dotenv_values
    return {k: v for k, v in dotenv_values(path).items() if v is not None}


@pytest.mark.parametrize("version,repo_key,other_key", [
    ("5.5", "BASE_REPO_PATH", "APP_600_REPO_ROOT"),
    ("6.0", "APP_600_REPO_ROOT", "BASE_REPO_PATH"),
])
def test_example_overlay_matches_the_frontend_profile(version, repo_key, other_key):
    back = _kv(REPO / f".env.{version}.example")
    front = _kv(REPO / "frontend" / "profiles" / f"{version}.env")
    assert back["BACKEND_PORT"] == front["BACKEND_PORT"]    # dist/web.config forwards to the port the backend opens
    assert back["LOG_DIR"] == f"logs_{version}"
    assert repo_key in back and other_key not in back
    assert "APP_VERSION" not in back                        # .env stays the single switch
    assert not any(w in k for k in back for w in ("PASSWORD", "SECRET", "TOKEN", "KEY"))   # no secrets in a tracked file
