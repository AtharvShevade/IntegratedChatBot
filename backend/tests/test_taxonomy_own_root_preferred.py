"""6.0: when a form's own taxonomy folder is among the schemaRef matches, only it is indexed."""
import os

from backend.tools import taxonomy_index as ti


def _mk(base, *parts):
    p = os.path.join(base, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def test_own_folder_wins_over_copies(tmp_path, monkeypatch):
    monkeypatch.setattr(ti.config, "_active_root", lambda: str(tmp_path))
    own = _mk(str(tmp_path), "DataBase", "4079", "Taxonomy")
    other = _mk(str(tmp_path), "DataBase", "4080", "Taxonomy")
    copy = _mk(str(tmp_path), "DataBase", "4079 - Copy", "Taxonomy")
    assert ti._candidate_roots("4079", (other, copy, own)) == (own,)


def test_foreign_schema_keeps_all_matches(tmp_path, monkeypatch):
    """Own folder holds a different return's files (the 4038/mpd07 case): keep the matches."""
    monkeypatch.setattr(ti.config, "_active_root", lambda: str(tmp_path))
    _mk(str(tmp_path), "DataBase", "4038", "Taxonomy")
    a = _mk(str(tmp_path), "DataBase", "4050", "Taxonomy")
    b = _mk(str(tmp_path), "DataBase", "4051", "Taxonomy")
    got = ti._candidate_roots("4038", (a, b))
    assert a in got and b in got
