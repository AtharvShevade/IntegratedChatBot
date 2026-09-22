"""Function-entry/exit tracing decorator for the db_qa pipeline.

Wraps a callable so that entering, exiting, and any exception are logged to
the "dbqa.tracer" logger at DEBUG level — opt-in only. Enable it (e.g. via
LOG_LEVEL or a per-logger override) to see the full call chain while
developing; it stays silent in production unless DEBUG is explicitly turned on.

Usage — individual function::

    from backend.utils.tracer import trace

    @trace
    def handle_my_department(store, params, user_id, is_admin):
        ...

Expected DEBUG output::

    ENTER handle_my_department(<XMLStore>, {}, 'iris810', False)
    EXIT  handle_my_department -> found=True records=1 summary='You are in ...'

Usage — auto-apply to all handle_* functions in a module (placed at module end)::

    import sys
    from backend.utils.tracer import trace as _trace

    _mod = sys.modules[__name__]
    for _fn_name in list(vars(_mod)):
        if _fn_name.startswith("handle_") and callable(getattr(_mod, _fn_name)):
            _fn = getattr(_mod, _fn_name)
            if not getattr(_fn, "__traced__", False):
                _t = _trace(_fn)
                _t.__traced__ = True
                setattr(_mod, _fn_name, _t)
"""
from __future__ import annotations

import functools
import logging

_trc = logging.getLogger("dbqa.tracer")

_MAX_ARG    = 120   # max chars per argument repr in the ENTER line
_MAX_RESULT = 300   # max chars for result repr in the EXIT line


def trace(func):
    """Decorator: print ENTER / EXIT / ERROR for every call to *func*."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        name = func.__qualname__

        # Build a compact, readable argument string.
        # Replace raw XMLStore repr with a short placeholder so output stays tidy.
        def _fmt(v: object) -> str:
            s = repr(v)
            if "XMLStore" in s:
                return "<XMLStore>"
            return s[:_MAX_ARG]

        parts = [_fmt(a) for a in args] + [f"{k}={_fmt(v)}" for k, v in kwargs.items()]
        sig   = ", ".join(parts)

        # DEBUG-gated only — this used to also unconditionally print() to
        # stdout on every call, which meant every DB Q&A query printed
        # ENTER/EXIT noise to the production console regardless of the
        # configured log level. Tracing is still fully available by
        # enabling DEBUG on the "dbqa.tracer" logger; it no longer fires
        # unconditionally in production.
        _trc.debug("ENTER %s(%s)", name, sig)

        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            _trc.exception("ERROR in traced function %s -> %s: %s", name, type(exc).__name__, exc)
            raise

        # Summarise the result concisely.
        # db_qa handlers return QueryResult dicts — show the most useful fields.
        if isinstance(result, dict) and "found" in result:
            r_repr = (
                f"found={result.get('found')} "
                f"records={len(result.get('records', []))} "
                f"summary={str(result.get('summary', ''))[:80]!r}"
            )
        else:
            r_repr = repr(result)[:_MAX_RESULT]

        _trc.debug("EXIT  %s -> %s", name, r_repr)
        return result

    return wrapper
