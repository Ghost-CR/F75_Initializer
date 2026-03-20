#!/usr/bin/env bash
set -eu

REPO_ROOT="${AULA_HACKY_REPO_ROOT:-__AULA_HACKY_REPO_ROOT__}"
LOG_FILE="/tmp/aula-hacky-poll.log"

cd "$REPO_ROOT"

{
    if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
        exec "$REPO_ROOT/.venv/bin/python" -m aula_hacky.timer_sync --time now --quiet
    fi

    if [ -x /usr/local/bin/uv ]; then
        exec /usr/local/bin/uv run python -m aula_hacky.timer_sync --time now --quiet
    fi

    if [ -x /usr/bin/uv ]; then
        exec /usr/bin/uv run python -m aula_hacky.timer_sync --time now --quiet
    fi

    if [ -x /home/simon/.local/bin/uv ]; then
        exec /home/simon/.local/bin/uv run python -m aula_hacky.timer_sync --time now --quiet
    fi

    printf '%s timer failed: no usable python or uv entrypoint found\n' "$(date --iso-8601=seconds)"
    exit 1
} >>"$LOG_FILE" 2>&1
