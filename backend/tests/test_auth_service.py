#!/usr/bin/env python3
"""Tests for authorization bypass behavior in backend.services.auth_service."""

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services import auth_service


class AuthServiceToggleTests(unittest.TestCase):

    def tearDown(self) -> None:
        importlib.reload(auth_service)
        return super().tearDown()

    def test_get_allowed_form_ids_bypasses_authorization_when_disabled(self):
        with patch.dict(os.environ, {"AUTHORIZATION_ENABLED": "false"}):
            importlib.reload(auth_service)
            result = auth_service.get_allowed_form_ids("anyuser")
            self.assertIsNone(result)
            self.assertFalse(auth_service.AUTHORIZATION_ENABLED)

    def test_can_generate_instance_allows_when_authorization_disabled(self):
        with patch.dict(os.environ, {"AUTHORIZATION_ENABLED": "false"}):
            importlib.reload(auth_service)
            self.assertTrue(auth_service.can_generate_instance("anyuser"))
            self.assertFalse(auth_service.AUTHORIZATION_ENABLED)

    def test_get_allowed_form_ids_still_uses_default_authorization_when_enabled(self):
        with patch.dict(os.environ, {"AUTHORIZATION_ENABLED": "true"}):
            importlib.reload(auth_service)
            self.assertIsNone(auth_service.get_allowed_form_ids(""))
            self.assertTrue(auth_service.AUTHORIZATION_ENABLED)


if __name__ == "__main__":
    unittest.main()
