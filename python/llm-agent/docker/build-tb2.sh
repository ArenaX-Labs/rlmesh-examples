#!/usr/bin/env bash
# Build Terminal-Bench 2 tasks as RLMesh Managed env images (linux/amd64), labelled and
# tagged REGISTRY/NAMESPACE/tb2-TASK:TAG. Nothing is pushed.
#
#   docker/build-tb2.sh TB2_CHECKOUT REGISTRY/NAMESPACE TAG TASK...
set -euo pipefail

[ $# -ge 4 ] || { echo "usage: $0 TB2_CHECKOUT REGISTRY/NAMESPACE TAG TASK..." >&2; exit 2; }
tb2=$(cd "$1" && pwd) prefix=$2 tag=$3
shift 3
cd "$(dirname "$0")/.."

PYTHON_URL=https://github.com/astral-sh/python-build-standalone/releases/download/20251014/cpython-3.12.12+20251014-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz
UV_URL=https://github.com/astral-sh/uv/releases/download/0.9.5/uv-x86_64-unknown-linux-gnu.tar.gz
RLMESH_VERSION=0.2.0a2

cache=${XDG_CACHE_HOME:-$HOME/.cache}/rlmesh-tb2
ctx=$cache/context
mkdir -p "$cache"
if [ ! -x "$ctx/python/bin/python3" ]; then
  rm -rf "$ctx" && mkdir -p "$ctx/uv"
  curl -fsSL "$PYTHON_URL" | tar -xz -C "$ctx"
  curl -fsSL "$UV_URL" | tar -xz -C "$ctx/uv" --strip-components 1
  printf 'export PATH="$HOME/.local/bin:$PATH"\n' > "$ctx/uv/env"
  uv pip install --quiet --python-platform x86_64-manylinux_2_28 --python-version 3.12 \
    --target "$ctx/python/lib/python3.12/site-packages" "rlmesh==$RLMESH_VERSION" pillow numpy
fi
if [ ! -f "$ctx/fonts/DejaVuSansMono.ttf" ]; then
  # Task images rarely ship fonts; the frames want DejaVu, which matplotlib's wheel bundles.
  rm -rf "$cache/mpl" "$ctx/fonts" && mkdir -p "$ctx/fonts"
  uv pip install --quiet --no-deps --python-platform x86_64-manylinux_2_28 --python-version 3.12 \
    --target "$cache/mpl" matplotlib==3.10.3
  cp "$cache/mpl/matplotlib/mpl-data/fonts/ttf/"DejaVuSans{,-Bold,Mono,Mono-Bold}.ttf "$ctx/fonts/"
fi
cp chat_env.py render.py terminal_env.py "$ctx/python/lib/python3.12/site-packages/"

for task in "$@"; do
  dir=$tb2/$task
  image=$(sed -n 's/^docker_image = "\(.*\)"/\1/p' "$dir/task.toml")
  rm -rf "$ctx/task" && mkdir -p "$ctx/task"
  cp -R "$dir/tests" "$ctx/task/tests"
  cp "$dir/instruction.md" "$ctx/task/"
  echo "terminal-bench/$task" > "$ctx/task/name"

  apt=$(grep -hoE 'apt-get install[^&;|>]*' "$dir/tests/test.sh" | sed 's/apt-get install//' \
    | tr ' ' '\n' | grep -vE '^-|^$' | sort -u | tr '\n' ' ' || true)
  pythons=$(grep -hoE -- '(-p|--python) [0-9.]+' "$dir/tests/test.sh" | awk '{print $2}' | sort -u | tr '\n' ' ' || true)
  build=llm-agent-build/tb2-$task
  docker buildx build --platform linux/amd64 --provenance=false --sbom=false --load \
    -f docker/env-terminal.Dockerfile --build-arg "TASK_IMAGE=$image" \
    --build-arg "APT_PACKAGES=$apt" --build-arg "UV_PYTHONS=$pythons" -t "$build" "$ctx"
  label=$(docker run --rm --platform linux/amd64 --cpus 2 --memory 2g \
    --entrypoint /opt/rlmesh/python/bin/python3 "$build" -m rlmesh describe terminal_env:TerminalTask --label)
  # OCI media types: the platform registry refuses docker-format manifests.
  echo "FROM $build" | docker buildx build --platform linux/amd64 --provenance=false --sbom=false \
    --label "$label" --output "type=image,name=$prefix/tb2-$task:$tag,oci-mediatypes=true" -
  echo "built $prefix/tb2-$task:$tag"
done
