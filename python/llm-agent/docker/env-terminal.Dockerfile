# A Terminal-Bench 2 task as an env image: the task's own image plus the terminal_env server,
# with its own Python under /opt/rlmesh so the task's Python is untouched. Build with
# docker/build-tb2.sh, which stages the context. Its RUNs (apt, uv) run emulated on an arm64 host.
ARG TASK_IMAGE
FROM ${TASK_IMAGE}
# What the task's test.sh apt-installs: the env pod's egress cannot reach the apt mirrors.
ARG APT_PACKAGES=""
# An end-of-life Debian (bullseye) is served only from archive.debian.org.
RUN if [ -n "$APT_PACKAGES" ]; then \
      install() { apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y $APT_PACKAGES; }; \
      { install || { sed -i 's#deb.debian.org/debian#archive.debian.org/debian#; /-updates/d' \
          /etc/apt/sources.list && install; }; } && rm -rf /var/lib/apt/lists/*; \
    fi

COPY python/ /opt/rlmesh/python/
COPY task/ /opt/rlmesh/task/
# The task's test.sh installs uv with curl; the platform's egress allows neither host, so it ships here.
COPY uv/ /root/.local/bin/
# The Pythons test.sh asks uvx for (-p 3.13): uv would fetch them from GitHub release assets,
# which the egress proxy blocks.
ARG UV_PYTHONS=""
RUN if [ -n "$UV_PYTHONS" ]; then /root/.local/bin/uv python install $UV_PYTHONS; fi
COPY fonts/ /usr/share/fonts/truetype/rlmesh/

ENV RLMESH_OUTPUT_DIR=/rlmesh/output/env \
    RLMESH_NAME=env \
    RLMESH_READY_FILE=/tmp/rlmesh-ready.json
EXPOSE 7447
HEALTHCHECK --interval=2s --start-period=60s CMD test -f /tmp/rlmesh-ready.json
ENTRYPOINT ["/opt/rlmesh/python/bin/python3", "-m", "rlmesh.serve", "--env", "terminal_env:TerminalTask"]
CMD []
