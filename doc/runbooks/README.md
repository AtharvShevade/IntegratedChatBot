# Operational Runbooks

Step-by-step procedures for common operational tasks on this backend.
Commands, paths, and environment variables below are taken directly from
this repository (`backend/utils/logger.py`, `backend/utils/intent_log.py`,
`backend/db_qa/intents/embedding_index.py`, `backend/sql_agent/_bootstrap.py`,
`backend/services/llm_config.py`, `backend/main.py`, `backend/agent/background_jobs.py`,
`.env.example`). Where a detail isn't established anywhere in the
repository, the runbook says so explicitly rather than guessing.

- [Log rotation / log maintenance](log-maintenance.md)
- [Rebuild embeddings](rebuild-embeddings.md)
- [Restart / verify Ollama](restart-ollama.md)
- [Handle a stuck background job](stuck-background-job.md)
