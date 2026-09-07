"""Dataset schema, loader and manifest generator.

One JSONL record per clip, in the same style as
eval/multilingual/dataset/queries_*.jsonl -- flat, one object per line, an ``id``
that never changes.

    {"id": "en_clean_01", "audio_file": "en/en_clean_01.wav", "language": "en",
     "speaker": "s1", "condition": "clean", "duration": 6.4,
     "reference_text": "what is the status of CIMS_ROR",
     "entities": ["CIMS_ROR"], "notes": ""}

THE GROUND TRUTH IS NOT GENERATED. ``generate_manifest()`` writes a TEMPLATE
with every planned clip's metadata and an EMPTY ``reference_text``; a human
records the audio and types what was actually said. A harness that invented
reference text would score models against a fiction, and every number it
produced would be worthless.

``load()`` enforces that: a record with no reference_text is returned but
marked ``scorable=False``, and run_eval refuses to score it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from eval.stt import config


@dataclass
class Clip:
    """One evaluation clip."""

    id: str
    audio_file: str          # relative to dataset/audio/
    language: str            # en | fr | ar | hi  (the language SPOKEN)
    condition: str           # see config.CONDITIONS
    speaker: str = ""        # opaque id, e.g. "s1"; lets us spot per-speaker bias
    duration: float | None = None       # seconds; filled by the recordist or probed
    reference_text: str = ""            # what was ACTUALLY said. Typed by a human.
    entities: list[str] = field(default_factory=list)  # must survive verbatim
    notes: str = ""

    @property
    def scorable(self) -> bool:
        """Accuracy can only be scored against a real transcript.

        Non-speech probes are the exception: silence has no transcript, and the
        thing being measured is precisely that the model says nothing.
        """
        if self.condition in config.NON_SPEECH_CONDITIONS:
            return True
        return bool(self.reference_text.strip())

    def audio_path(self) -> Path:
        return config.AUDIO_DIR / self.audio_file

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# The planned 64 clips -- metadata only, no transcripts
# ---------------------------------------------------------------------------
#
# 48 core (4 languages x 12) + 10 code-switch + 10 entity stress + 6 robustness.
# Deliberately small: a set this size can be recorded in an afternoon and
# scored by hand, which is what makes it likely to actually exist. Expand only
# once it has told us something.

_CORE_PER_LANGUAGE = (
    # (condition, count, note shown to whoever records it)
    ("clean",  4, "Short natural command, 5-15s, quiet room."),
    ("entity", 3, "Must contain a real identifier: CIMS_ROR, R009, CIMS_RAQ(Monthly)."),
    ("noisy",  2, "Office background: typing, chatter, or a fan."),
    ("quiet",  1, "Spoken softly, at arm's length from the mic."),
    ("fast",   1, "Spoken noticeably faster than normal."),
    ("pause",  1, "One deliberate 2-3s pause mid-sentence."),
)

_CODESWITCH = (
    ("hi", "devanagari_english", 4, "Devanagari with English nouns, e.g. 'मुझे अपने CIMS_ROR report का status जानना है'."),
    ("hi", "romanized_hinglish", 4, "Romanised Hinglish, e.g. 'Mujhe apne order ka status check karna hai'."),
    ("hi", "mixed_entity",       2, "Hinglish carrying an identifier and a date."),
)

_ENTITY_STRESS = (
    ("en", "CIMS_ROR"), ("en", "R009"), ("en", "R149"),
    ("en", "ReturnId"), ("en", "XBRL"),
    ("en", "a date, spoken naturally (e.g. thirty-first of March twenty twenty-six)"),
    ("en", "a large amount (e.g. three hundred fifty-six billion rupees)"),
    ("hi", "CIMS_ROR inside a Hindi sentence"),
    ("fr", "CIMS_RAQ(Monthly) inside a French sentence"),
    ("ar", "R149 inside an Arabic sentence"),
)

_ROBUSTNESS = (
    ("silence",      "en", "5s of room tone. Say NOTHING. Expected transcript: empty."),
    ("noise",        "en", "5s of background noise only, no speech. Expected transcript: empty."),
    ("mic_bump",     "en", "Normal sentence with a knock against the mic partway through."),
    ("quiet",        "en", "Barely audible speech, near the noise floor."),
    ("two_speakers", "en", "Two people talking, partly overlapping."),
    ("long",         "en", "35-45s of continuous speech, to cross Whisper's 30s window."),
)


def planned_clips() -> list[Clip]:
    """The 64-clip specification, as records with empty reference_text."""
    clips: list[Clip] = []

    for lang in ("en", "fr", "ar", "hi"):
        for condition, count, note in _CORE_PER_LANGUAGE:
            for n in range(1, count + 1):
                cid = f"{lang}_{condition}_{n:02d}"
                clips.append(Clip(
                    id=cid, audio_file=f"{lang}/{cid}.wav", language=lang,
                    condition=condition, speaker="s1" if n % 2 else "s2", notes=note,
                ))

    for lang, kind, count, note in _CODESWITCH:
        for n in range(1, count + 1):
            cid = f"cs_{kind}_{n:02d}"
            clips.append(Clip(
                id=cid, audio_file=f"codeswitch/{cid}.wav", language=lang,
                condition="codeswitch", speaker="s1" if n % 2 else "s2", notes=note,
            ))

    for n, (lang, term) in enumerate(_ENTITY_STRESS, start=1):
        cid = f"ent_{n:02d}"
        clips.append(Clip(
            id=cid, audio_file=f"entity/{cid}.wav", language=lang,
            condition="entity", speaker="s1",
            notes=f"Say a natural sentence containing: {term}",
        ))

    for n, (condition, lang, note) in enumerate(_ROBUSTNESS, start=1):
        cid = f"rob_{n:02d}_{condition}"
        clips.append(Clip(
            id=cid, audio_file=f"robustness/{cid}.wav", language=lang,
            condition=condition, speaker="s1", notes=note,
        ))

    return clips


def generate_manifest(path: Path | None = None, overwrite: bool = False) -> Path:
    """Write the TEMPLATE manifest. Refuses to clobber real work.

    Once a recordist has typed reference transcripts into this file, it is the
    dataset -- so overwriting it destroys the only irreplaceable artefact in
    the harness. --force is required to do that.
    """
    target = path or (config.DATASET_DIR / "manifest.jsonl")
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"{target} already exists. It may contain hand-typed transcripts; "
            f"pass overwrite=True (--force) only if you are certain."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        for clip in planned_clips():
            fh.write(json.dumps(clip.to_dict(), ensure_ascii=False) + "\n")
    return target


def load(path: Path | None = None) -> list[Clip]:
    """Read a manifest. Raises only on a malformed file, never on missing audio.

    Missing audio and missing transcripts are normal mid-collection states and
    are reported by ``status()`` rather than treated as errors.
    """
    target = path or (config.DATASET_DIR / "manifest.jsonl")
    if not target.exists():
        raise FileNotFoundError(
            f"No manifest at {target}. Create the template with:\n"
            f"    python -m eval.stt.run_eval --init-dataset"
        )
    clips: list[Clip] = []
    seen: set[str] = set()
    with open(target, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{target}:{n}: malformed JSON: {exc}") from exc
            if raw.get("_meta"):
                continue
            missing = {"id", "audio_file", "language", "condition"} - set(raw)
            if missing:
                raise ValueError(f"{target}:{n}: missing required field(s): {sorted(missing)}")
            if raw["id"] in seen:
                raise ValueError(f"{target}:{n}: duplicate id {raw['id']!r}")
            if raw["language"] not in config.LANGUAGES:
                raise ValueError(f"{target}:{n}: unknown language {raw['language']!r}")
            if raw["condition"] not in config.CONDITIONS + ("noise",):
                raise ValueError(f"{target}:{n}: unknown condition {raw['condition']!r}")
            seen.add(raw["id"])
            clips.append(Clip(**{k: v for k, v in raw.items() if k in Clip.__dataclass_fields__}))
    return clips


def status(clips: list[Clip]) -> dict:
    """How much of the dataset actually exists yet."""
    have_audio = [c for c in clips if c.audio_path().exists()]
    have_text = [c for c in clips if c.scorable]
    ready = [c for c in clips if c.audio_path().exists() and c.scorable]
    return {
        "clips": len(clips),
        "with_audio": len(have_audio),
        "with_reference": len(have_text),
        "ready_to_score": len(ready),
        "missing_audio": sorted(c.id for c in clips if not c.audio_path().exists()),
        "missing_reference": sorted(c.id for c in clips if not c.scorable),
    }
