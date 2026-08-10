"""New-taxonomy handlers — ROLE, ROLE_ACCESS, USER_LEVEL categories."""
from __future__ import annotations

import asyncio
import concurrent.futures
import re

from collections import Counter

from backend.db_qa.versions.loader import build_index
from backend.db_qa.xml_store import XMLStore, get_attr, is_active_status
from backend.db_qa.query_handlers._extraction_guard import (
    UNDERSTAND_FAILURE_MSG as _UNDERSTAND_FAILURE_MSG,
    looks_like_extraction_garbage,
)

# Sentinel attribute meaning "any of the four flags" -- see _flag_true.
ANY_FLAG = "__ANY__"

_ACTION_MAP: dict[str, str] = {
    "new": "HasNew", "create": "HasNew", "add": "HasNew",
    # No dedicated RoleAccess flag exists for "upload" — treated as a
    # creation action (closest fit), same as new_intent_classifier.ACTION_MAP.
    "upload": "HasNew",
    "edit": "HasEdit", "update": "HasEdit", "modify": "HasEdit",
    "view": "HasView", "see": "HasView", "read": "HasView",
    "approve": "HasApprove", "approval": "HasApprove",
    # "generate"/"disable" resolved ONLY via the LLM normalizer before
    # (llm_service.normalize_action_word, whose own docstring uses
    # "generate" -> "create" as its example). That call costs a real
    # round trip -- measured at 19-26s here, since it retries twice --
    # and returns nothing at all when the Ollama proxy is unreachable,
    # so the user waited ~26s to be told the request wasn't understood.
    # Both verbs map unambiguously, so resolve them deterministically and
    # leave the LLM for genuinely ambiguous verbs ("run", "manage",
    # "perform", "delete" -- no HasExecute/HasDelete flag exists).
    "generate": "HasNew",
    "disable": "HasEdit",
    # "access"/"use"/"run"/"perform" do NOT name one of the four flags --
    # they ask whether the role has ANY permission on the module at all.
    # There is no HasAccess column, so every one of these previously missed
    # _ACTION_MAP, fell through to the LLM, and came back "Sorry, I couldn't
    # understand your request" -- 17 catalogue questions in ROLE_ACCESS
    # alone ("Can I access the Balance Sheet module?", "Which roles can
    # access X?", "Can I run cross-validation?", "What modules am I allowed
    # to access?"). ANY_FLAG is a sentinel, not a column name; the two
    # handlers below test it against all four flags instead of one.
    "access": ANY_FLAG, "use": ANY_FLAG, "run": ANY_FLAG, "perform": ANY_FLAG,
}


def _flag_true(row: dict, attr: str) -> bool:
    """Is *attr* granted on this XML_RoleAccess row? ANY_FLAG means "any of
    the four", which is what "can I access X" actually asks."""
    if attr == ANY_FLAG:
        return any(row.get(f, "false").lower() == "true" for f in _ALL_FLAGS)
    return row.get(attr, "false").lower() == "true"

_ALL_FLAGS = ("HasNew", "HasEdit", "HasView", "HasApprove")


_ATTR_TO_CANONICAL_WORD = {"HasNew": "create", "HasEdit": "edit", "HasView": "view",
                            "HasApprove": "approve", ANY_FLAG: "access"}


def _display_action_word(action_word: str, attr: str) -> str:
    """The verb to show the user for a resolved permission check.

    Two separate corrections, one from each branch:
    - action_word is "" when attr was only resolved via the LLM raw_query
      fallback (see _resolve_action_attr), so the summary would read
      "You can ." — substitute the canonical verb for the attribute.
    - "approval" is a noun form extracted verbatim from phrasings like
      "Do I have approval rights...?", which would read "You can
      approval." — substitute the verb form.
    """
    word = action_word or _ATTR_TO_CANONICAL_WORD.get(attr, action_word)
    return "approve" if word.lower() == "approval" else word


def _resolve_action_attr(action_word: str, raw_query: str = "") -> str:
    """Look up the raw action verb in _ACTION_MAP; on a miss, fall back to
    the LLM normalizer (backend.services.llm_service.normalize_action_word)
    to catch verbs the fixed keyword list doesn't know (e.g. "generate" for
    "create"). dispatch2()/these handlers are all plain sync — this bridges
    the one async LLM call synchronously rather than threading async/await
    through dispatch2 and its ~30 direct test call sites.

    action_word is usually already "" here, not the literal unrecognized
    word: new_intent_classifier._extract_raw_action_word only recognizes
    the same fixed canonical verb list, so an unknown verb comes back None
    and gets stripped before reaching this handler — raw_query (the full
    user question, passed through as entities["raw_query"]) is what
    actually carries the unrecognized verb for the LLM to work with.

    Returns "" (same as a regex miss) if the LLM also declines or errors.
    """
    attr = _ACTION_MAP.get(action_word.lower(), "")
    if attr:
        return attr
    if not action_word and not raw_query:
        return ""
    from backend.services.llm_service import normalize_action_word
    canonical = _run_coro_sync(normalize_action_word(raw_query or action_word))
    return _ACTION_MAP.get(canonical or "", "")


def _run_coro_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # A loop is already running in this thread (e.g. dispatch2() called
    # synchronously from inside agent/__init__.py's async decide()) —
    # asyncio.run() would raise "already running", so run the coroutine on
    # its own loop in a throwaway thread instead.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()



def _module_matches(module: str, option_name: str) -> bool:
    """Does an extracted module value select this XML_RoleAccess OptionName?

    Substring match (the convention new_intent_classifier._MODULE_SYNONYMS'
    canonical values are built around -- "report" deliberately selects every
    Report-family module), with ONE carve-out: "-" is a non-word character,
    so every "xbrl ..." canonical is also a literal substring of the
    corresponding "Non-XBRL ..." OptionName. Without this guard,
    module="xbrl generation" selected BOTH 'XBRL Generation' and 'Non-XBRL
    Generation', so "can i generate xbrl?" silently answered using the
    caller's non-XBRL permissions too -- breaking the XBRL/non-XBRL
    separation this module is otherwise careful about. The reverse is safe
    ("non-xbrl ..." is not a substring of any XBRL name), which is why only
    this direction is rejected.
    """
    if not module:
        return True
    m, o = module.lower(), option_name.lower()
    if m not in o:
        return False
    return not (m.startswith("xbrl") and "non-xbrl" in o)


def _result(intent: str, label: str, records: list, summary: str, **meta) -> dict:
    return {"intent": intent, "label": label, "found": bool(records), "records": records, "summary": summary, "meta": meta}


# This rule started life here as a role-only word list; it is now shared
# with departments and returns, which had the same leak.
_looks_like_garbage = looks_like_extraction_garbage


def _role_not_found(intent: str, label: str, name: str | None) -> dict:
    """Shared not-found response for every handler that resolves a target
    role by name — mirrors department_handlers._department_not_found's
    reasoning: a genuinely empty or grammar-only extraction means the
    QUESTION wasn't understood (ask to rephrase), never a leaked internal
    parser fragment presented as if it were the user's real input."""
    name = (name or "").strip()
    if not name or _looks_like_garbage(name):
        return _not_found(intent, label, _UNDERSTAND_FAILURE_MSG)
    return _not_found(intent, label, f"Role '{name}' was not found.")


def _not_found(intent: str, label: str, msg: str) -> dict:
    return _result(intent, label, [], msg)


def _resolve_target_role(store: XMLStore, scope: dict, entities: dict) -> dict | None:
    if scope["target_type"] == "self":
        u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
        if not u:
            return None
        role_id = get_attr(u, "RoleId", "Role_Id", default="")
        return store.role_by_id(role_id) if role_id else None
    # A numeric role_id ("what is the name of role ID 106?") takes priority
    # over target_role — the latter can still be extraction noise (e.g.
    # "ID 106") in that phrasing, since the ID itself is the actual target.
    role_id = entities.get("role_id", "")
    if role_id:
        role = store.role_by_id(role_id)
        if role:
            return role
    target = entities.get("target_role", "")
    return store.resolve_role(target) if target else None


def handle_role_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    query_type = (entities.get("query_type") or "all").lower()
    roles = store.roles()

    if query_type == "count":
        active = sum(1 for r in roles if is_active_status(r.get("Status")))
        return _result("role_list", "Role Count",
                       [{"total": len(roles), "active": active, "inactive": len(roles) - active}],
                       f"Total roles: {len(roles)} ({active} active, {len(roles) - active} inactive).",
                       total=len(roles), active=active)
    elif query_type == "active_count":
        n = sum(1 for r in roles if is_active_status(r.get("Status")))
        return _result("role_list", "Active Role Count", [{"active": n}], f"Active roles: {n}.", active=n)
    elif query_type == "inactive_count":
        n = sum(1 for r in roles if not is_active_status(r.get("Status")))
        return _result("role_list", "Inactive Role Count", [{"inactive": n}], f"Inactive roles: {n}.", inactive=n)
    elif query_type == "active":
        rows = [r for r in roles if is_active_status(r.get("Status"))]
        label, summary = "Active Roles", f"There are {len(rows)} active roles."
    elif query_type == "inactive":
        rows = [r for r in roles if not is_active_status(r.get("Status"))]
        label, summary = "Inactive Roles", f"There are {len(rows)} inactive roles."
    elif query_type in ("most_users", "least_users", "with_counts"):
        counts = Counter(get_attr(u, "RoleId", "Role_Id", default="") for u in store.users())
        enriched = []
        for r in roles:
            row = dict(r)
            row["UserCount"] = counts.get(get_attr(r, "RoleId", "Role_Id", default=""), 0)
            enriched.append(row)
        if query_type == "most_users":
            enriched.sort(key=lambda r: r["UserCount"], reverse=True)
            rows = enriched[:1]
            label = "Role With Most Users"
            summary = f"'{rows[0].get('Name')}' has the most users ({rows[0]['UserCount']})." if rows else "No roles found."
        elif query_type == "least_users":
            enriched.sort(key=lambda r: r["UserCount"])
            rows = enriched[:1]
            label = "Role With Fewest Users"
            summary = f"'{rows[0].get('Name')}' has the fewest users ({rows[0]['UserCount']})." if rows else "No roles found."
        else:
            rows = enriched
            label, summary = "All Roles (With User Counts)", f"There are {len(rows)} roles."
    elif query_type == "exists":
        target = entities.get("target_role", "")
        if not target or _looks_like_garbage(target):
            return _not_found("role_list", "Role Existence Check", _UNDERSTAND_FAILURE_MSG)
        match = store.role_by_name(target)
        rows = [match] if match else []
        label = "Role Existence Check"
        summary = (f"Yes, role '{target}' exists." if match else f"No role named '{target}' was found.")
    else:
        rows = roles
        label, summary = "All Roles", f"There are {len(rows)} roles defined in the system."

    return _result("role_list", label, rows, summary, count=len(rows))


def handle_role_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    role = _resolve_target_role(store, scope, entities)
    if not role:
        if scope["target_type"] == "self":
            return _not_found("role_profile", "Role Profile", "Your role could not be found.")
        name = entities.get("target_role") or entities.get("role_id")
        return _role_not_found("role_profile", "Role Profile", name)
    label = "My Role" if scope["target_type"] == "self" else f"Role: {role.get('Name')}"
    who_phrase = "Your" if scope["target_type"] == "self" else "The"
    active = is_active_status(role.get("Status"))
    return _result("role_profile", label, [role],
                   f"{who_phrase} role is '{role.get('Name')}' (id {get_attr(role, 'RoleId', 'Role_Id', default='')}), "
                   f"which is currently {'active' if active else 'inactive'}.")


def handle_role_users(scope: dict, entities: dict, store: XMLStore) -> dict:
    target = entities.get("target_role", "")
    role = store.resolve_role(target) if target else None
    if not role:
        return _role_not_found("role_users", "Users With Role", target)
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    users = [store.enrich_user(u) for u in store.users() if get_attr(u, "RoleId", "Role_Id") == role_id]
    return _result("role_users", f"Users with Role: {role.get('Name')}", users,
                   f"Found {len(users)} user(s) with role '{role.get('Name')}'.",
                   role_name=role.get("Name"), count=len(users))


def handle_role_peer_count(scope: dict, entities: dict, store: XMLStore) -> dict:
    u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
    if not u:
        return _not_found("role_peer_count", "Users with My Role", "Your profile could not be found.")
    role_id = get_attr(u, "RoleId", "Role_Id", default="")
    my_uid = u.get("UserId", "")
    peers = [pu for pu in store.users()
             if get_attr(pu, "RoleId", "Role_Id") == role_id and pu.get("UserId") != my_uid]
    role_name = store.role_name_by_id(role_id)
    return _result("role_peer_count", f"Users with Role: {role_name}",
                   [store.enrich_user(p) for p in peers],
                   f"{len(peers)} other user(s) share the '{role_name}' role with you.",
                   role_name=role_name, count=len(peers))


def handle_permission_profile(scope: dict, entities: dict, store: XMLStore) -> dict:
    role = _resolve_target_role(store, scope, entities)
    if not role:
        if scope["target_type"] == "self":
            return _not_found("permission_profile", "Permission Profile", "Your role could not be found.")
        return _role_not_found("permission_profile", "Permission Profile", entities.get("target_role"))
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    accesses = [store.enrich_role_access(a) for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]
    who_phrase = "Your role" if scope["target_type"] == "self" else f"Role '{role.get('Name')}'"
    query_type = entities.get("query_type")

    if query_type == "full_control":
        # Only modules where the role has ALL FOUR flags — "which modules
        # does role X have full control over".
        full = [a for a in accesses if all(a.get(f, "false").lower() == "true" for f in _ALL_FLAGS)]
        label = ("My Full-Control Modules" if scope["target_type"] == "self"
                  else f"Full-Control Modules: {role.get('Name')}")
        return _result("permission_profile", label, full,
                       f"{who_phrase} has full control (create, edit, view, and approve) over {len(full)} module(s).",
                       role_name=role.get("Name"), count=len(full))

    if query_type == "not_access":
        # The complement — every known module the role has NO access to at
        # all (none of create/edit/view/approve is true). "All known
        # modules" is the menu's own option list (store.options()), not
        # just the modules that happen to have a RoleAccess row for this
        # role, since a module with no row at all is just as "not
        # accessible" as one whose row has every flag false.
        accessible_names = {
            a.get("OptionName", "") for a in accesses
            if any(a.get(f, "false").lower() == "true" for f in _ALL_FLAGS)
        }
        all_names = sorted({o.get("OptionName", "") for o in store.options() if o.get("OptionName")})
        not_accessible = [{"OptionName": n} for n in all_names if n not in accessible_names]
        label = ("What I Don't Have Access To" if scope["target_type"] == "self"
                  else f"Not Accessible: {role.get('Name')}")
        return _result("permission_profile", label, not_accessible,
                       f"{who_phrase} does not have access to {len(not_accessible)} module(s)."
                       if not_accessible else f"{who_phrase} has access to every module in the system.",
                       role_name=role.get("Name"), count=len(not_accessible))

    label = "My Permissions" if scope["target_type"] == "self" else f"Permissions for Role: {role.get('Name')}"
    return _result("permission_profile", label, accesses,
                   f"{who_phrase} has access to {len(accesses)} module(s).",
                   role_name=role.get("Name"), count=len(accesses))


def handle_permission_check(scope: dict, entities: dict, store: XMLStore) -> dict:
    role = _resolve_target_role(store, scope, entities)
    if not role:
        if scope["target_type"] == "self":
            return _not_found("permission_check", "Permission Check", "Your role could not be found.")
        return _role_not_found("permission_check", "Permission Check", entities.get("target_role"))
    action_word = entities.get("action", "")
    attr = _resolve_action_attr(action_word, entities.get("raw_query", ""))
    if not attr:
        return _not_found("permission_check", "Permission Check", _UNDERSTAND_FAILURE_MSG)
    role_id = get_attr(role, "RoleId", "Role_Id", default="")
    module = entities.get("module", "")
    accesses = [store.enrich_role_access(a) for a in store.role_access()
                if get_attr(a, "RoleId", "Role_Id") == role_id]
    if module:
        accesses = [a for a in accesses if _module_matches(module, a.get("OptionName", ""))]
    allowed = [a for a in accesses if _flag_true(a, attr)]
    who_phrase = "You" if scope["target_type"] == "self" else role.get("Name", "")
    can = "can" if allowed else "cannot"
    module_phrase = f" on {module}" if module else ""
    display_word = _display_action_word(action_word, attr)
    return _result("permission_check", f"Permission Check: {display_word}{module_phrase}",
                   allowed, f"{who_phrase} {can} {display_word}{module_phrase}.",
                   action=display_word, module=module, count=len(allowed))


def _dedup_roles_preserve_order(roles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for r in roles:
        rid = get_attr(r, "RoleId", "Role_Id", default="")
        if rid not in seen:
            seen.add(rid)
            unique.append(r)
    return unique


def handle_roles_with_permission(scope: dict, entities: dict, store: XMLStore) -> dict:
    module = entities.get("module", "")
    query_type = entities.get("query_type")
    role_index = build_index(store.roles(), "RoleId")

    if query_type == "no_edit_create":
        # Role-level aggregate, not module-specific: a role qualifies only
        # if NONE of its RoleAccess rows (across every module) has HasNew
        # or HasEdit set — "no edit or create permissions AT ALL".
        disqualified: set[str] = set()
        seen_roles: set[str] = set()
        for a in store.role_access():
            rid = get_attr(a, "RoleId", "Role_Id", default="")
            seen_roles.add(rid)
            if a.get("HasNew", "false").lower() == "true" or a.get("HasEdit", "false").lower() == "true":
                disqualified.add(rid)
        qualifying_ids = seen_roles - disqualified
        matches = [role_index[rid] for rid in qualifying_ids if rid in role_index]
        return _result("roles_with_permission", "Roles With No Edit Or Create Permissions",
                       matches, f"{len(matches)} role(s) have no edit or create permissions at all.",
                       count=len(matches))

    if query_type == "full_access":
        # ALL FOUR flags true for the same role+module — "full access" per
        # the brief's own definition (create + edit + view + approve).
        matches = []
        for a in store.role_access():
            if not all(a.get(f, "false").lower() == "true" for f in _ALL_FLAGS):
                continue
            if not _module_matches(module, store.option_name_by_id(a.get("OptionId", ""))):
                continue
            role = role_index.get(get_attr(a, "RoleId", "Role_Id", default=""))
            if role:
                matches.append(role)
        unique = _dedup_roles_preserve_order(matches)
        module_phrase = f" to {module}" if module else ""
        return _result("roles_with_permission", f"Roles With Full Access{module_phrase}",
                       unique, f"{len(unique)} role(s) have full access (create, edit, view, and approve){module_phrase}.",
                       count=len(unique))

    if query_type == "view_only":
        # View-only: HasView true AND every other flag false, for the
        # named module (module extraction may map to something not present
        # as a literal OptionName — e.g. "returns" has no single dedicated
        # menu option — in which case this returns zero matches rather
        # than guessing at the wrong module).
        matches = []
        for a in store.role_access():
            if a.get("HasView", "false").lower() != "true":
                continue
            if any(a.get(f, "false").lower() == "true" for f in ("HasNew", "HasEdit", "HasApprove")):
                continue
            if not _module_matches(module, store.option_name_by_id(a.get("OptionId", ""))):
                continue
            role = role_index.get(get_attr(a, "RoleId", "Role_Id", default=""))
            if role:
                matches.append(role)
        unique = _dedup_roles_preserve_order(matches)
        module_phrase = f" to {module}" if module else ""
        return _result("roles_with_permission", f"Roles With View-Only Access{module_phrase}",
                       unique, f"{len(unique)} role(s) have view-only access{module_phrase}.", count=len(unique))

    action_word = entities.get("action", "")
    attr = _resolve_action_attr(action_word, entities.get("raw_query", ""))
    if not attr:
        return _not_found("roles_with_permission", "Roles With Permission", _UNDERSTAND_FAILURE_MSG)
    matches = []
    for a in store.role_access():
        if not _flag_true(a, attr):
            continue
        if not _module_matches(module, store.option_name_by_id(a.get("OptionId", ""))):
            continue
        role = role_index.get(get_attr(a, "RoleId", "Role_Id", default=""))
        if role:
            matches.append(role)
    unique = _dedup_roles_preserve_order(matches)
    module_phrase = f" on {module}" if module else ""
    display_word = _display_action_word(action_word, attr)
    return _result("roles_with_permission", f"Roles That Can {display_word}{module_phrase}",
                   unique, f"{len(unique)} role(s) can {display_word}{module_phrase}.", count=len(unique))


def handle_role_module_access(scope: dict, entities: dict, store: XMLStore) -> dict:
    module = entities.get("module", "")
    target_role = entities.get("target_role", "")
    query_type = entities.get("query_type")
    if target_role:
        role = store.resolve_role(target_role)
        if not role:
            return _role_not_found("role_module_access", "Role Module Access", target_role)
        role_id = get_attr(role, "RoleId", "Role_Id", default="")
        accesses = [store.enrich_role_access(a) for a in store.role_access()
                    if get_attr(a, "RoleId", "Role_Id") == role_id]
        if query_type == "full_control":
            accesses = [a for a in accesses if all(a.get(f, "false").lower() == "true" for f in _ALL_FLAGS)]
            return _result("role_module_access", f"Full-Control Modules: {role.get('Name')}",
                           accesses, f"Role '{role.get('Name')}' has full control (create, edit, view, "
                           f"and approve) over {len(accesses)} module(s).",
                           role_name=role.get("Name"), count=len(accesses))
        if module:
            # A specific module was also named ("Can role Tester view the
            # audit log?", "Does role Tester have access to SDMX?") — this
            # branch previously ignored `module` entirely once target_role
            # was set, always dumping every one of the role's accesses
            # regardless of which single module was actually asked about.
            matching = [a for a in accesses if _module_matches(module, a.get("OptionName", ""))]
            has_any = any(
                a.get(f, "false").lower() == "true" for a in matching for f in _ALL_FLAGS
            )
            verb = "does" if has_any else "does not"
            return _result("role_module_access", f"{role.get('Name')} <-> {module}",
                           matching, f"Role '{role.get('Name')}' {verb} have access to '{module}'.",
                           role_name=role.get("Name"), has_access=has_any, count=len(matching))
        return _result("role_module_access", f"Modules Accessible to {role.get('Name')}",
                       accesses, f"Role '{role.get('Name')}' has access to {len(accesses)} module(s).",
                       role_name=role.get("Name"), count=len(accesses))
    if module:
        role_index = build_index(store.roles(), "RoleId")
        matches = []
        for a in store.role_access():
            if not _module_matches(module, store.option_name_by_id(a.get("OptionId", ""))):
                continue
            role = role_index.get(get_attr(a, "RoleId", "Role_Id", default=""))
            if role:
                matches.append(role)
        return _result("role_module_access", f"Roles With Access to {module}",
                       matches, f"{len(matches)} role(s) have access to '{module}'.", count=len(matches))
    return _not_found("role_module_access", "Role Module Access", _UNDERSTAND_FAILURE_MSG)


def handle_role_permission_diff(scope: dict, entities: dict, store: XMLStore) -> dict:
    role_a_name = entities.get("target_role", "")
    role_b_name = entities.get("role_b", "")
    role_a = store.resolve_role(role_a_name) if role_a_name else None
    role_b = store.resolve_role(role_b_name) if role_b_name else None
    if not role_a or not role_b:
        missing = role_a_name if not role_a else role_b_name
        return _role_not_found("role_permission_diff", "Role Permission Diff", missing)

    a_id = get_attr(role_a, "RoleId", "Role_Id", default="")
    b_id = get_attr(role_b, "RoleId", "Role_Id", default="")
    a_access = build_index(
        [store.enrich_role_access(x) for x in store.role_access() if get_attr(x, "RoleId", "Role_Id") == a_id],
        "OptionId",
    )
    b_access = build_index(
        [store.enrich_role_access(x) for x in store.role_access() if get_attr(x, "RoleId", "Role_Id") == b_id],
        "OptionId",
    )
    all_options = set(a_access) | set(b_access)
    rows = []
    for opt_id in all_options:
        a_row, b_row = a_access.get(opt_id), b_access.get(opt_id)
        name = (a_row or b_row or {}).get("OptionName", opt_id)
        rows.append({
            "Module": name,
            f"{role_a.get('Name')}_HasNew": (a_row or {}).get("HasNew", "false"),
            f"{role_b.get('Name')}_HasNew": (b_row or {}).get("HasNew", "false"),
            f"{role_a.get('Name')}_HasEdit": (a_row or {}).get("HasEdit", "false"),
            f"{role_b.get('Name')}_HasEdit": (b_row or {}).get("HasEdit", "false"),
            f"{role_a.get('Name')}_HasView": (a_row or {}).get("HasView", "false"),
            f"{role_b.get('Name')}_HasView": (b_row or {}).get("HasView", "false"),
            f"{role_a.get('Name')}_HasApprove": (a_row or {}).get("HasApprove", "false"),
            f"{role_b.get('Name')}_HasApprove": (b_row or {}).get("HasApprove", "false"),
        })
    return _result("role_permission_diff", f"{role_a.get('Name')} vs {role_b.get('Name')}",
                   rows, f"Compared {len(rows)} module(s) between '{role_a.get('Name')}' and '{role_b.get('Name')}'.",
                   role_a=role_a.get("Name"), role_b=role_b.get("Name"))


def handle_user_level_list(scope: dict, entities: dict, store: XMLStore) -> dict:
    level = entities.get("level", "")
    levels = list(store.user_levels())
    if not levels:
        return _not_found("user_level_list", "User Levels",
                          "No user levels (L1/L2/L3) are configured in this system.")
    if level:
        levels = [lv for lv in levels if lv.get("Name", "").upper() == level.upper()]
    return _result("user_level_list", "User Levels", levels,
                   f"There are {len(levels)} user level(s) defined in the system.", count=len(levels))


def handle_user_level_self(scope: dict, entities: dict, store: XMLStore) -> dict:
    u = store.user_by_id(scope.get("user_id") or scope["login_id"]) or store.user_by_name(scope["login_id"])
    if not u:
        return _not_found("user_level_self", "My User Level", "Your profile could not be found.")
    level_name, level_id = store.user_level_for_user(u)
    if not level_name:
        return _not_found("user_level_self", "My User Level",
                          "No user level (L1/L2/L3) is assigned to your account in this department.")
    return _result("user_level_self", "My User Level",
                   [{"LevelName": level_name, "LevelId": level_id}],
                   f"Your user level is: {level_name}.")
