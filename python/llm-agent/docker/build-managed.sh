#!/usr/bin/env bash
# Build the harness and env images for RLMesh Managed (linux/amd64), stamp each with its
# describe label, and tag it REGISTRY/NAMESPACE/NAME:TAG. Nothing is pushed: push the
# tags you want as :latest yourself (README, "RLMesh Managed").
#
#   docker/build-managed.sh REGISTRY/NAMESPACE TAG [NAME...]
set -euo pipefail

[ $# -ge 2 ] || { echo "usage: $0 REGISTRY/NAMESPACE TAG [NAME...]" >&2; exit 2; }
prefix=$1 tag=$2
shift 2

# name class dockerfile [build args...]
images=(
  "llm-harness harness:LLMHarness harness.Dockerfile --build-arg OPENAI_MODEL=claude-sonnet-5-5"
  "llm-env-chat chat_env:AdditionTask env-chat.Dockerfile --target addition"
  "llm-env-tictactoe chat_env:TicTacToeTask env-chat.Dockerfile --target tictactoe"
  "llm-env-wordle serve_v0:EnvironmentEnv env-v0.Dockerfile --build-arg ENV_ID=wordle"
  "llm-env-math500 serve_v1:TasksetEnv env-v1.Dockerfile --target taskset"
  "llm-env-tau2 serve_v1:V1EnvEnv env-v1.Dockerfile --target environment --build-arg ENV_ID=primeintellect/tau2-bench"
)

cd "$(dirname "$0")/.."
for row in "${images[@]}"; do
  read -r name class dockerfile build_args <<<"$row"
  if [ $# -gt 0 ] && [[ " $* " != *" $name "* ]]; then
    continue
  fi
  # A local-only name for the unlabelled build, so BuildKit never looks it up in a registry.
  build=llm-agent-build/$name
  # No attestations: they turn the push into an OCI index, which Managed does not take.
  # shellcheck disable=SC2086 # build_args is a flag list
  docker build --platform linux/amd64 --provenance=false --sbom=false \
    -f "docker/$dockerfile" -t "$build" $build_args .
  label=$(docker run --rm --platform linux/amd64 --entrypoint rlmesh "$build" describe "$class" --label)
  # OCI media types: the platform registry refuses docker-format manifests.
  echo "FROM $build" | docker buildx build --platform linux/amd64 --provenance=false --sbom=false \
    --label "$label" --output "type=image,name=$prefix/$name:$tag,oci-mediatypes=true" -
  echo "built $prefix/$name:$tag"
done
