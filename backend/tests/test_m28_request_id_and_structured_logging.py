"""M-28: a per-request correlation ID (X-Request-ID) is now minted (or
reused from the client) by middleware, available throughout the request via
backend.utils.request_context.get_request_id(), echoed back as a response
header, and attached to every log record. LOG_FORMAT=json opts into
structured JSON log lines; unset preserves the exact previous plain-text
format (just with request_id appended).
"""
from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from backend import main as main_module
from backend.utils import request_context
from backend.utils.logger import JsonFormatter, RequestIdFilter


@pytest.fixture
def client():
    return TestClient(main_module.app)


class TestRequestIdContextvar:
    def test_defaults_to_dash_outside_a_request(self):
        assert request_context.get_request_id() == "-"

    def test_set_get_reset_round_trip(self):
        token = request_context.set_request_id("abc123")
        try:
            assert request_context.get_request_id() == "abc123"
        finally:
            request_context.reset_request_id(token)
        assert request_context.get_request_id() == "-"

    def test_new_request_id_is_a_32char_hex_string(self):
        rid = request_context.new_request_id()
        assert len(rid) == 32
        int(rid, 16)  # does not raise -- valid hex


class TestRequestIdMiddleware:
    def test_response_carries_an_x_request_id_header(self, client):
        res = client.get("/health")
        assert "x-request-id" in res.headers
        rid = res.headers["x-request-id"]
        assert len(rid) == 32

    def test_client_supplied_request_id_is_echoed_back(self, client):
        res = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
        assert res.headers["x-request-id"] == "my-custom-id"

    def test_two_requests_get_different_generated_ids(self, client):
        r1 = client.get("/health")
        r2 = client.get("/health")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]

    def test_request_id_is_cleared_after_the_request_completes(self, client):
        client.get("/health", headers={"X-Request-ID": "leaked-check"})
        assert request_context.get_request_id() == "-"


class TestRequestIdFilter:
    def test_attaches_request_id_attribute_to_a_record(self):
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", (), None)
        token = request_context.set_request_id("filter-test-id")
        try:
            RequestIdFilter().filter(record)
        finally:
            request_context.reset_request_id(token)
        assert record.request_id == "filter-test-id"

    def test_does_not_overwrite_an_already_set_request_id(self):
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", (), None)
        record.request_id = "pre-existing"
        RequestIdFilter().filter(record)
        assert record.request_id == "pre-existing"


class TestJsonFormatter:
    def test_formats_a_record_as_valid_json_with_expected_fields(self):
        record = logging.LogRecord(
            "backend.test", logging.INFO, __file__, 1, "hello %s", ("world",), None,
            func="my_func",
        )
        record.request_id = "json-test-id"
        line = JsonFormatter().format(record)
        parsed = json.loads(line)
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "backend.test"
        assert parsed["function"] == "my_func"
        assert parsed["request_id"] == "json-test-id"

    def test_includes_exc_info_when_present(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                "backend.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info(),
            )
        record.request_id = "-"
        parsed = json.loads(JsonFormatter().format(record))
        assert "ValueError" in parsed["exc_info"]
        assert "boom" in parsed["exc_info"]
