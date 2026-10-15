"""port_guard: the built dist/web.config (written for the selected APP_VERSION) is what must
match BACKEND_PORT; public/web.config is only the source default."""
from __future__ import annotations

import pytest

import port_guard

TEMPLATE = '<configuration><system.webServer><rewrite><rules><rule name="x"><action type="Rewrite" url="http://127.0.0.1:{port}/{{R:1}}"/></rule></rules></rewrite></system.webServer></configuration>'


def _write(root, rel, port):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(TEMPLATE.format(port=port), encoding="utf-8")


def test_matching_dist_passes_even_if_public_names_another_port(tmp_path):
    _write(tmp_path, "frontend/dist/web.config", 8002)
    _write(tmp_path, "frontend/public/web.config", 8001)     # source default of the other version
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_stale_dist_from_the_other_version_is_refused(tmp_path, capsys):
    _write(tmp_path, "frontend/dist/web.config", 8001)       # built for 5.5
    _write(tmp_path, "frontend/public/web.config", 8002)
    with pytest.raises(SystemExit):
        port_guard.assert_port_matches_web_config(8002, str(tmp_path))
    err = capsys.readouterr().err
    assert "frontend/dist/web.config" in err.replace("\\", "/") and "8001" in err and "npm run build" in err


def test_without_a_dist_the_public_file_is_checked(tmp_path):
    _write(tmp_path, "frontend/public/web.config", 8001)
    port_guard.assert_port_matches_web_config(8001, str(tmp_path))
    with pytest.raises(SystemExit):
        port_guard.assert_port_matches_web_config(8002, str(tmp_path))


def test_no_web_config_at_all_is_fine(tmp_path):
    port_guard.assert_port_matches_web_config(8001, str(tmp_path))


def test_skip_flag_still_bypasses(tmp_path, monkeypatch):
    _write(tmp_path, "frontend/dist/web.config", 8001)
    monkeypatch.setenv("SKIP_PORT_CHECK", "1")
    port_guard.assert_port_matches_web_config(8002, str(tmp_path))
