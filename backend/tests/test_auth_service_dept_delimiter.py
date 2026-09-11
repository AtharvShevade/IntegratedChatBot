"""Department ReturnId/Forms delimiter and NX-attribute name — version-aware.

D1/D2 fix, verified against REAL data (not fabricated fixtures):

  5.5: D:\\RepoCore_5.5\\DataBase\\XML_Dept.xml
       Forms="1001|1002|...|4074"   NXForms="6001|6002|..."   ("|"-joined)

  6.0: D:\\Repo6.0\\1001\\DataBase\\Department.xml
       ReturnId="2029,4089,4070"    NXReturnId="5001"          (","-joined)

Before this fix, auth_service._lookup() always split on "|" regardless of
version. A 6.0 department's comma-joined ReturnId has no "|" in it at all,
so the WHOLE string came back as one bogus form id -- every real 6.0 form id
check ("4076" in allowed_set) failed, silently denying access everywhere.

These tests point auth_service directly at the real files above (only
xml_dept_path/xml_user_path are patched -- no fabricated repo structure) and
assert the parsed set contains the individual ids, not one combined blob.

Uses unittest.mock.patch.dict as an explicit `with` block (same pattern as
test_auth_service.py's AuthServiceToggleTests), NOT pytest's monkeypatch, for
APP_VERSION: the `with` block reverts the env var deterministically before
each test function returns, so the module-reload-back below is never racing
a fixture-teardown ordering question.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

REAL_5_5_DEPT = Path(r"D:\RepoCore_5.5\DataBase\XML_Dept.xml")
REAL_5_5_USER = Path(r"D:\RepoCore_5.5\DataBase\XML_User.xml")
REAL_6_0_DEPT = Path(r"D:\Repo6.0\1001\DataBase\Department.xml")
REAL_6_0_USER = Path(r"D:\Repo6.0\1001\DataBase\User.xml")

pytestmark = pytest.mark.skipif(
    not (REAL_5_5_DEPT.is_file() and REAL_5_5_USER.is_file()
         and REAL_6_0_DEPT.is_file() and REAL_6_0_USER.is_file()),
    reason="real 5.5/6.0 repository fixtures not available on this machine",
)


def _reload_current():
    """Reload version_config then auth_service against whatever APP_VERSION
    os.environ currently holds."""
    from backend import version_config
    importlib.reload(version_config)
    from backend.services import auth_service
    importlib.reload(auth_service)
    return auth_service


@pytest.fixture(autouse=True)
def _restore_real_version_after_each_test():
    """Unconditionally reload back to the real environment's APP_VERSION
    after every test in this file -- runs after each test function has
    already exited its own `with patch.dict(...)` block, so os.environ is
    already back to the real value by the time this executes."""
    yield
    _reload_current()


# ---------------------------------------------------------------------------
# Test 1 / 5 — 6.0 normal ReturnId: comma-delimited, must split into
# individual ids, not one combined string (the actual regression).
# ---------------------------------------------------------------------------

def test_6_0_return_id_splits_on_comma_not_pipe(monkeypatch):
    with patch.dict(os.environ, {"APP_VERSION": "6.0"}):
        auth_service = _reload_current()
        monkeypatch.setattr(auth_service, "xml_dept_path", lambda: str(REAL_6_0_DEPT))
        monkeypatch.setattr(auth_service, "xml_user_path", lambda: str(REAL_6_0_USER))
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)

        # Real login from Department Id=1 ("Compliance"), ReturnId="2029,4089,4070".
        result = auth_service.get_allowed_form_ids("checker1@irisindia.net")

        assert result is not None
        assert result == {"2029", "4089", "4070"}, (
            f"expected 3 individual form ids, got {result!r} -- if this is "
            "one combined string, the comma/pipe delimiter regression is back"
        )
        assert "2029,4089,4070" not in result


# ---------------------------------------------------------------------------
# Test 3 — 6.0 NX: attribute is NXReturnId, not NXForms.
# ---------------------------------------------------------------------------

def test_6_0_nx_reads_nxreturnid_attribute(monkeypatch):
    with patch.dict(os.environ, {"APP_VERSION": "6.0"}):
        auth_service = _reload_current()
        monkeypatch.setattr(auth_service, "xml_dept_path", lambda: str(REAL_6_0_DEPT))
        monkeypatch.setattr(auth_service, "xml_user_path", lambda: str(REAL_6_0_USER))
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)

        result = auth_service.get_allowed_nx_form_ids("checker1@irisindia.net")

        assert result == {"5001"}


# ---------------------------------------------------------------------------
# Test 2 / 4 — 5.5 unchanged: Forms/NXForms still "|"-delimited.
# ---------------------------------------------------------------------------

def test_5_5_forms_still_splits_on_pipe(monkeypatch):
    with patch.dict(os.environ, {"APP_VERSION": "5.5"}):
        auth_service = _reload_current()
        monkeypatch.setattr(auth_service, "xml_dept_path", lambda: str(REAL_5_5_DEPT))
        monkeypatch.setattr(auth_service, "xml_user_path", lambda: str(REAL_5_5_USER))
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)

        # Real login "rohan11", DepartmentId="101" ("DSC"), Forms is a long
        # "|"-joined list including these ids among many others.
        result = auth_service.get_allowed_form_ids("rohan11")

        assert result is not None
        assert len(result) > 50, f"expected many individual ids, got {len(result)}"
        assert {"1001", "4046"} <= result
        assert "1001|1002" not in result  # never a fused/partial blob


def test_5_5_nx_still_reads_nxforms_attribute(monkeypatch):
    with patch.dict(os.environ, {"APP_VERSION": "5.5"}):
        auth_service = _reload_current()
        monkeypatch.setattr(auth_service, "xml_dept_path", lambda: str(REAL_5_5_DEPT))
        monkeypatch.setattr(auth_service, "xml_user_path", lambda: str(REAL_5_5_USER))
        monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)

        result = auth_service.get_allowed_nx_form_ids("rohan11")

        assert result is not None
        assert {"6001", "6012", "6026"} <= result


# ---------------------------------------------------------------------------
# Module-level constants, directly -- fast, no file I/O, pin the exact
# version-aware values down explicitly.
# ---------------------------------------------------------------------------

def test_module_constants_are_version_aware():
    with patch.dict(os.environ, {"APP_VERSION": "5.5"}):
        auth_5_5 = _reload_current()
        assert auth_5_5._DEPT_FORMS_DELIM == "|"
        assert auth_5_5._DEPT_NX_FORMS_ATTR == "NXForms"

    with patch.dict(os.environ, {"APP_VERSION": "6.0"}):
        auth_6_0 = _reload_current()
        assert auth_6_0._DEPT_FORMS_DELIM == ","
        assert auth_6_0._DEPT_NX_FORMS_ATTR == "NXReturnId"


def test_env_override_still_wins_over_version_default():
    """XML_DEPT_FORMS_DELIM / XML_DEPT_NX_FORMS_ATTR remain the escape hatch
    for a deployment whose data does not match either default."""
    with patch.dict(os.environ, {
        "APP_VERSION": "6.0",
        "XML_DEPT_FORMS_DELIM": ";",
        "XML_DEPT_NX_FORMS_ATTR": "CustomNX",
    }):
        auth_6_0 = _reload_current()
        assert auth_6_0._DEPT_FORMS_DELIM == ";"
        assert auth_6_0._DEPT_NX_FORMS_ATTR == "CustomNX"
