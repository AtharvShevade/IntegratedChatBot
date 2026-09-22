"""
backend/tools — feature modules consumed by the agent (XBRL comparison,
error explanation, taxonomy lookup, instance generation, etc.) plus the
generic log-reading tool registry re-exported below.

The log-reading tools (get_error_logs, get_logs_by_report, TOOL_REGISTRY)
live in log_tools.py; they are re-exported here to preserve
`from backend.tools import get_error_logs` etc. for any existing caller.
"""

from .log_tools import get_error_logs, get_logs_by_report, TOOL_REGISTRY

__all__ = ["get_error_logs", "get_logs_by_report", "TOOL_REGISTRY"]
