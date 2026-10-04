"""H-12: fields the 6.0 loader always emits (even when unmapped/absent in the
raw XML) can be ``None`` rather than missing — e.g. ``Option.xml`` has no
``IsMenu`` attribute at all, so ``versions/loader.py``'s ``_project_row``
still emits the key with value ``None`` (attribute_map maps it to ``None``).
A plain ``row.get("IsMenu", "").lower()`` only substitutes the default when
the *key itself* is missing, not when it is present with value ``None``, so
it crashes with ``AttributeError: 'NoneType' object has no attribute
'lower'``.

The fix reuses the existing ``get_attr()`` helper (already used elsewhere in
``xml_store.py`` for schema-inconsistency fallback) at every call site that
previously did ``row.get(key, "").lower()``/``.strip()`` — ``get_attr``
already treats "missing" and "present but None" identically, returning the
default in both cases.
"""
from __future__ import annotations

from backend.db_qa.xml_store import get_attr
from backend.db_qa.query_handlers.menu_handlers import handle_menu_list


class _FakeStore:
    def __init__(self, options):
        self._options = options

    def options(self):
        return self._options


class TestGetAttrNoneSafety:
    def test_missing_key_returns_default(self):
        assert get_attr({}, "IsMenu") == ""

    def test_key_present_with_none_returns_default(self):
        # This is the exact shape the 6.0 loader produces for an unmapped
        # attribute: the key exists, the value is None.
        assert get_attr({"IsMenu": None}, "IsMenu") == ""

    def test_normal_string_value_is_returned_unchanged(self):
        assert get_attr({"IsMenu": "True"}, "IsMenu") == "True"

    def test_empty_string_value_is_returned_as_is(self):
        assert get_attr({"IsMenu": ""}, "IsMenu") == ""

    def test_result_is_always_safe_to_call_lower_and_strip_on(self):
        for row in ({}, {"IsMenu": None}, {"IsMenu": "True"}, {"IsMenu": ""}):
            get_attr(row, "IsMenu").lower()
            get_attr(row, "IsMenu").strip()  # must not raise


class TestMenuListHandlerSurvivesNoneIsMenu:
    def test_handle_menu_list_does_not_crash_when_ismenu_is_none(self):
        # Reproduces the exact H-12 crash scenario: every 6.0 option row has
        # IsMenu present but set to None (no raw XML attribute exists for it).
        options = [
            {"Id": "1", "Name": "Users", "IsMenu": None, "ParentOptionId": None, "OptionName": "Users"},
            {"Id": "2", "Name": "Roles", "IsMenu": None, "ParentOptionId": None, "OptionName": "Roles"},
        ]
        store = _FakeStore(options)
        # Before the fix this raised AttributeError: 'NoneType' object has no
        # attribute 'lower'.
        result = handle_menu_list({"target_type": "system"}, {}, store)
        assert result["found"] is False  # None never equals "true", so no menu items match
        assert result["records"] == []

    def test_handle_menu_list_still_matches_true_ismenu(self):
        options = [
            {"Id": "1", "Name": "Users", "IsMenu": "True", "ParentOptionId": None, "OptionName": "Users"},
            {"Id": "2", "Name": "Roles", "IsMenu": "False", "ParentOptionId": None, "OptionName": "Roles"},
        ]
        store = _FakeStore(options)
        result = handle_menu_list({"target_type": "system"}, {}, store)
        assert result["found"] is True
        assert len(result["records"]) == 1
        assert result["records"][0]["Name"] == "Users"

    def test_handle_menu_list_section_filter_survives_none_optionname(self):
        # A second fragile call site in the same function: OptionName could
        # in principle also be present-but-None for an unmapped schema.
        options = [{"Id": "1", "Name": "X", "IsMenu": "True", "OptionName": None}]
        store = _FakeStore(options)
        result = handle_menu_list({"target_type": "system"}, {"section": "user"}, store)
        assert result["found"] is False
        assert result["records"] == []
