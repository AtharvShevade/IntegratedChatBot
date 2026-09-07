"""Score translation quality on already-captured results (metric 1).

Judging is deliberately decoupled from the run. The runner persists
``english_payload``, ``localized_payload`` and the per-turn inputs, so quality
can be scored -- or re-scored with a different judge, or re-scored after
calibrating against native review -- without paying for the translation model
again. Inline judging would double the cost of every run for a number that is
advisory rather than a gate.

    python -m eval.multilingual.score_judge --model gemma4:31b --lang fr

Writes results/<model>_<lang>.judge.jsonl, which report.py merges in.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.multilingual import config
from eval.multilingual.judge import Judge


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-." else "-" for c in text)


def score_file(source: Path, judge: Judge, resume: bool = True) -> Path:
    target = source.with_suffix(".judge.jsonl")
    done: set[str] = set()
    if resume and target.exists():
        # A record that carries no numeric score is a FAILED judge call, not a
        # completed one. Treating it as done would permanently freeze an
        # outage into the results -- which is exactly what happened when the
        # judge was pointed at the wrong endpoint and every call 404'd.
        # Re-judging one is cheap; a silently unscored suite is not.
        kept: list[str] = []
        with open(target, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                record = json.loads(line)
                scored = any(
                    isinstance(v, (int, float))
                    and k.endswith(("adequacy", "fluency", "terminology"))
                    for k, v in record.items()
                )
                if scored:
                    done.add(record["id"])
                    kept.append(line.rstrip("\n"))
        # Drop the failed rows so they are not double-written on retry.
        with open(target, "w", encoding="utf-8") as fh:
            for line in kept:
                fh.write(line + "\n")
    elif target.exists():
        target.unlink()

    records = []
    with open(source, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if not record.get("_meta"):
                records.append(record)

    for i, record in enumerate(records, 1):
        if record["id"] in done:
            continue
        lang = record.get("lang", "en")
        scores: dict = {"id": record["id"], "lang": lang}

        turns = record.get("turns") or []
        first = turns[0] if turns else {}
        if first.get("localized_input") and first.get("english_input"):
            inbound = judge.score(first["localized_input"], first["english_input"], lang, "en")
            for key, value in inbound.items():
                scores[f"inbound_{key}"] = value

        english = "\n".join((record.get("english_payload") or {}).values())
        localized = "\n".join((record.get("localized_payload") or {}).values())
        if english and localized:
            outbound = judge.score(english, localized, "en", lang)
            for key, value in outbound.items():
                scores[f"outbound_{key}"] = value

        with open(target, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(scores, ensure_ascii=False) + "\n")
        print(f"  [{i}/{len(records)}] {record['id']:6s} "
              f"in_adq={scores.get('inbound_adequacy')} "
              f"out_adq={scores.get('outbound_adequacy')} "
              f"out_flu={scores.get('outbound_fluency')}")
    return target


def load_judge_scores(source: Path) -> dict[str, dict]:
    """Judge scores keyed by case id, for report.py to merge."""
    target = source.with_suffix(".judge.jsonl")
    if not target.exists():
        return {}
    out: dict[str, dict] = {}
    with open(target, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                record = json.loads(line)
                out[record["id"]] = {
                    k: v for k, v in record.items()
                    if k not in ("id", "lang") and isinstance(v, (int, float))
                }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=config.translate_model())
    parser.add_argument("--lang", required=True)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--screen", action="store_true",
                        help="score the screening-suite results instead of the full run")
    args = parser.parse_args(argv)

    tag = "_screen" if args.screen else ""
    source = config.RESULTS_DIR / f"{_slug(args.model)}_{args.lang}{tag}.jsonl"
    if not source.exists():
        raise SystemExit(f"no results at {source}")
    judge = Judge(model=args.judge_model)
    print(f"judging {source.name} with {judge.model}")
    target = score_file(source, judge)
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
