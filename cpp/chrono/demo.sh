#!/usr/bin/env bash
# Usage: CHRONO_DIR=<chrono install prefix> cpp/chrono/demo.sh [run_model.py args]
# Optional: EIGEN_DIR, VULKAN_DIR, PORT (default 7447), RENDERER=vulkan,
# RLMESH_DIR (an rlmesh checkout; default: a clone of RLMESH_REF in cpp/chrono/.rlmesh).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rlmesh="${RLMESH_DIR:-$here/.rlmesh}"
ref="${RLMESH_REF:-v0.2.0-alpha.2}"
build="$here/build"
port="${PORT:-7447}"
: "${CHRONO_DIR:?set CHRONO_DIR to a Project Chrono install prefix}"
renderer="${RENDERER:-raytrace}"
prefix="$CHRONO_DIR${EIGEN_DIR:+;$EIGEN_DIR}${VULKAN_DIR:+;$VULKAN_DIR}"
vulkan=OFF
[[ "$renderer" == vulkan ]] && vulkan=ON

if [[ ! -d "$rlmesh" ]]; then
  echo "==> cloning rlmesh $ref"
  git clone --quiet --depth 1 --branch "$ref" https://github.com/ArenaX-Labs/rlmesh "$rlmesh"
fi
echo "==> building rlmesh-capi (release)"
(cd "$rlmesh" && RLMESH_RELEASE_BUILD=1 cargo build -p rlmesh-capi --release --lib)
echo "==> building the Chrono env"
cmake -S "$here" -B "$build" -DCMAKE_PREFIX_PATH="$prefix" -DRLMESH_DIR="$rlmesh" \
  -DCHRONO_REACH_VULKAN="$vulkan" >/dev/null
cmake --build "$build" -j"$(nproc)"

echo "==> serving on 127.0.0.1:$port"
"$build/chrono_reach_env" --address "127.0.0.1:$port" --renderer "$renderer" &
env_pid=$!
trap 'kill -TERM "$env_pid" 2>/dev/null; wait "$env_pid" 2>/dev/null || true' EXIT
sleep 1

echo "==> driving it from Python"
cd "$here"
uv run run_model.py "127.0.0.1:$port" "$@"
