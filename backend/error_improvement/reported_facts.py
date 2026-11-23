"""What the filer actually reported, read from the return's instance XML.

The validator's error file lists a failing operand that was never reported as a bare 'variable = 0' with no item. The
instance holds every reported fact with its full context (axis -> member), so it answers two things:
  * was this item reported at all (a reported 0 is not the same as nothing)?
  * what are the dimensions of a context (axis -> member), without decoding the context id?
Found next to the error file: <stem>_Instance.xml (all returns that keep their instance).
"""
from __future__ import annotations

import os
import re

from . import cell_locator as cl


class Reported:
    def __init__(self, inst: "cl.Instance"):
        self._ctx = {cid: dict(c.explicit) for cid, c in inst.contexts.items()}
        self._typed = {cid: dict(c.typed) for cid, c in inst.contexts.items()}
        self._facts = {(f.concept, f.context): f.value for f in inst.facts}

    def ctx_dims(self, ctx_id: str):
        """{axis: member} for a context id, or None when the instance has no such context."""
        return self._ctx.get(ctx_id)

    def typed_values(self, ctx_id: str) -> dict:
        return self._typed.get(ctx_id, {})

    def value(self, concept: str, ctx_id: str):
        """The reported value of (concept, context), or None when it was never reported."""
        return self._facts.get((cl.local(concept), ctx_id))

    @property
    def fact_count(self) -> int:
        return len(self._facts)


def instance_path(error_file: str) -> str | None:
    """<dir>/<stem>_Instance.xml for an error file named <stem>_Instance.html (same stem)."""
    d, name = os.path.split(error_file)
    stem = re.sub(r"_(Instance|XBRLError)\.(html|xml)$", "", name)
    p = os.path.join(d, stem + "_Instance.xml")
    return p if os.path.isfile(p) else None


def load(error_file: str) -> "Reported | None":
    p = instance_path(error_file)
    if p is None:
        return None
    try:
        return Reported(cl.read_instance(p))
    except Exception:                                        # noqa: BLE001 - an unreadable instance is simply not evidence
        return None
