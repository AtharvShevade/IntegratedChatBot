"""Phase 5 tests — templates.render().

NOTE on BASE_REPO_PATH: backend.config.BASE_REPO_PATH is a module-level
constant frozen at first import from os.getenv (this repo's .env points it
at a 5.5-shaped tree). access_control.scope_query -> auth_service resolves
the tenant's User.xml path via that constant regardless of which db_path
an XMLStore was built with, so the one tenant-scoped test below runs in a
fresh subprocess with BASE_REPO_PATH set BEFORE the interpreter starts
(same pattern as test_access_control.py).
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from backend.db_qa import templates
from backend.db_qa.intents.taxonomy import Intent

PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
REPO_ROOT = Path(__file__).resolve().parents[3]
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")


def test_every_intent_has_a_template():
    for intent in Intent:
        assert intent in templates.TEMPLATES, f"no template registered for {intent}"


def test_render_never_raises_on_missing_key():
    result = {"intent": "user_profile", "label": "X", "found": True, "records": [], "summary": "fallback text", "meta": {}}
    # Deliberately break the template to force the except-branch.
    original = templates.TEMPLATES[Intent.USER_PROFILE]
    templates.TEMPLATES[Intent.USER_PROFILE] = "{nonexistent_key}"
    try:
        out = templates.render(Intent.USER_PROFILE, result)
    finally:
        templates.TEMPLATES[Intent.USER_PROFILE] = original
    assert out == "fallback text"


def test_render_unknown_intent_string_falls_back_to_summary():
    result = {"summary": "some summary", "meta": {}}
    out = templates.render("not_a_real_intent", result)
    assert out == "some summary"


def test_display_value_masks_ciphertext_like_field():
    masked = templates._display_value("Name", "ThisLooksLikeABase64Blob123==")
    assert masked == templates._ENCRYPTED_PLACEHOLDER


def test_display_value_does_not_mask_normal_email():
    val = templates._display_value("EmailId", "someone@example.com")
    assert val == "someone@example.com"


def test_display_value_does_not_mask_unrelated_field():
    val = templates._display_value("Status", "true")
    assert val == "true"


@_need_6_0_1001
def test_render_real_user_profile_result():
    script = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from backend.db_qa import access_control, templates
        from backend.db_qa.query_handlers import dispatch2
        from backend.db_qa.xml_store import XMLStore

        store = XMLStore({str(PATH_6_0_1001)!r}, tenant_id="1001")
        scope = access_control.scope_query(
            {{"login_id": "vaibhav@irisindia.net", "tenant_id": "1001"}}, "user_profile", {{"target_type": "self"}},
        )
        result = dispatch2("user_profile", scope, {{"target_type": "self"}}, store)
        text = templates.render("user_profile", result)
        assert text == result["summary"], text
        assert text.startswith("Profile for "), text
        print("OK")
    """)
    env = dict(os.environ)
    env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "OK" in result.stdout
