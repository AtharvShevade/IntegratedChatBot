"""L-10: serialize_rows() converted Decimal values to float, which silently
loses precision on high-precision/large financial figures. Now serialized as
str(value) instead, preserving the exact decimal representation.
"""
from __future__ import annotations

from decimal import Decimal

from backend.sql_agent.utils import serialize_rows


class TestDecimalSerialization:
    def test_decimal_is_serialized_as_string_not_float(self):
        rows = [(Decimal("123.456789012345"),)]
        result = serialize_rows(rows)
        assert result == [["123.456789012345"]]
        assert isinstance(result[0][0], str)

    def test_precision_is_not_lost_for_values_float_would_round(self):
        # float(Decimal("0.1")) == 0.1 but float(Decimal(...)) can lose
        # trailing precision for values beyond float's 15-17 significant
        # digits -- this value would be mangled by a float round-trip.
        value = Decimal("12345678901234567.89")
        rows = [(value,)]
        result = serialize_rows(rows)
        assert result == [[str(value)]]
        assert result[0][0] == "12345678901234567.89"

    def test_negative_and_zero_decimals(self):
        rows = [(Decimal("-42.50"), Decimal("0"), Decimal("0.00"))]
        result = serialize_rows(rows)
        assert result == [["-42.50", "0", "0.00"]]

    def test_non_decimal_behavior_is_unchanged(self):
        rows = [(None, 42, 3.14, "text")]
        result = serialize_rows(rows)
        assert result == [[None, 42, 3.14, "text"]]

    def test_mixed_row_with_decimal_and_other_types(self):
        rows = [(1, Decimal("99.99"), None, "label")]
        result = serialize_rows(rows)
        assert result == [[1, "99.99", None, "label"]]
