# Build from the repo root:  docker build -t rlmesh-examples/metaworld metaworld
FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/

# Headless MuJoCo rendering (OSMesa) plus git to fetch the pinned Meta-World rev.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglew2.2 libosmesa6 libegl1 libglib2.0-0 git \
    && rm -rf /var/lib/apt/lists/*
ENV MUJOCO_GL=osmesa

WORKDIR /app/metaworld
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY metaworld_env.py tasks.py ./
ENV PATH="/app/metaworld/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RLMESH_ADDRESS=0.0.0.0:50051

EXPOSE 50051
CMD ["python", "-m", "rlmesh.serve", "--env", "metaworld_env:MetaWorld"]
