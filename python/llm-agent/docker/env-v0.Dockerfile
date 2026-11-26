# A verifiers v0 environment as an env image. Build context: llm-agent.
#
#   docker build -f docker/env-v0.Dockerfile -t llm-env-v0 .
#   docker build -f docker/env-v0.Dockerfile -t llm-env-mastermind --build-arg ENV_ID=mastermind .
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /uvx /bin/
# render.py draws with these; without them it falls back to Pillow's own font.
RUN apt-get update && apt-get install -y --no-install-recommends fonts-inter fonts-jetbrains-mono \
    && rm -rf /var/lib/apt/lists/*

ARG RLMESH_VERSION=0.2.0a2
COPY requirements-v0.txt overrides-v0.txt .
# wordle on PyPI is another package, so Prime's index goes first.
RUN uv pip install --system --no-cache \
      --index https://hub.primeintellect.ai/primeintellect/simple \
      --index-strategy unsafe-first-match --override overrides-v0.txt \
      -r requirements-v0.txt "rlmesh==${RLMESH_VERSION}"

WORKDIR /app
COPY chat_env.py render.py serve_v0.py ./

ARG ENV_ID=wordle
ARG MAX_TURNS=
# A sandbox runs the container as the host user, who has no home here.
ENV ENV_ID=${ENV_ID} \
    MAX_TURNS=${MAX_TURNS} \
    HOME=/tmp \
    RLMESH_OUTPUT_DIR=/rlmesh/output/env \
    RLMESH_NAME=env \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json \
    NLTK_DATA=/opt/nltk_data \
    HF_HOME=/opt/hf
# Fetch the task's data now: Managed envs cannot reach NLTK's or most other download hosts.
RUN python -c "import verifiers as vf; vf.load_environment('${ENV_ID}').get_eval_dataset()" \
    && mkdir -p /opt/nltk_data /opt/hf && chmod -R a+rX,go-w /opt/nltk_data && chmod -R a+rwX /opt/hf
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=300s CMD test -f /tmp/rlmesh-ready.json
ENTRYPOINT ["python", "-m", "rlmesh.serve", "--env", "serve_v0:EnvironmentEnv"]
