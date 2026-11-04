"""One entry point: give it ANY error file of a return and it finds the rest and explains the errors.

    python explain.py <error file> --repo <repo folder> [--workbook W] [--llm] [--out report.md]

Lookup (nothing is configured per return):
  form id        from the path (.../Instance/<form>/file) or, failing that, XML_InstanceLog.xml (ErrorDocPath -> FormId)
  metadata       <repo>/<form>   or   <repo>/DataBase/<form>
  workbook       --workbook, else the user's upload made just before the error file (<form>/UploadedFiles/<time>/),
                 else the blank template (cell addresses then rest on the mapping alone and are marked as such)
  error format   validator html (rules + facts)  |  spreadsheet XML (sheet + column given)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
from . import cell_locator as cl            # noqa: E402
from . import cell_state as cs              # noqa: E402
from . import direct_errors as de           # noqa: E402
from . import error_html as eh              # noqa: E402
from . import explain_table as et           # noqa: E402
from . import explain_workbook as ew        # noqa: E402
from . import fact_address as fa            # noqa: E402
from . import formula_defs as fdefs         # noqa: E402
from . import other_errors as oe            # noqa: E402
from . import match_upload as mu            # noqa: E402
from . import reported_facts as rf          # noqa: E402
from . import table_titles as tt            # noqa: E402
from . import rule_cards as rc              # noqa: E402
from .template_converter import readable_template   # noqa: E402
from .workbook import EmptyWorkbook, Workbook, pick_template, pick_template_path   # noqa: E402


def form_of(error_file: str, repo: str | None) -> str | None:
    parts = os.path.normpath(error_file).split(os.sep)
    if "Instance" in parts:
        i = parts.index("Instance")
        if i + 1 < len(parts) - 1 and parts[i + 1].isdigit():
            return parts[i + 1]
    name = os.path.basename(error_file)
    for fn in ("XML_InstanceLog.xml", "InstanceLog.xml"):                  # 5.5 / 6.0
        log = os.path.join(repo, fn) if repo else ""
        if log and os.path.isfile(log):
            for row in ET.parse(log).getroot().iter("Row"):
                if os.path.basename(row.get("ErrorDocPath", "")) == name:
                    return row.get("FormId")
    return None


def metadata_folder(repo: str | None, form: str | None) -> str | None:
    if not repo or not form:
        return None
    for p in (os.path.join(repo, form), os.path.join(repo, "DataBase", form)):
        if os.path.isdir(p):
            return p
    return None


def _located(analysed):
    return [lc for it in analysed for _i, lo, _e in it[4] for v in lo.values() for lc in v if lc.addr]


def _evidence(analysed) -> tuple[int, int]:
    """(locations confirmed by the filed value, facts whose mapped cell the workbook contradicts). Zero-valued facts are left out:
    an empty cell "matches" a zero, so a zero proves nothing about which upload the error file came from."""
    ok = bad = 0
    for it in analysed:
        for _i, lo, _e in it[4]:
            for lcs in lo.values():
                for lc in lcs:
                    t = fa._dec(lc.fact.value)
                    if not lc.fact.concept or t is None or t == 0:
                        continue
                    if lc.addr and lc.res.status == "CONFIRMED":
                        ok += 1
                    elif not lc.addr and lc.res.status == "UNCONFIRMED":
                        bad += 1
    return ok, bad


def _upload_stamp(path: str, folder: str) -> str:
    """'21 Nov 2025 15:15' from the upload's folder name (dd-mm-yy-HH-MM-SS)."""
    name = os.path.relpath(path, folder).split(os.sep)[1]
    try:
        return time.strftime("%d %b %Y %H:%M", time.strptime(name, "%d-%m-%y-%H-%M-%S"))
    except ValueError:
        return name


def _reasons(analysed) -> dict:
    out: dict = {}
    for it in analysed:
        for _i, lo, _e in it[4]:
            for v in lo.values():
                for lc in v:
                    if not lc.addr and lc.reason:
                        out[lc.reason] = out.get(lc.reason, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def explain_file(error_file: str, repo: str | None = None, workbook: str | None = None, use_llm: bool = False,
                 model: str = "qwen2.5:7b", numbering: dict | None = None):
    """-> dict(rows, analysed, info). info carries what the explanation rests on, for the report header."""
    t0 = time.time()
    form = form_of(error_file, repo)
    folder = metadata_folder(repo, form) if form else None
    info = {"error_file": os.path.basename(error_file), "form": form, "folder": folder, "basis": "", "format": "", "notes": []}
    if folder is None:
        info["notes"].append("no metadata folder for this return: cells are found from the workbook alone")
    meta = cl.load_form_folder(folder, form) if folder else cl.FormMeta(form or "", "")
    if folder:
        meta.reported = rf.load(error_file)
        meta.formula_defs = fdefs.load(os.path.join(folder, "Taxonomy"))
        meta.table_titles = tt.load(os.path.join(folder, "Taxonomy"))
        meta.layout_ranges = tt.layout_ranges(meta)
        info["sources"] = {"instance": meta.reported is not None, "rule_definitions": len(meta.formula_defs)}

    wb, basis = None, "none"
    if workbook:
        wb, basis = Workbook(workbook), "workbook given"
    elif folder:
        up = mu.match_upload(folder, error_file)
        if up:
            wb, basis = Workbook(up), f"user upload {os.path.relpath(up, folder).split(os.sep)[1]}"
        else:
            wb = pick_template(meta, folder)
            basis = "template only (no user workbook found)" if wb else "none"
    if wb is None:
        wb, basis = EmptyWorkbook(), "error file only (no workbook, no template)"
    elif folder is None:
        basis = "workbook and error file only (no return metadata)"
    info["basis"] = basis
    try:
        wb.table_titles = getattr(meta, "table_titles", {})      # the cards name each cell's table from the taxonomy when it says
        wb.layout_ranges = getattr(meta, "layout_ranges", [])
    except AttributeError:                                       # an object that takes no attributes just has none
        pass
    if getattr(wb, "path", "") and not getattr(wb, "is_template", False):
        from .formula_graph import FormulaGraph
        own = wb.path
        # formulas: the return's template when there is one, otherwise the user's own file (converted if it is binary)
        wb.formulas = FormulaGraph(resolve=lambda: (readable_template(pick_template_path(meta, folder)) if folder else None)
                                   or readable_template(own))
        wb.upload_formulas = cs.upload_graph(own)               # the filer's own formulas (None for a legacy .xls)

    kind = oe.detect(error_file)
    if kind:
        info["format"] = {"duplicate": "duplicate-element errors", "dynamic_domain": "drop-down (dynamic domain) errors",
                          "service_failure": "validator service failure", "crilc_report": "month-on-month comparison report"}[kind]
        rows, located = oe.explain(kind, error_file, wb, et.Row, meta, fa)
        info["facts"] = sum(len(r.facts.get("values", [])) or r.facts.get("borrowers", 1) for r in rows)
        info["located"] = located
        if kind in ("service_failure", "crilc_report"):
            info["notes"] = [n for n in info["notes"] if "metadata folder" not in n]
        analysed = []
    elif de.is_direct_error_file(error_file):
        info["format"] = "spreadsheet error file (sheet and column given)"
        errors = de.parse(error_file)
        rows, located = de.explain(errors, wb, et.Row)
        info["facts"], info["located"] = len(errors), located
        info["notes"].append(f"{len(errors)} errors grouped into {len(rows)} rows")
        analysed = []
    else:
        info["format"] = "validator report (rules and facts)"
        html = open(error_file, encoding="utf-8", errors="ignore").read()
        rules = eh.parse_rules(html)
        analysed = ew.analyse(meta, wb, rules)
        reasons = _reasons(analysed)
        # A value the workbook does not hold, or a mapped cell that holds another number, points at the wrong upload: the user may have
        # uploaded several times before the validator ran. Try the other uploads made before the error file and keep the one whose
        # values agree with the error file best. A tie keeps the nearest upload (the previous behaviour).
        weak = sum(n for k, n in reasons.items() if k.startswith(("reported value is not in the uploaded", "the mapped cell")))
        if weak and weak >= 0.1 * max(1, sum(reasons.values())) and not basis.startswith(("template", "workbook given")):
            cur_ok, cur_bad = _evidence(analysed)
            best = (cur_ok - cur_bad, wb, analysed, basis, (cur_ok, cur_bad), None)
            tried = [{"upload": os.path.relpath(wb.path, folder).split(os.sep)[1], "confirmed": cur_ok, "contradicted": cur_bad}]
            for alt in [u for u in mu.ranked_uploads(folder, error_file, window_min=24 * 60, limit=6) if u != wb.path]:
                wb2 = Workbook(alt)
                wb2.formulas = getattr(wb, "formulas", None)
                wb2.upload_formulas = cs.upload_graph(alt)
                an2 = ew.analyse(meta, wb2, rules)
                ok2, bad2 = _evidence(an2)
                tried.append({"upload": os.path.relpath(alt, folder).split(os.sep)[1], "confirmed": ok2, "contradicted": bad2})
                if ok2 - bad2 > best[0]:
                    best = (ok2 - bad2, wb2, an2, f"user upload {os.path.relpath(alt, folder).split(os.sep)[1]} (best of the uploads before the error file)",
                            (ok2, bad2), alt)
            _n, wb, analysed, basis, (b_ok, b_bad), switched = best
            info["basis"] = basis
            info["upload_check"] = {"tried": tried, "switched": bool(switched)}
            if switched:
                msg = (f"Cell locations use the upload made {_upload_stamp(switched, folder)}: its values agree with this error file "
                       f"({b_ok} confirmed, {b_bad} contradicted); the upload made just before the error file did not "
                       f"({cur_ok} confirmed, {cur_bad} contradicted).")
                info["notes"].append(msg)
                info["upload_note"] = msg
            reasons = _reasons(analysed)
        info["reasons"] = reasons
        data = et.data_rows(analysed, wb)
        taken = {tuple(c.split(" -> ")) for r in data for c in r.facts.get("culprit_cells", [])}
        rows = data + et.cover_rows(analysed) + et.other_rows(analysed) + et.rule_rows(wb, analysed, taken) + \
            et.spec_row(eh.spec_warnings(html))
        facts = [lc for it in analysed for _i, lo, _e in it[4] for v in lo.values() for lc in v]
        info["facts"] = len(facts)
        info["located"] = sum(1 for lc in facts if lc.addr)
        info["confirmed"] = sum(1 for lc in facts if lc.res.status == "CONFIRMED")
        if basis.startswith("template"):
            info["notes"].append("no filled workbook: cells come from the mapping only and are not value-checked")
    rows.sort(key=lambda r: {"DATA": 0, "RULE": 1, "SPEC": 2}[r.kind])
    if use_llm:
        from . import explain_llm as el
        for r in rows:
            out = el.ask(model, {**r.facts, "task": "Explain this row in 2 sentences for the filer: put it in 'problem'; "
                                                   "'why' = why it fails; 'action' = what to do."})
            if out and all(out.values()) and el.guard(" ".join(out.values()), {**r.facts, "s": r.solution, "e": r.error}):
                r.explanation = f"{out['problem']} {out['why']} {out['action']}"
    info["seconds"] = round(time.time() - t0, 1)
    cards = {}
    if analysed:
        try:
            cards = rc.build_cards(analysed, wb, rows, numbering)           # one card per failing rule (the user-facing format)
            if info.get("upload_note"):                                    # tell the user which upload the error file really came from
                for c in cards.values():
                    c["view"].setdefault("warnings", []).append(info["upload_note"])
        except Exception as exc:                                  # noqa: BLE001 - cards are an extra view; never lose the table
            info["notes"].append(f"rule cards could not be built: {type(exc).__name__}: {exc}")
    return {"rows": rows, "analysed": analysed, "info": info, "wb": wb, "cards": cards}


def render(result: dict) -> str:
    i, rows = result["info"], result["rows"]
    head = [f"# Error explanation - {i['error_file']}",
            f"Return {i['form']} | {i['format']} | basis: {i['basis']} | "
            f"cells found for {i.get('located', 0)} of {i.get('facts', 0)} items | {i['seconds']} s"]
    head += [f"Note: {n}" for n in i["notes"]]
    if i.get("reasons"):
        head.append("Items without a cell, and why:")
        head += [f"- {n} x {why}" for why, n in i["reasons"].items()]
    body = et.render(rows, result["analysed"], i["form"], i["error_file"]).split("\n", 2)[2]
    return "\n".join(head) + "\n" + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("error_file")
    ap.add_argument("--repo", default=None, help="repo folder; optional: without it the error file and workbook alone are used")
    ap.add_argument("--workbook")
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--out")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    text = render(explain_file(a.error_file, a.repo, a.workbook, a.llm, a.model))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
