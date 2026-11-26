# A chat_env task as an env image; needs no verifiers. Build context: llm-agent.
#
#   docker build -f docker/env-chat.Dockerfile -t llm-env-chat .
#   docker build -f docker/env-chat.Dockerfile --target tictactoe -t llm-env-tictactoe .
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends fonts-inter fonts-jetbrains-mono \
    && rm -rf /var/lib/apt/lists/*
ARG RLMESH_VERSION=0.2.0a2
RUN pip install --no-cache-dir "rlmesh==${RLMESH_VERSION}" pillow numpy

WORKDIR /app
COPY chat_env.py render.py ./

ENV RLMESH_OUTPUT_DIR=/rlmesh/output/env \
    RLMESH_NAME=env \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=60s CMD test -f /tmp/rlmesh-ready.json

FROM base AS tictactoe
ENTRYPOINT ["python", "-m", "rlmesh.serve", "--env", "chat_env:TicTacToeTask"]

FROM base AS addition
ENTRYPOINT ["python", "-m", "rlmesh.serve", "--env", "chat_env:AdditionTask"]
