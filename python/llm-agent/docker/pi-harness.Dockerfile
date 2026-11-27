# The pi coding agent harness as a model image. Build context: llm-agent.
#
#   docker build --platform linux/amd64 -f docker/pi-harness.Dockerfile -t pi-harness .
ARG BASE=python:3.11-slim
FROM node:22-slim AS pi
ARG PI_VERSION=0.73.1
RUN npm install --prefix /opt/pi --save-exact "@mariozechner/pi-coding-agent@${PI_VERSION}"

FROM ${BASE}
COPY --from=pi /usr/local/bin/node /usr/local/bin/node
COPY --from=pi /opt/pi /opt/pi

# A base that already has this rlmesh keeps it.
ARG RLMESH_VERSION=0.2.0a2
RUN pip install --no-cache-dir "rlmesh==${RLMESH_VERSION}"

WORKDIR /app
COPY chat_env.py harness.py pi_harness.py pi_tools.js ./

# PI_MODEL must be in pi's model list for its provider, or served at OPENAI_BASE_URL.
ARG PI_PROVIDER=anthropic
ARG PI_MODEL=claude-sonnet-4-6
ENV PI_COMMAND=/opt/pi/node_modules/.bin/pi \
    PI_PROVIDER=${PI_PROVIDER} \
    PI_MODEL=${PI_MODEL} \
    RLMESH_OUTPUT_DIR=/rlmesh/output/model \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=60s CMD test -f /tmp/rlmesh-ready.json
ENTRYPOINT ["python", "-m", "rlmesh.serve", "pi_harness:PiHarness"]
