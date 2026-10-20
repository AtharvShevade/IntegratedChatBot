"""port_guard: compares BACKEND_PORT with the web.config IIS really uses.

Order: WEB_CONFIG_PATH (the deployed IIS site's web.config) -> frontend/dist/web.config
(a local build) -> nothing. frontend/public/web.config is only the build's template and is
never checked, because APP_VERSION does not change it.
"""
from __future__ import annotations

import pytest

import port_guard

TEMPLATE = '<configuration><system.webServer><rewrite><rules><rule name="x"><action type="Rewrite" url="http://127.0.0.1:{port}/{{R:1}}"/></rule></rules></rewrite></system.webServer></configuration>'


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("WEB_CONFIG_PATH", raising=False)
    monkeypatch.delenv("SKIP_PORT_CHECK", raising=False)


def _write(path, port):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(port=port), encoding="utf-8")
    return path


# ── the server case that motivated this ─────────────────────────────────────
def test_server_without_a_dist_folder_is_not_checked_against_the_template(tmp_path):
    _write(tmp_path / "frontend/public/web.config", 8001)     # 5.5 default template in git
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))     # 6.0 backend: must start


def test_deployed_web_config_via_env_matching_passes(tmp_path, monkeypatch):
    site = _write(tmp_path / "iis_site/web.config", 8002)
    _write(tmp_path / "frontend/public/web.config", 8001)     # still ignored
    monkeypatch.setenv("WEB_CONFIG_PATH", str(site))
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_deployed_web_config_via_env_mismatch_is_refused(tmp_path, monkeypatch, capsys):
    site = _write(tmp_path / "iis_site/web.config", 8001)      # a 5.5 build deployed by mistake
    monkeypatch.setenv("WEB_CONFIG_PATH", str(site))
    with pytest.raises(SystemExit):
        port_guard.assert_port_matches_web_config(8002, str(tmp_path))
    err = capsys.readouterr().err
    assert "WEB_CONFIG_PATH" in err and "8001" in err and "8002" in err and "redeploy" in err


def test_env_path_beats_a_local_dist(tmp_path, monkeypatch):
    site = _write(tmp_path / "iis_site/web.config", 8002)
    _write(tmp_path / "frontend/dist/web.config", 8001)        # stale local build is irrelevant on that host
    monkeypatch.setenv("WEB_CONFIG_PATH", str(site))
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_relative_env_path_is_resolved_from_the_project_root(tmp_path, monkeypatch):
    _write(tmp_path / "site/web.config", 8002)
    monkeypatch.setenv("WEB_CONFIG_PATH", "site/web.config")
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_quoted_env_path_is_accepted(tmp_path, monkeypatch):
    site = _write(tmp_path / "iis site/web.config", 8002)
    monkeypatch.setenv("WEB_CONFIG_PATH", f'"{site}"')
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_missing_env_path_warns_and_skips_instead_of_failing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WEB_CONFIG_PATH", str(tmp_path / "nope" / "web.config"))
    _write(tmp_path / "frontend/dist/web.config", 8001)        # not consulted once a path was configured
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))
    assert "does not exist" in capsys.readouterr().err


# ── local development, unchanged ─────────────────────────────────────────────
def test_local_dist_matching_passes_even_if_public_names_another_port(tmp_path):
    _write(tmp_path / "frontend/dist/web.config", 8002)
    _write(tmp_path / "frontend/public/web.config", 8001)
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_stale_local_dist_from_the_other_version_is_refused(tmp_path, capsys):
    _write(tmp_path / "frontend/dist/web.config", 8001)        # built for 5.5
    with pytest.raises(SystemExit):
        port_guard.assert_port_matches_web_config(8002, str(tmp_path))
    err = capsys.readouterr().err
    assert "frontend/dist/web.config" in err.replace("\\", "/") and "8001" in err and "npm run build" in err


def test_no_web_config_anywhere_is_fine(tmp_path):
    port_guard.assert_port_matches_web_config(8001, str(tmp_path))


def test_a_web_config_without_a_rewrite_rule_is_fine(tmp_path):
    (tmp_path / "frontend/dist").mkdir(parents=True)
    (tmp_path / "frontend/dist/web.config").write_text("<configuration/>", encoding="utf-8")
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_skip_flag_still_bypasses(tmp_path, monkeypatch):
    site = _write(tmp_path / "iis_site/web.config", 8001)
    monkeypatch.setenv("WEB_CONFIG_PATH", str(site))
    monkeypatch.setenv("SKIP_PORT_CHECK", "1")
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))
