"""L-04: centralized SQL Agent prompt templates + injection hardening.

Scoped specifically to SQL generation/correction -- NOT the chatbot's other
LLM workflows (error explanation, variance explanation, beautifier), which
have their own prompt code and are explicitly out of scope here.

This intentionally does NOT move sql_generator.py's schema-rendering logic,
business-semantics blocks, or the large static rule text (_STATIC_DDL_RULES)
here -- those are tightly-tuned, data-driven prompt CONTENT, not reusable
templates, and moving them would be a behavior-risking rewrite with no
security benefit. What lives here are the few literal template fragments
that wrap untrusted input (the user's own question, the previous invalid
SQL, the validation/Oracle error text on a correction retry) plus the
sanitization applied to that input before it is ever interpolated in.

Versioned so a specific prompt shape is identifiable in logs
(see sql_generator.py's one `prompt_version=` log line per generation call).
"""
from __future__ import annotations

import re

SQL_GENERATION_PROMPT_VERSION = "sql_generation_v1"
SQL_CORRECTION_PROMPT_VERSION = "sql_correction_v1"

# C-05/L-04: the question previously went into the prompt raw as
# f"[QUESTION]{user_query}[/QUESTION]" with no neutralising of the
# delimiter tokens themselves (or of a markdown-heading-shaped "######"
# prefix that could be mistaken for a new instruction section) -- a
# question containing a literal "[/QUESTION]" could close the tag early and
# inject new "instructions" into the rest of the prompt. Stripped here,
# once, before the (sanitized) query is used in ANY prompt variant
# (initial generation or correction retry) -- a legitimate question never
# contains these tokens, so this is a no-op for normal input.
_INJECTION_PATTERN = re.compile(r"\[/?(?:QUESTION|SQL)\]|^#{2,}", re.IGNORECASE | re.MULTILINE)
_MAX_QUESTION_CHARS = 500


def sanitize_user_query(user_query: str) -> str:
    """Neutralise prompt-delimiter tokens in untrusted user text and cap its
    length, before it is ever placed inside [QUESTION]...[/QUESTION] or any
    other prompt section. Safe on ordinary questions -- they don't contain
    these tokens, so this returns them unchanged (besides the length cap)."""
    if not user_query:
        return user_query
    cleaned = _INJECTION_PATTERN.sub(" ", user_query)
    return cleaned[:_MAX_QUESTION_CHARS]


def wrap_tag(name: str, content: str) -> str:
    """Wrap a piece of retrieved/generated DATA (previous SQL, a validation
    or Oracle error message, schema text) in an explicit tag so the model
    sees it as context to read, not as an instruction to follow -- the same
    convention used for the question itself via [QUESTION]/[/QUESTION]."""
    return f"<{name}>\n{content}\n</{name}>"
