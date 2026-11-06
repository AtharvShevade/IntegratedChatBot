"""Admin role (APP_DB_ADMIN_ROLE_ID) sees every return, whatever the department says.

Small temp XML files only: a user with the admin RoleId must get every Id from
Returns.xml / NonXBRLReturns.xml, even when the department row has no returns
or the department does not exist; other users still follow their department.
"""
from __future__ import annotations

import pytest

from backend.services import auth_service

USERS = """<Users>
<Row LoginId="boss" DepartmentId="9" RoleId="101"/>
<Row LoginId="boss_nodept" DepartmentId="" RoleId="101"/>
<Row LoginId="maker" DepartmentId="1" RoleId="102"/>
</Users>"""
DEPTS = """<Depts>
<Row DeptId="1" Forms="1001|1002" NXForms="6001"/>
<Row DeptId="9" Forms="" NXForms=""/>
</Depts>"""
RETURNS = '<Returns><Return Id="1001"/><Return Id="1002"/><Return Id="1003"/></Returns>'
NX = '<Returns><Return Id="6001"/><Return Id="6002"/></Returns>'


@pytest.fixture
def repo(tmp_path, monkeypatch):
    db = tmp_path / "DataBase"
    db.mkdir()
    (db / "XML_User.xml").write_text(USERS, encoding="utf-8")
    (db / "XML_Dept.xml").write_text(DEPTS, encoding="utf-8")
    (db / "Returns.xml").write_text(RETURNS, encoding="utf-8")
    (db / "NonXBRLReturns.xml").write_text(NX, encoding="utf-8")
    monkeypatch.setattr(auth_service, "xml_user_path", lambda: str(db / "XML_User.xml"))
    monkeypatch.setattr(auth_service, "xml_dept_path", lambda: str(db / "XML_Dept.xml"))
    monkeypatch.setattr(auth_service, "returns_xml_path", lambda: str(db / "Returns.xml"))
    monkeypatch.setattr(auth_service, "_db_path", lambda name: str(db / name))
    monkeypatch.setattr(auth_service, "AUTHORIZATION_ENABLED", True)
    monkeypatch.setenv("APP_DB_ADMIN_ROLE_ID", "101")
    auth_service._cache.clear()
    auth_service._nx_cache.clear()
    yield
    auth_service._cache.clear()
    auth_service._nx_cache.clear()


def test_admin_gets_every_return_even_with_empty_department(repo):
    assert auth_service.get_allowed_form_ids("boss") == {"1001", "1002", "1003"}
    assert auth_service.get_allowed_nx_form_ids("boss") == {"6001", "6002"}


def test_admin_without_department_still_gets_every_return(repo):
    assert auth_service.get_allowed_form_ids("boss_nodept") == {"1001", "1002", "1003"}


def test_non_admin_still_follows_department(repo):
    assert auth_service.get_allowed_form_ids("maker") == {"1001", "1002"}
    assert auth_service.get_allowed_nx_form_ids("maker") == {"6001"}


def test_admin_role_id_comes_from_env(repo, monkeypatch):
    monkeypatch.setenv("APP_DB_ADMIN_ROLE_ID", "102")
    auth_service._cache.clear()
    assert auth_service.get_allowed_form_ids("maker") == {"1001", "1002", "1003"}
    assert auth_service.get_allowed_form_ids("boss") == set()
