"""Parse the 'iDeal Validation Output' error html (plain and backtracking shapes) into rules, failing
instances and their facts. Pure parsing: no metadata, no workbook, no guessing.

A RULE has a name (assertion label), a formula expression and a number of failing INSTANCES; each instance is
one table of FACTS: variable (V1, V2 ...), concept, value, context, unit, decimal.

Backtracking tables (extra columns: DB TableName / Excel SheetName, Table Header, Cell Code ...) are read
too, but nothing here depends on them: they are returned as optional extras on each fact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_PANEL_SPLIT = re.compile(r'<div class="panel panel-default" id="(?:errorPanel|formulaErrorPanel)(\d+)">')
_LABEL = re.compile(r'class="assertionLabel">(.*?)</div>', re.S)
_EXPR = re.compile(r'class="formulaErrorTest"[^>]*>(.*?)</div>', re.S)
_BADGE = re.compile(r'class="badge badge-danger">\s*(\d+)\+?\s*</div>', re.S)
_TABLE = re.compile(r"<table.*?</table>", re.S)
_TITLE = re.compile(r'class="formulaErrorTitle"[^>]*>(.*?)</td>', re.S)
_TH = re.compile(r'<t[hd] class="headerCell">(.*?)</t[hd]>', re.S)
_TD = re.compile(r'<td class="(?:long)?[mM]sgBodyCell">(.*?)</td>', re.S)
_ROW = re.compile(r'<tr class="hide fv">(.*?)</tr>', re.S)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<.*?>|&nbsp;", " ", html)).strip()


@dataclass
class Fact:
    var: str
    concept: str
    value: str
    context: str
    unit: str = ""
    decimal: str = ""
    extra: dict = field(default_factory=dict)       # backtracking columns, if the file has them


@dataclass
class Instance:
    title: str
    facts: list[Fact]


@dataclass
class Rule:
    name: str
    expression: str
    declared_count: int
    instances: list[Instance]


def parse_rules(html: str) -> list[Rule]:
    """Every formula rule in the FORMULA_ERROR tab that has failing instances."""
    start = html.find('id="accordionFormula"')
    end = html.find("<div class=\"tab-pane fade\" id=\"2\"", start) if start >= 0 else -1
    body = html[start:end if end > 0 else len(html)] if start >= 0 else html
    parts = _PANEL_SPLIT.split(body)
    rules: list[Rule] = []
    for i in range(1, len(parts), 2):
        chunk = parts[i + 1]
        label = _LABEL.search(chunk)
        expr = _EXPR.search(chunk)
        if not label or not expr:
            continue
        badge = _BADGE.search(chunk)
        instances: list[Instance] = []
        for table in _TABLE.findall(chunk):
            headers = [_text(h) for h in _TH.findall(table)]
            if not headers:
                continue
            idx = {h: n for n, h in enumerate(headers)}
            title = _TITLE.search(table)
            facts: list[Fact] = []
            for row in _ROW.findall(table):
                cells = [_text(c) for c in _TD.findall(row)]
                if len(cells) != len(headers):
                    continue

                def col(*names: str) -> str:
                    for n in names:
                        if n in idx:
                            return cells[idx[n]]
                    return ""
                extra = {h: cells[n] for h, n in idx.items()
                         if h in ("DB TableName", "Excel SheetName", "Table Header", "Cell Code", "Row Label(s)", "Column Label(s)", "Entered Data(s)")}
                facts.append(Fact(
                    var=col("Variable", "Variable Id"), concept=col("Name"),
                    value=col("Value", "Instance Data(s)"), context=col("Context"),
                    unit=col("Unit"), decimal=col("Decimal"), extra=extra,
                ))
            if facts:
                instances.append(Instance(_text(title.group(1)) if title else "", facts))
        rules.append(Rule(_text(label.group(1)), _text(expr.group(1)),
                          int(badge.group(1)) if badge else len(instances), instances))
    return rules


def other_tab_counts(html: str) -> dict[str, int]:
    """Counts shown on the other tabs' badges (quality-check / specification), for the report footer."""
    out = {}
    for label, n in re.findall(r'class="assertionLabel">\s*([A-Za-z_\- ]+?)\s*</div>\s*<div[^>]*class="badge badge-\w+">\s*(\d+)', html, re.S):
        out[label.strip()] = int(n)
    return out


_SPEC = re.compile(r"(\w+:\w+)\s*\|\s*(.*?)\s*(?:Warning|Error)(?:&nbsp;|\s)*Code:\s*(\w+)\s+FileName:\s*(\S+)\s+LineNo:\s*(\d+)", re.S)


def spec_warnings(html: str) -> list[tuple[str, str, str, int]]:
    """Specification-tab entries as (error name, message, code, count). They describe the TABLE definition
    (taxonomy), not the filer's workbook, so no cell is involved."""
    start = html.find('id="3"')
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", html[start:])) if start >= 0 else ""
    seen: dict[tuple[str, str, str], int] = {}
    for name, msg, code, _file, _line in _SPEC.findall(text):
        key = (name, re.sub(r"@\w+ = \w+", "", msg).strip(" ,."), code)
        seen[key] = seen.get(key, 0) + 1
    return [(n, m, c, k) for (n, m, c), k in sorted(seen.items(), key=lambda x: -x[1])]
