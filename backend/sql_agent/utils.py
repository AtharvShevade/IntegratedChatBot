# backend/sql_agent/utils.py
#
# Row serialisation for the JSON response. Vendored from the agent's own
# api/utils.py (whose FastAPI layer this project's backend replaces) rather than
# imported from it, so nothing in backend/ depends on that discarded API package.

from __future__ import annotations

from decimal import Decimal
from typing import Any, List


def serialize_rows(rows: list) -> List[List[Any]]:
    """Convert Oracle-typed row tuples to JSON-safe Python types."""
    result = []
    for row in rows:
        serialized = []
        for val in row:
            if val is None:
                serialized.append(None)
            elif isinstance(val, Decimal):
                serialized.append(float(val))
            elif isinstance(val, (int, float)):
                serialized.append(val)
            else:
                serialized.append(str(val))
        result.append(serialized)
    return result
