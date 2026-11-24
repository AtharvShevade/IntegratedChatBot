"""Error Resolution tab: upload an error file -> identify the return -> explain with the check-status engine."""
import asyncio
import os

import pytest

from backend.agent import error_upload as eu


@pytest.fixture(autouse=True)
def scratch(tmp_path, monkeypatch):
    monkeypatch.setenv("ERROR_UPLOAD_DIR", str(tmp_path / "scratch"))
    yield


# ── file acceptance ───────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("IDIB_4046_Instance.html", "IDIB_4046_Instance.html"),
    (r"C:\Users\me\Desktop\a b.xml", "a b.xml"),
    ("../../etc/x<y>.HTML", "x_y_.html"),
])
def test_safe_filename_keeps_only_a_clean_base_name(raw, expected):
    assert eu.safe_filename(raw) == expected


@pytest.mark.parametrize("raw", ["", "report.exe", "notes.txt", "x.html.exe", None])
def test_safe_filename_rejects_other_types(raw):
    with pytest.raises(eu.UploadError):
        eu.safe_filename(raw)


def test_check_content_rules():
    eu.check_content(b"<html><body><div id='accordionFormula'></div></body></html>", "a.html")
    eu.check_content(b"\xef\xbb\xbf<?xml version='1.0'?><Errors/>", "a.xml")
    for data, name in [(b"", "a.html"), (b"MZ\x00\x01binary", "a.html"), (b"just text", "a.xml"), (b"plain words", "a.html")]:
        with pytest.raises(eu.UploadError):
            eu.check_content(data, name)
    with pytest.raises(eu.UploadError):
        eu.check_content(b"<html>" + b"x" * (eu.MAX_BYTES + 1), "a.html")


# ── identification ────────────────────────────────────────────────────────────────────────────────────────────
def test_pick_winner_needs_a_clear_winner():
    assert eu.pick_winner([("4046", 1.0), ("4047", 0.5)]) == "4046"
    assert eu.pick_winner([("4046", 1.0), ("4047", 1.0)]) is None        # two returns share every rule: do not guess
    assert eu.pick_winner([("4046", 0.6)]) is None                        # not nearly all rules
    assert eu.pick_winner([]) is None


def test_identify_prefers_given_then_log_then_rules(monkeypatch):
    monkeypatch.setattr(eu, "form_from_instance_log", lambda n: "4049" if n == "known.html" else None)
    monkeypatch.setattr(eu, "rule_names_in", lambda html: ["R1", "R2"])
    monkeypatch.setattr(eu, "candidates_by_rules", lambda names, repo=None: [("4044", 1.0), ("4040", 0.4)])
    assert eu.identify("known.html", b"<html>", "4046")["method"] == "given"
    assert eu.identify("known.html", b"<html>")["form_id"] == "4049"
    got = eu.identify("other.html", b"<html>")
    assert (got["form_id"], got["method"]) == ("4044", "rules")
    monkeypatch.setattr(eu, "candidates_by_rules", lambda names, repo=None: [("4044", 0.5), ("4040", 0.5)])
    got = eu.identify("other.html", b"<html>")
    assert got["form_id"] is None and got["method"] == "none" and len(got["candidates"]) == 2
    with pytest.raises(eu.UploadError):
        eu.identify("x.html", b"<html>", "abc")


def test_rule_index_and_candidates(tmp_path):
    for form, ids in {"4046": ["RuleA", "RuleB"], "4047": ["RuleA"]}.items():
        d = tmp_path / "DataBase" / form / "Taxonomy"
        d.mkdir(parents=True)
        body = "".join(f'<va:valueAssertion id="{i}" test="1"/>' for i in ids)
        (d / "x_formula.xml").write_text(f"<root>{body}</root>", encoding="utf-8")
    eu._RULE_INDEX.clear()
    got = eu.candidates_by_rules(["RuleA", "RuleB"], repo=str(tmp_path))
    assert got[0] == ("4046", 1.0) and got[1] == ("4047", 0.5)
    assert eu.pick_winner(got) == "4046"


# ── storage, ownership, expiry ────────────────────────────────────────────────────────────────────────────────
def test_store_load_and_owner_only():
    uid = eu.store(b"<html></html>", "a.html", "4046", "alice", {"method": "given"})
    assert eu.load_meta(uid, "alice")["form_id"] == "4046"
    assert os.path.isfile(eu.file_path(uid, eu.load_meta(uid, "alice")))
    assert os.path.normpath(eu.file_path(uid, eu.load_meta(uid, "alice"))).split(os.sep)[-3:-1] == ["Instance", "4046"]
    with pytest.raises(eu.UploadError):
        eu.load_meta(uid, "bob")                                          # someone else's upload looks like an expired one
    with pytest.raises(eu.UploadError):
        eu.load_meta("../../etc", "alice")                                # not an id we made


def test_set_form_moves_the_file_under_the_chosen_return():
    uid = eu.store(b"<html></html>", "a.html", None, "alice", {"method": "none"})
    meta = eu.set_form(uid, "alice", "4046")
    assert meta["form_id"] == "4046" and os.path.isfile(eu.file_path(uid, meta))
    assert not os.path.exists(os.path.join(eu.scratch_root(), uid, "Instance", "_unknown", "a.html"))
    with pytest.raises(eu.UploadError):
        eu.set_form(uid, "alice", "40x6")


def test_purge_expired_removes_only_old_uploads():
    old = eu.store(b"<html></html>", "a.html", "1", "u", {})
    new = eu.store(b"<html></html>", "b.html", "1", "u", {})
    t = os.path.getmtime(os.path.join(eu.scratch_root(), old)) - eu.RETENTION_SECONDS - 5
    os.utime(os.path.join(eu.scratch_root(), old), (t, t))
    assert eu.purge_expired() == 1
    assert not os.path.exists(os.path.join(eu.scratch_root(), old)) and os.path.exists(os.path.join(eu.scratch_root(), new))


# ── batches reuse the check-status pipeline ───────────────────────────────────────────────────────────────────
def test_explain_batch_shapes_like_explain_category(monkeypatch):
    uid = eu.store(b"<html></html>", "a.html", "4046", "alice", {"method": "given"})
    import backend.tools.report_lookup as rl
    monkeypatch.setattr(rl, "explain_errors_by_category_for_form", lambda path, cat, form, off, lang: [{"rule_name": "R"}] * 3)
    monkeypatch.setattr(rl, "count_errors_by_category", lambda path, form_id="": {"formula_error": 5, "formula_warning": 1, "formula_total": 6})
    res = asyncio.run(eu.explain_batch(uid, "alice", "formula_error", 0))
    assert res["result_type"] == "final" and len(res["error_details"]) == 3
    assert res["data"]["has_more"] is True and res["data"]["next_offset"] == 3 and res["data"]["total_count"] == 6
    bad = asyncio.run(eu.explain_batch(uid, "alice", "nonsense", 0))
    assert bad["result_type"] == "error"


# ── HTTP wiring ───────────────────────────────────────────────────────────────────────────────────────────────
def test_endpoints_upload_form_explain(monkeypatch):
    from fastapi.testclient import TestClient
    import backend.main as m
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    monkeypatch.setattr(m, "_caller_may_access_form", lambda login, form: login == "alice")
    monkeypatch.setattr(m, "_caller_is_authenticated", lambda login: bool(login))
    monkeypatch.setattr(eu, "form_from_instance_log", lambda n: None)
    monkeypatch.setattr(eu, "candidates_by_rules", lambda names, repo=None: [])
    monkeypatch.setattr(eu, "summarise", lambda uid, meta: {"upload_id": uid, "filename": meta["filename"], "form_id": meta.get("form_id") or "",
                                                           "error_category_counts": {"filename": meta["filename"], "formula_error": 2}})
    c = TestClient(m.app)
    html = b"<html><body><div>x</div></body></html>"
    # a wrong type is refused before anything is stored
    r = c.post("/error-resolution/upload", files={"file": ("a.exe", b"MZ", "application/octet-stream")}, data={"login_id": "alice"})
    assert r.status_code == 422
    # not identified: the user is asked for the return
    r = c.post("/error-resolution/upload", files={"file": ("a.html", html, "text/html")}, data={"login_id": "alice"})
    assert r.status_code == 200 and r.json()["needs_form"] is True
    uid = r.json()["upload_id"]
    # picking a return the caller may not see is refused; one they may see re-files the upload
    assert c.post("/error-resolution/form", json={"upload_id": uid, "form_id": "4046", "login_id": "bob"}).status_code == 403
    r = c.post("/error-resolution/form", json={"upload_id": uid, "form_id": "4046", "login_id": "alice"})
    assert r.status_code == 200 and r.json()["form_id"] == "4046" and r.json()["needs_form"] is False
    # another user cannot read it
    assert c.post("/error-resolution/explain", json={"upload_id": uid, "category": "formula_error", "login_id": "bob"}).status_code in (403, 422)
    # the owner gets a normal explain-category-shaped response
    import backend.tools.report_lookup as rl
    monkeypatch.setattr(rl, "explain_errors_by_category_for_form", lambda *a, **k: [{"rule_name": "R", "explanation": "x"}])
    monkeypatch.setattr(rl, "count_errors_by_category", lambda *a, **k: {"formula_error": 1, "formula_total": 1})
    r = c.post("/error-resolution/explain", json={"upload_id": uid, "category": "formula_error", "login_id": "alice"})
    assert r.status_code == 200 and r.json()["result_type"] == "final" and r.json()["error_details"][0]["rule_name"] == "R"
