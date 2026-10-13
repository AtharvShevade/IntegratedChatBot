"""6.0 leaves InstanceDoc blank for failed runs, but the run's own
"<stem>_Instance.xml" sits beside "<stem>_Instance.html". The dimension
explainer may use that exact-stem sibling (6.0 only); 5.5 is unchanged."""
from __future__ import annotations

import pytest

from backend import version_config
from backend.tools import instance_context as ic

_INSTANCE_XML = '<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'


@pytest.fixture
def run_files(tmp_path):
    html = tmp_path / "RUN1_Instance.html"
    xml = tmp_path / "RUN1_Instance.xml"
    other = tmp_path / "RUN2_Instance.xml"          # a neighbouring run: must never be picked
    html.write_text("<html></html>")
    xml.write_text(_INSTANCE_XML)
    other.write_text(_INSTANCE_XML)
    return html, xml, other


def test_v6_uses_the_exact_stem_sibling(run_files, monkeypatch):
    html, xml, _ = run_files
    monkeypatch.setattr(version_config, "IS_V6", True)
    assert ic._same_run_sibling_instance(str(html)) == str(xml)


def test_v6_never_picks_a_neighbouring_run(tmp_path, monkeypatch):
    monkeypatch.setattr(version_config, "IS_V6", True)
    html = tmp_path / "RUN1_Instance.html"
    html.write_text("<html></html>")
    (tmp_path / "RUN2_Instance.xml").write_text(_INSTANCE_XML)
    assert ic._same_run_sibling_instance(str(html)) is None


def test_5_5_is_unchanged(run_files, monkeypatch):
    html, _, _ = run_files
    monkeypatch.setattr(version_config, "IS_V6", False)
    assert ic._same_run_sibling_instance(str(html)) is None


def test_only_html_error_files_have_a_sibling(run_files, monkeypatch):
    _, xml, _ = run_files
    monkeypatch.setattr(version_config, "IS_V6", True)
    assert ic._same_run_sibling_instance(str(xml)) is None


def test_find_instance_document_falls_back_only_when_the_log_has_none(run_files, monkeypatch):
    html, xml, _ = run_files
    monkeypatch.setattr(version_config, "IS_V6", True)
    import backend.tools.report_lookup as rl
    monkeypatch.setattr(rl, "resolve_instance_doc_path", lambda *a, **k: None)
    assert ic.find_instance_document(str(html), "4092") == str(xml)
    # a path recorded in the log still wins
    monkeypatch.setattr(rl, "resolve_instance_doc_path", lambda *a, **k: str(xml))
    assert ic.find_instance_document(str(html), "4092") == str(xml)
