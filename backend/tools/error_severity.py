"""Severity of a validation item, and the counts that follow from it.

The validator marks each formula rule with a coloured badge: red (`badge-danger`) is an error that must be corrected, yellow or
orange (`badge-warning`, `badge-orange`) is a warning. Only errors are counted as errors; warnings stay visible and are counted
separately. The severity is read from the badge's own class, never from a number inside it (the number is how many times the
rule failed, not how many errors there are), and anything that is not clearly red is never counted as an error.

    severity_from_class(css_class) -> "error" | "warning" | "unknown"
    count_errors(rules)            -> number of rules whose severity is "error"
    count_warnings(rules)          -> number of rules whose severity is "warning"
    errors_first(rules)            -> a new list, errors first, original order kept inside each group

A rule dict that carries no "severity" key at all comes from a parser that did not look at the badge; it keeps counting as an
error, exactly as before. An explicit "unknown" (a badge class that is neither red nor yellow/orange) is not counted.
"""
from __future__ import annotations

import html
import re

ERROR, WARNING, UNKNOWN = "error", "warning", "unknown"

_ERROR_TOKENS = {"badge-danger", "danger", "badge-error", "error", "badge-red", "red", "text-danger", "label-danger"}
_WARNING_TOKENS = {"badge-warning", "warning", "badge-orange", "orange", "badge-yellow", "yellow", "label-warning", "text-warning"}


def severity_from_class(css_class: str | None) -> str:
    """'badge badge-danger' -> 'error'; 'badge badge-warning' -> 'warning'; anything else -> 'unknown'.
    A class that names both a red and a yellow/orange token is a warning: never inflate the error count on a doubt."""
    tokens = {t.lower() for t in (css_class or "").split()}
    if tokens & _WARNING_TOKENS:
        return WARNING
    if tokens & _ERROR_TOKENS:
        return ERROR
    return UNKNOWN


def severity_of(rule: dict) -> str | None:
    """The rule's severity, or None when the parser that produced it never classified it."""
    s = rule.get("severity") if isinstance(rule, dict) else None
    return s if s in (ERROR, WARNING, UNKNOWN) else None


def is_error(rule: dict) -> bool:
    s = severity_of(rule)
    return s is None or s == ERROR


def count_errors(rules) -> int:
    return sum(1 for r in rules or [] if is_error(r))


def count_warnings(rules) -> int:
    return sum(1 for r in rules or [] if severity_of(r) == WARNING)


def errors_first(rules) -> list:
    rules = list(rules or [])
    return [r for r in rules if is_error(r)] + [r for r in rules if not is_error(r)]


# ── reading the severity of each rule panel straight from the error file (for parsers that do not read the badge) ──────
_PANEL_SPLIT = re.compile(r'(?=<div[^>]+id=["\']errorPanel\d+["\'])', re.I)
_NAME = re.compile(r'class=["\'][^"\']*\bassertionLabel\b[^"\']*["\'][^>]*>(.*?)</div>', re.S | re.I)
_BADGE_CLASS = re.compile(r'<(?:div|span)[^>]*class=["\']([^"\']*\bbadge\b[^"\']*)["\']', re.I)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def panel_severities(raw_html: str) -> list[tuple[str, str]]:
    """[(rule name, severity)] for every rule panel of the error file, in file order."""
    out = []
    for chunk in _PANEL_SPLIT.split(raw_html or ""):
        if not re.match(r'<div[^>]+id=["\']errorPanel\d+["\']', chunk, re.I):
            continue
        name = _NAME.search(chunk)
        badge = _BADGE_CLASS.search(chunk)
        out.append((_text(name.group(1)) if name else "", severity_from_class(badge.group(1)) if badge else UNKNOWN))
    return out


def annotate(rules: list[dict], raw_html: str) -> list[dict]:
    """Copies of `rules` with a "severity" taken from the matching panel of the file (matched by name, in order).
    Rules that already carry a severity are left as they are; a rule with no matching panel stays unclassified."""
    panels = panel_severities(raw_html)
    used = [False] * len(panels)
    out = []
    for rule in rules or []:
        if severity_of(rule) is not None:
            out.append(rule)
            continue
        name = _text(rule.get("rule_name", ""))
        sev = None
        for i, (pname, psev) in enumerate(panels):
            if not used[i] and pname == name:
                used[i], sev = True, psev
                break
        out.append({**rule, "severity": sev} if sev else rule)
    return out
