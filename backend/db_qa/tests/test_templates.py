"""Phase 5 tests — templates.render()."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.db_qa import access_control, templates
from backend.db_qa.intents.taxonomy import Intent
from backend.db_qa.query_handlers import dispatch2
from backend.db_qa.xml_store import XMLStore

PATH_5_5 = Path(r"D:\Repo(new)\DataBase")
_need_5_5 = pytest.mark.skipif(not PATH_5_5.is_dir(), reason="5.5 real data tree not present")


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


@_need_5_5
def test_render_real_user_profile_result():
    store = XMLStore(str(PATH_5_5), tenant_id=None)
    scope = access_control.scope_query({"login_id": "iris810"}, "user_profile", {"target_type": "self"})
    result = dispatch2("user_profile", scope, {"target_type": "self"}, store)
    text = templates.render("user_profile", result)
    assert text == result["summary"]
    assert "iris810" in text
