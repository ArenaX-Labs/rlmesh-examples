FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/

# Headless MuJoCo rendering (OSMesa), plus git to fetch the pinned Meta-World revision.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglew2.2 libosmesa6 libegl1 libglib2.0-0 git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY metaworld_env.py tasks.py ./

ENV PATH="/app/.venv/bin:$PATH" \
    MUJOCO_GL=osmesa \
    PYTHONUNBUFFERED=1 \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=120s CMD test -f /tmp/rlmesh-ready.json
CMD ["python", "-m", "rlmesh.serve", "--env", "metaworld_env:MetaWorld"]
