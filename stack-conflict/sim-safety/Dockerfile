FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/

# Headless MuJoCo rendering for env.render().
RUN apt-get update && apt-get install -y --no-install-recommends libosmesa6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY env.py ./

ENV PATH="/app/.venv/bin:$PATH" \
    MUJOCO_GL=osmesa \
    PYOPENGL_PLATFORM=osmesa \
    PYTHONUNBUFFERED=1 \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=120s CMD test -f /tmp/rlmesh-ready.json
CMD ["python", "-m", "rlmesh.serve", "--env", "env:HalfCheetahSafety"]
