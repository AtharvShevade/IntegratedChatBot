# H-15: containerized deployment path for the FastAPI backend ONLY.
#
# This is an ADDITIVE alternative to the existing IIS deployment
# (service_server.py / dev_server.py + frontend/public/web.config's reverse
# proxy, see port_guard.py) -- it does not change, replace, or require that
# deployment. Nothing here is wired into IIS, and nothing in the IIS path
# depends on this file.
#
# No port is hardcoded: BACKEND_PORT is read from the environment at
# container start (same contract as backend/config.py's _read_backend_port()
# -- there is still no built-in default, matching every other deployment of
# this app). No .env or secret is baked into the image -- real config is
# supplied at `docker run`/compose time via --env-file or a mounted .env,
# exactly like the native deployment already does.
#
# oracledb's thin mode (already a requirement, see requirements.txt) needs no
# Oracle Instant Client, so this image has no Oracle-specific system packages.

FROM python:3.13-slim AS base

# Reproducible: requirements-lock.txt pins every transitive dependency to
# the exact versions this backend/test suite was developed and verified
# against (see that file's own header) -- not requirements.txt's looser >=
# declarations.
COPY requirements-lock.txt /tmp/requirements-lock.txt
RUN pip install --no-cache-dir -r /tmp/requirements-lock.txt \
    && rm /tmp/requirements-lock.txt

# Runs as a non-root user -- nothing in this app needs root, and the
# container should not be able to write outside the directories it's
# explicitly given (the bind-mounted LOG_DIR / repo data volumes below).
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

# backend/sql_agent/embeddings_*/ are large, prebuilt artifacts committed to
# this repo (see M-31) -- copied in as part of backend/ below, same as a
# native checkout. SQL Agent code/config is untouched by this Dockerfile.
COPY backend/ ./backend/
COPY dev_server.py service_server.py port_guard.py ./
COPY .env.example ./

RUN mkdir -p /app/logs && chown -R appuser:appuser /app
USER appuser

# Documents the conventional port; the actual bind port is still whatever
# BACKEND_PORT resolves to at container start (see CMD below) -- this does
# not fix it.
ARG BACKEND_PORT=8001
EXPOSE ${BACKEND_PORT}

# SKIP_PORT_CHECK: port_guard.py's web.config-vs-BACKEND_PORT check exists
# specifically for the IIS reverse-proxy deployment; there is no IIS/
# web.config inside this container, so that check is not applicable here
# (a missing web.config already no-ops it, but this makes the "why" explicit
# rather than relying on that fallback silently).
ENV SKIP_PORT_CHECK=1

# BACKEND_HOST defaults to 0.0.0.0 here (NOT the native deployment's
# loopback-only 127.0.0.1 default, see dev_server.py/service_server.py's
# H-07 comment) -- that default exists so the backend is reachable only
# through the local IIS reverse proxy on the SAME machine. Inside a
# container, the network namespace is already the isolation boundary (Docker
# only exposes what `-p`/compose `ports:` publishes); binding to loopback
# here would make the service unreachable from outside the container
# entirely. Still fully overridable via BACKEND_HOST for a deployment that
# fronts this container with its own reverse proxy in the same network
# namespace (e.g. a sidecar).
ENV BACKEND_HOST=0.0.0.0

# sh -c only expands the env vars uvicorn needs as CLI arguments; exec
# replaces the shell so uvicorn remains PID 1's only child (receives signals
# directly, no shell left running underneath it).
CMD ["sh", "-c", "exec uvicorn backend.main:app --host \"$BACKEND_HOST\" --port \"${BACKEND_PORT:?BACKEND_PORT is not set}\""]
