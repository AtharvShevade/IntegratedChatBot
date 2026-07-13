# version_mode.py — deployment-level 5.5 vs 6.0 switch.
#
# Tenant-aware code (config.py, auth_service.py, config_6_0.py) already
# branches correctly on whether a request carries tenant_id — that data-driven
# branch is unchanged by this module. APP_VERSION is a *deployment* assertion
# on top of it: in a 6.0 deployment, a request missing tenant_id is a bug
# (wrong iframe wiring, stale frontend build, etc.), not a valid "fall back to
# 5.5" case — so 6.0 mode enforces tenant_id is present instead of silently
# defaulting to global paths.
#
#   APP_VERSION=5.5   (default) — session-based auth, direct repo path, no
#                       tenant_id required or expected.
#   APP_VERSION=6.0             — JWT-derived tenant_id required on every
#                       request that resolves repo paths or auth.

import os

APP_VERSION: str = os.getenv("APP_VERSION", "5.5").strip()

IS_6_0: bool = APP_VERSION == "6.0"
IS_5_5: bool = not IS_6_0
