# Build from the repo root:  docker build -t rlmesh-examples/env-stack-conflict/sim-modern env-stack-conflict/sim-modern
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/

# Headless MuJoCo rendering for env.render().
RUN apt-get update && apt-get install -y --no-install-recommends libosmesa6 libgl1 \
    && rm -rf /var/lib/apt/lists/*
ENV MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa

WORKDIR /app/env-stack-conflict/sim-modern
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY env.py ./
ENV PATH="/app/env-stack-conflict/sim-modern/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RLMESH_ADDRESS=0.0.0.0:50051

EXPOSE 50051
CMD ["python", "-m", "rlmesh.serve", "--env", "env:HalfCheetahModern"]
