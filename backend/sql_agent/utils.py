from typing import Any, List
from decimal import Decimal


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
