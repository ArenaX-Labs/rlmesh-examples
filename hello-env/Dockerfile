# Build from the repo root:  docker build -t rlmesh-examples/hello-env hello-env
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/

WORKDIR /app/hello-env
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY hello_env.py ./
ENV PATH="/app/hello-env/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RLMESH_ADDRESS=0.0.0.0:50051

EXPOSE 50051
CMD ["python", "-m", "rlmesh.serve", "--env", "hello_env:HelloEnv"]
