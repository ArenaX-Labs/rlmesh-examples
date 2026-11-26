FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY hello_env.py ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=60s CMD test -f /tmp/rlmesh-ready.json
CMD ["python", "-m", "rlmesh.serve", "--env", "hello_env:HelloEnv"]
