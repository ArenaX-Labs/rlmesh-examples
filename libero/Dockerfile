# Build from the repo root:  docker build -t rlmesh-examples/libero libero
FROM python:3.10-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/

# Headless MuJoCo rendering (OSMesa), plus a toolchain for egl-probe (sdist only).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglew2.2 libosmesa6 libegl1 libglib2.0-0 gcc g++ cmake make \
    && rm -rf /var/lib/apt/lists/*
ENV MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa

WORKDIR /app/libero
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
ENV PATH="/app/libero/.venv/bin:$PATH"

# Bake the sim assets (~400MB, from the HF Hub) into the image so the container
# starts offline. `echo N` answers LIBERO's first-import config prompt.
RUN echo N | python -c "from pathlib import Path; from libero.libero import get_assets_path; assets = Path(get_assets_path()); assert assets.is_dir(), f'Missing LIBERO assets: {assets}'"

COPY libero_env.py ./
ENV PYTHONUNBUFFERED=1 \
    RLMESH_ADDRESS=0.0.0.0:50051

EXPOSE 50051
CMD ["python", "-m", "rlmesh.serve", "--env", "libero_env:Libero"]
