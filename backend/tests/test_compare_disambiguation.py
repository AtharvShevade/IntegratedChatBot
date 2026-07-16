"""Regression tests for the Compare Instances disambiguation flow.

Bug: after a partial report name ("Compare cims") produced a multi-match
disambiguation list, replying with one of the shown report names failed
with "I couldn't find any report matching '<name>'." — even though the
name had just been shown as a valid option.

Root cause: the STAGE_CMP_REPORT disambiguation-selection branch in
decide() called _check_name_auth(selected, allowed_form_ids, "compare_reports")
and _compare_with_name(selected, session_id) WITHOUT tenant_id. Both
functions default tenant_id to None, so in 6.0 mode this looked up
Returns.xml under the wrong (non-tenant-scoped) path and always failed to
resolve the FormId — exactly reproducing the reported error. In 5.5 mode
tenant_id is legitimately always None, so this bug only manifested in 6.0.

Exact-name and Return ID compare flows (which go through _handle_compare's
single-match branch, unaffected by this omission) must continue to work
unchanged.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent import decide, _session_context

PATH_6_0_1001 = Path(r"D:\Repo6\Repo6\1001\DataBase")
_need_6_0_1001 = pytest.mark.skipif(not PATH_6_0_1001.is_dir(), reason="6.0 tenant 1001 real data tree not present")


def _run_compare_query(query: str, session_id: str, *, tenant_id=None, login_id=None):
    """Run `query` through decide() with compare_reports pre-selected as the
    LLM-extracted intent, matching how a real 'Compare X' message resolves
    without needing a live LLM call."""
    async def _run():
        with patch(
            "backend.agent.extract_intent_and_entities",
            AsyncMock(return_value={"intent": "compare_reports", "search_terms": query, "reporting_date": None}),
        ):
            return await decide(
                query, session_id=session_id, asp_session=None,
                login_id=login_id, user_id=None, role_id=None,
                tenant_id=tenant_id, conversation_history=[],
            )
    return asyncio.run(_run())


# ── 5.5 real data: natural chat flow, partial name -> candidate list -> pick ─

class TestPartialNameDisambiguation5_5:
    def test_partial_name_produces_candidate_list(self):
        _session_context.pop("test-cmp-partial-1", None)
        result = _run_compare_query("cims", "test-cmp-partial-1")
        assert result["result_type"] == "disambiguation"
        assert len(result["options"]) > 1
        assert all(name.upper().startswith("CIMS") for name in result["options"])

    def test_selecting_a_shown_candidate_by_full_name_resolves(self):
        session_id = "test-cmp-partial-2"
        _session_context.pop(session_id, None)
        disamb = _run_compare_query("cims", session_id)
        assert disamb["result_type"] == "disambiguation"
        chosen = disamb["options"][0]

        result = asyncio.run(decide(
            chosen, session_id=session_id, asp_session=None,
            login_id=None, user_id=None, role_id=None, conversation_history=[],
        ))
        # Must NOT be the "couldn't find any report matching" regression —
        # either instance selection proceeds, or a legitimate "no instance
        # files" result is returned, but never a failed name lookup for a
        # name that was JUST shown as a valid option.
        assert f"I couldn't find any report matching '{chosen}'" not in result["response_text"]

    def test_selecting_by_number_still_works(self):
        session_id = "test-cmp-partial-3"
        _session_context.pop(session_id, None)
        disamb = _run_compare_query("cims", session_id)
        assert disamb["result_type"] == "disambiguation"

        result = asyncio.run(decide(
            "1", session_id=session_id, asp_session=None,
            login_id=None, user_id=None, role_id=None, conversation_history=[],
        ))
        chosen = disamb["options"][0]
        assert f"I couldn't find any report matching '{chosen}'" not in result["response_text"]

    def test_short_partial_name_produces_candidate_list_and_resolves(self):
        """'ror' style short partial names must behave the same way as
        longer partial names like 'cims'."""
        session_id = "test-cmp-partial-4"
        _session_context.pop(session_id, None)
        result = _run_compare_query("ror", session_id)
        # 'ror' matches exactly ROR in this dataset (find_matching_reports
        # prefers exact/prefix matches) — either a direct resolution or a
        # short disambiguation list is acceptable, but never the
        # not-found regression for a name that exists.
        assert "couldn't find any report matching 'ror'" not in result["response_text"].lower() or \
            result["result_type"] == "disambiguation"


# ── Non-regression: exact name / Return ID flows (single-match, unaffected) ──

class TestExactNameAndReturnIdNoRegression5_5:
    def test_exact_report_name_resolves_directly(self):
        session_id = "test-cmp-exact-1"
        _session_context.pop(session_id, None)
        result = _run_compare_query("CIMS_ROR", session_id)
        assert result["result_type"] != "error" or "couldn't find any report matching" not in result["response_text"]

    def test_exact_crilc_resolves_directly(self):
        session_id = "test-cmp-exact-2"
        _session_context.pop(session_id, None)
        result = _run_compare_query("CIMS_CRILC_RFA", session_id)
        assert "couldn't find any report matching" not in result["response_text"]


# ── Real 6.0 data: the exact regression scenario from the bug report ────────

class TestCompareDisambiguation6_0:
    """tenant_id resolution reads backend.config.BASE_REPO_PATH, a
    module-level constant frozen at first import — this test process may
    already have it pointed elsewhere (per the real .env), and
    monkeypatch.setenv can't retroactively change an already-frozen
    constant. A fresh subprocess with the right env vars set BEFORE the
    interpreter starts is the only way to genuinely exercise 6.0 in-process
    (same pattern used in test_access_control.py and
    test_instance_generator_date_validation.py)."""

    def _run_in_subprocess(self, script_body: str) -> subprocess.CompletedProcess:
        script = textwrap.dedent(script_body)
        env = dict(os.environ)
        env["APP_VERSION"] = "6.0"
        env["BASE_REPO_PATH"] = str(PATH_6_0_1001.parent.parent)
        return subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)

    @_need_6_0_1001
    def test_partial_name_disambiguation_then_selection_resolves(self):
        result = self._run_in_subprocess(f"""
            import asyncio, sys
            sys.path.insert(0, {str(PROJECT_ROOT)!r})
            from unittest.mock import AsyncMock, patch
            from backend.agent import decide

            async def main():
                sid = "test-6-0-cmp-1"
                with patch(
                    "backend.agent.extract_intent_and_entities",
                    AsyncMock(return_value={{"intent": "compare_reports", "search_terms": "cims", "reporting_date": None}}),
                ):
                    r1 = await decide(
                        "Compare cims", session_id=sid, asp_session=None,
                        login_id="vaibhav@irisindia.net", user_id="0", role_id="0",
                        tenant_id="1001", conversation_history=[],
                    )
                assert r1["result_type"] == "disambiguation", r1
                chosen = r1["options"][0]
                r2 = await decide(
                    chosen, session_id=sid, asp_session=None,
                    login_id="vaibhav@irisindia.net", user_id="0", role_id="0",
                    tenant_id="1001", conversation_history=[],
                )
                assert f"I couldn't find any report matching '{{chosen}}'" not in r2["response_text"], r2["response_text"]
                print("OK")

            asyncio.run(main())
        """)
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert "OK" in result.stdout

    @_need_6_0_1001
    def test_guided_flow_partial_name_then_selection_resolves(self):
        """Same regression via the guided-menu entry point
        ('Perform comparative analysis' -> partial name -> selection)."""
        result = self._run_in_subprocess(f"""
            import asyncio, sys
            sys.path.insert(0, {str(PROJECT_ROOT)!r})
            from backend import guided
            from backend.agent import decide

            async def main():
                sid = "test-6-0-cmp-guided-1"
                guided._handle_action_selected("Perform comparative analysis", sid, "vaibhav@irisindia.net", "1001")
                guided._guided_sessions[sid] = {{"stage": guided.STAGE_CMP_REPORT}}
                r1 = await guided.guided_step("cims", sid, None, login_id="vaibhav@irisindia.net", tenant_id="1001")
                assert r1["result_type"] == "disambiguation", r1
                chosen = r1["options"][0]
                r2 = await decide(
                    chosen, session_id=sid, asp_session=None,
                    login_id="vaibhav@irisindia.net", user_id="0", role_id="0",
                    tenant_id="1001", conversation_history=[],
                )
                assert f"I couldn't find any report matching '{{chosen}}'" not in r2["response_text"], r2["response_text"]
                print("OK")

            asyncio.run(main())
        """)
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert "OK" in result.stdout

    @_need_6_0_1001
    def test_exact_name_still_resolves_in_6_0(self):
        """Non-regression: exact-name compare must keep working in 6.0."""
        result = self._run_in_subprocess(f"""
            import asyncio, sys
            sys.path.insert(0, {str(PROJECT_ROOT)!r})
            from unittest.mock import AsyncMock, patch
            from backend.agent import decide

            async def main():
                with patch(
                    "backend.agent.extract_intent_and_entities",
                    AsyncMock(return_value={{"intent": "compare_reports", "search_terms": "CIMS_ROR", "reporting_date": None}}),
                ):
                    r = await decide(
                        "Compare CIMS_ROR", session_id="test-6-0-cmp-exact-1", asp_session=None,
                        login_id="vaibhav@irisindia.net", user_id="0", role_id="0",
                        tenant_id="1001", conversation_history=[],
                    )
                assert "couldn't find any report matching" not in r["response_text"], r["response_text"]
                print("OK")

            asyncio.run(main())
        """)
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert "OK" in result.stdout

    @_need_6_0_1001
    def test_return_id_still_resolves_in_6_0(self):
        """Non-regression: Return ID (e.g. R018) compare must keep working."""
        result = self._run_in_subprocess(f"""
            import asyncio, sys
            sys.path.insert(0, {str(PROJECT_ROOT)!r})
            from unittest.mock import AsyncMock, patch
            from backend.agent import decide

            async def main():
                with patch(
                    "backend.agent.extract_intent_and_entities",
                    AsyncMock(return_value={{"intent": "compare_reports", "search_terms": "R018", "reporting_date": None}}),
                ):
                    r = await decide(
                        "Compare R018", session_id="test-6-0-cmp-rid-1", asp_session=None,
                        login_id="vaibhav@irisindia.net", user_id="0", role_id="0",
                        tenant_id="1001", conversation_history=[],
                    )
                assert "couldn't find any report matching" not in r["response_text"], r["response_text"]
                print("OK")

            asyncio.run(main())
        """)
        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
        assert "OK" in result.stdout
