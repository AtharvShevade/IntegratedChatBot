"""Split a response into translatable prose and non-translatable structure.

The problem this solves, measured on the 24-case subset:

    st03 sends 3,446 characters to the translation model. 3,336 of them are a
    numbered list of 162 regulatory report names -- data the model must copy
    verbatim and must never alter. Every payload >= 3,294 chars failed with a
    502 from the shared proxy (8 of 8, across all three languages), each
    burning ~246s before falling back to untranslated English.

The names never needed to leave the server. Every site that renders such a
list also passes the identical data structurally: `_build(..., response_text=
msg, options=opts)` at backend/agent/__init__.py:3327 is the canonical shape,
and all 14 rendering sites in that file follow it.

So the boundary masks the rendered block out of the prose, translates what is
left, and re-renders the list locally from `options`. For st03 that is 3,446 ->
~110 translatable characters, and report identifiers become impossible to
corrupt rather than merely instructed-not-to-be.

This module is deliberately free of harness imports so it can move into
backend/i18n/ unchanged if the production layer is ever built. It reads only
the (response_text, options) pair -- it does not touch routing, selection, or
any of the 14 rendering sites.
"""
from __future__ import annotations

import re

# Marker standing in for the option list while the prose is translated. Chosen
# to look like structure rather than prose: bracketed, upper-case, no spaces,
# so a translator is unlikely to render it into the target language. Survival
# is verified after every call regardless -- see restore_options().
OPTIONS_PLACEHOLDER = "[[OPTIONS_LIST]]"

# Tolerate a model that alters the marker's punctuation or spacing but keeps
# the word, e.g. "[[ OPTIONS_LIST ]]" or "[OPTIONS_LIST]".
_PLACEHOLDER_RE = re.compile(r"\[{1,2}\s*OPTIONS[_\s]?LIST\s*\]{1,2}", re.IGNORECASE)


def render_options_block(options: list[str]) -> str:
    """The numbered list exactly as the pipeline renders it.

    Mirrors `"\\n".join(f"{i + 1}. {n}" for i, n in enumerate(opts))`, the form
    used at all 14 sites in backend/agent/__init__.py.
    """
    return "\n".join(f"{i + 1}. {name}" for i, name in enumerate(options or []))


def mask_options(text: str, options: list[str]) -> tuple[str, str | None]:
    """Replace the rendered option list in ``text`` with the placeholder.

    Returns ``(masked_text, block)``; ``block`` is None when the list is not
    present verbatim, in which case nothing is masked and the caller translates
    the text unchanged -- never a silent partial mask.
    """
    if not text or not options:
        return text, None
    block = render_options_block(options)
    if not block or block not in text:
        return text, None
    return text.replace(block, OPTIONS_PLACEHOLDER, 1), block


def restore_options(translated: str, block: str | None) -> str:
    """Put the original option list back into a translated string.

    The block is re-inserted byte-for-byte from the structured data, so the
    option labels in the final response are the pipeline's own strings -- they
    never passed through the model and cannot have been altered by it.

    If the placeholder did not survive translation, the block is appended
    rather than lost: a response missing its options is unusable, whereas one
    with the list in a slightly odd position is still correct and selectable.
    """
    if block is None:
        return translated
    if not translated:
        return block
    match = _PLACEHOLDER_RE.search(translated)
    if match:
        return translated[: match.start()] + block + translated[match.end():]
    return f"{translated.rstrip()}\n\n{block}"


def is_only_placeholder(text: str) -> bool:
    """True when masking consumed the whole field.

    Some sites set ``response_text=opts_text`` with no surrounding prose
    (backend/agent/__init__.py:1244). There is then nothing to translate, and
    asking a model to translate a bare marker invites it to invent text.
    """
    return bool(text) and not _PLACEHOLDER_RE.sub("", text).strip()


def split_payload(
    payload: dict[str, str], options: list[str] | None
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Split a translatable payload around the option list.

    Returns ``(to_translate, blocks, passthrough)``:
      * ``to_translate`` - fields that still contain prose after masking
      * ``blocks``       - masked option list per field, for restoration
      * ``passthrough``  - fields that were nothing but the option list, which
                           are returned verbatim without a model call at all
    """
    to_translate: dict[str, str] = {}
    blocks: dict[str, str] = {}
    passthrough: dict[str, str] = {}

    for name, text in payload.items():
        masked, block = mask_options(text, options or [])
        if block is not None:
            blocks[name] = block
        if block is not None and is_only_placeholder(masked):
            passthrough[name] = block
            continue
        to_translate[name] = masked
    return to_translate, blocks, passthrough


def reassemble(
    translated: dict[str, str], blocks: dict[str, str], passthrough: dict[str, str]
) -> dict[str, str]:
    """Rebuild the localized payload from translated prose + original blocks."""
    out = dict(passthrough)
    for name, text in translated.items():
        out[name] = restore_options(text, blocks.get(name))
    return out
