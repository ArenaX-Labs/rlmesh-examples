# A Terminal-Bench 2 task as an env image: the task's own image plus the terminal_env server,
# with its own Python under /opt/rlmesh so the task's Python is untouched. Build with
# docker/build-tb2.sh, which stages the context. The only RUN is apt (emulated on an arm64 host).
ARG TASK_IMAGE
FROM ${TASK_IMAGE}
# What the task's test.sh apt-installs: the env pod's egress cannot reach the apt mirrors.
ARG APT_PACKAGES=""
RUN if [ -n "$APT_PACKAGES" ]; then \
      apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y $APT_PACKAGES \
      && rm -rf /var/lib/apt/lists/*; \
    fi

COPY python/ /opt/rlmesh/python/
COPY task/ /opt/rlmesh/task/
# The task's test.sh installs uv with curl; the platform's egress allows neither host, so it ships here.
COPY uv/ /root/.local/bin/
COPY fonts/ /usr/share/fonts/truetype/rlmesh/

ENV RLMESH_OUTPUT_DIR=/rlmesh/output/env \
    RLMESH_NAME=env \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=60s CMD test -f /tmp/rlmesh-ready.json
ENTRYPOINT ["/opt/rlmesh/python/bin/python3", "-m", "rlmesh.serve", "--env", "terminal_env:TerminalTask"]
CMD []
