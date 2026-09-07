"""Supervisor that restarts a run until every case is recorded.

Necessary because the SQL-agent path can take the whole interpreter down
natively on this machine -- no traceback, no Python exception, and an exit code
of 0 that looks like a clean finish. That silently truncated a 60-case baseline
run at case 42. ``pipeline.run_turn`` now catches the SystemExit family, but a
hard native abort cannot be caught in-process at all, so the only reliable
answer is an out-of-process retry.

Every runner mode appends results line by line and supports ``--resume``, so a
restart re-enters exactly where it stopped and no completed case is repeated.

    python -m eval.multilingual.supervise --baseline --runs 3
    python -m eval.multilingual.supervise --lang fr
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from eval.multilingual import config
from eval.multilingual.dataset import build_dataset

MAX_ATTEMPTS = 12


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-." else "-" for c in text)


def _recorded_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("id"):
                ids.add(record["id"])
    return ids


def _expected_ids(lang: str, limit: int | None, subset: bool = False,
                  screen: bool = False) -> set[str]:
    cases = build_dataset.load(lang, subset=subset, screen=screen)
    if limit:
        cases = cases[:limit]
    return {c["id"] for c in cases}


def supervise(runner_args: list[str], target: Path, lang: str,
              limit: int | None, subset: bool = False, screen: bool = False) -> int:
    expected = _expected_ids(lang, limit, subset, screen)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        done = _recorded_ids(target)
        missing = expected - done
        if not missing:
            print(f"[supervise] complete: {len(done)}/{len(expected)} cases in {target.name}")
            return 0
        print(f"[supervise] attempt {attempt}/{MAX_ATTEMPTS}: "
              f"{len(done)}/{len(expected)} done, {len(missing)} remaining")
        # ALWAYS resume. --resume only skips ids already recorded, so it is
        # safe on a fresh file -- whereas omitting it makes run_eval unlink and
        # restart the target. That matters for --baseline, where `--runs N`
        # re-runs runs 1..N: launching run 2 without --resume wiped the
        # already-complete run 1. To force a clean run, delete the file.
        args = list(runner_args) + ["--resume"]
        proc = subprocess.run(
            [sys.executable, "-u", "-m", "eval.multilingual.run_eval", *args],
            cwd=str(config.PROJECT_ROOT),
        )
        after = _recorded_ids(target)
        if after == done and proc.returncode == 0 and not (expected - after):
            break
        if after == done:
            # No forward progress: the same case is killing the process every
            # time. Report it rather than looping forever.
            stuck = sorted(expected - after)[:5]
            print(f"[supervise] no progress on attempt {attempt}; "
                  f"next unrecorded case(s): {stuck}")
            if attempt >= 3:
                print("[supervise] giving up -- investigate the case above")
                return 1
    done = _recorded_ids(target)
    missing = sorted(expected - done)
    if missing:
        print(f"[supervise] incomplete: still missing {len(missing)}: {missing}")
        return 1
    print(f"[supervise] complete: {len(done)}/{len(expected)} cases")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--lang")
    parser.add_argument("--model")
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--subset", action="store_true",
                        help="run the frozen 24-case stratified subset")
    parser.add_argument("--screen", action="store_true",
                        help="run the 5-case screening suite")
    args = parser.parse_args(argv)

    model = args.model or config.translate_model()

    if args.baseline:
        rc = 0
        for run_index in range(1, args.runs + 1):
            target = config.RESULTS_DIR / f"baseline_en_run{run_index}.jsonl"
            runner = ["--baseline", "--runs", str(run_index)]
            if args.limit:
                runner += ["--limit", str(args.limit)]
            # --runs N re-runs 1..N; --resume makes the earlier ones no-ops.
            print(f"\n########## baseline run {run_index}/{args.runs} ##########")
            if args.subset:
                runner.append("--subset")
            rc |= supervise(runner, target, "en", args.limit, args.subset)
        return rc

    if not args.lang:
        parser.error("choose --baseline or --lang")

    tag = "_screen" if args.screen else ""
    target = config.RESULTS_DIR / f"{_slug(model)}_{args.lang}{tag}.jsonl"
    runner = ["--lang", args.lang, "--runs", str(args.runs)]
    if args.model:
        runner += ["--model", args.model]
    if args.judge:
        runner.append("--judge")
    if args.limit:
        runner += ["--limit", str(args.limit)]
    if args.subset:
        runner.append("--subset")
    if args.screen:
        runner.append("--screen")
    return supervise(runner, target, args.lang, args.limit, args.subset, args.screen)


if __name__ == "__main__":
    raise SystemExit(main())
