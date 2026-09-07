"""Domain vocabulary hint for Whisper's ``initial_prompt``.

Whisper conditions on this text as if it were the transcript of the preceding
audio, which biases it toward the spelling of terms it would otherwise mangle:
CIMS_ROR, ReturnId, XBRL, R009.

It is also the single most dangerous knob in the decoder. The same conditioning
that fixes "seems ror" -> "CIMS_ROR" can make the model EMIT prompt terms that
were never spoken, and the service already hallucinates on non-speech (measured:
silence -> "You", a tone -> "Thank you."). A prompt makes that worse, not better.

So this ships DISABLED. It is enabled only by STT_VOCABULARY_ENABLED=true, and
only after the Phase 6 benchmark shows both of:

    * entity preservation rate improves, AND
    * hallucination rate on the silence/noise clips does not increase.

Kept short and static on purpose. A long prompt eats decoder context, and a
prompt built from all ~200 return names would bias the model toward whichever
names happen to be listed first.
"""
from __future__ import annotations

import os

# One line, under the ~200-character guidance. Terms chosen because they are
# the ones the pipeline actually matches on and the ones a general-purpose
# model has no reason to spell correctly.
_DEFAULT_PROMPT = (
    "CIMS_ROR, CIMS_RAQ, ReturnId, XBRL, R009, R149, "
    "formula error, dimension error, reporting date, instance."
)

_MAX_CHARS = 240


def is_enabled() -> bool:
    """Default FALSE. See the module docstring -- this is an unmeasured
    accuracy/hallucination trade, not a free win."""
    return os.getenv("STT_VOCABULARY_ENABLED", "false").strip().lower() in (
        "1", "true", "yes", "on",
    )


def initial_prompt() -> str | None:
    """The hint to send, or None when disabled.

    STT_VOCABULARY overrides the default text, so a deployment can tune the
    term list without a code change -- the same config-seam convention the
    translation model uses.
    """
    if not is_enabled():
        return None
    prompt = os.getenv("STT_VOCABULARY", _DEFAULT_PROMPT).strip()
    if not prompt:
        return None
    return prompt[:_MAX_CHARS]
