"""New-taxonomy handlers — MENU_OPTIONS category."""
from __future__ import annotations

from backend.db_qa.xml_store import XMLStore


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def handle_menu_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    section = entities.get("section", "")
    options = [o for o in store.options() if o.get("IsMenu", "").lower() == "true"]
    if section:
        options = [o for o in options if section.lower() in o.get("OptionName", "").lower()]
    label = "My Menu" if scope["target_type"] == "self" else "System Menu & Modules"
    return _result("menu_list", label, options,
                   f"There are {len(options)} menu item(s)" + (f" under '{section}'." if section else "."),
                   count=len(options))


def handle_module_detail(scope: dict, entities: dict, store: XMLStore) -> dict:
    module = entities.get("module", "")
    option_id = entities.get("option_id", "")
    options = store.options()
    match = None
    if option_id:
        match = next((o for o in options if o.get("OptionId", "") == option_id), None)
    elif module:
        match = next((o for o in options if o.get("OptionName", "").lower() == module.lower()), None)
    if not match:
        return _not_found("module_detail", "Module Detail",
                          f"Module '{module or option_id}' not found." if (module or option_id)
                          else "Please specify a module name or option id.")
    return _result("module_detail", f"Module: {match.get('OptionName')}", [match],
                   f"Details for module '{match.get('OptionName')}'.")


def handle_module_children(scope: dict, entities: dict, store: XMLStore) -> dict:
    module = entities.get("module", "")
    if not module:
        return _not_found("module_children", "Module Children", "Please specify a parent module name.")
    parent = next((o for o in store.options() if o.get("OptionName", "").lower() == module.lower()), None)
    if not parent:
        return _not_found("module_children", "Module Children", f"Module '{module}' not found.")
    children = [o for o in store.options() if o.get("ParentOptionId", "") == parent.get("OptionId", "")]
    return _result("module_children", f"Children of {parent.get('OptionName')}", children,
                   f"Module '{parent.get('OptionName')}' has {len(children)} child module(s).", count=len(children))
