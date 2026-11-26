# RLMesh Examples

Larger examples for [RLMesh](https://github.com/ArenaX-Labs/rlmesh): simulators, containers, VLA
adapters, LLM agents and native envs. Each folder is self-contained and installs a released
`rlmesh`, as a user would. For the concepts, start with the
[RLMesh README](https://github.com/ArenaX-Labs/rlmesh#readme) and its
[docs](https://rlmesh.dev/docs/); the small API examples live in the
[rlmesh repository](https://github.com/ArenaX-Labs/rlmesh/tree/main/examples).

| Example                                                                  | What it adds                                                                            | Hardware                             |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- | ------------------------------------ |
| [`python/hello-env/`](python/hello-env/)                                 | A small Gymnasium env, an `EnvFactory`, and the serve, build and run loop               | CPU                                  |
| [`python/byo-container/`](python/byo-container/)                         | Hand-written env and model images, run as sandboxes or with your own launcher           | CPU, Docker                          |
| [`python/sandbox/`](python/sandbox/)                                     | Sandboxes RLMesh builds for you from a Gymnasium id or a Hugging Face EnvHub repo       | CPU, Docker                          |
| [`python/metaworld/`](python/metaworld/)                                 | An upstream Gymnasium simulator with camera, state and instruction observations         | CPU                                  |
| [`python/libero/`](python/libero/)                                       | A non-Gymnasium simulator with fixed initial states and bundled assets                  | CPU                                  |
| [`python/dm-control/`](python/dm-control/)                               | A `dm_env` simulator behind Gymnasium-style calls, and a model that emits action chunks | CPU                                  |
| [`python/stack-conflict/`](python/stack-conflict/)                       | A SAC checkpoint evaluated on a simulator stack it cannot share a venv with             | CPU                                  |
| [`python/vla-adapters/`](python/vla-adapters/)                           | Env tags and model specs resolving adapters across many VLA × env pairs                 | CPU                                  |
| [`python/llm-agent/`](python/llm-agent/)                                 | An LLM agent harness on Prime Environments Hub tasks, locally or as Docker images       | CPU, an OpenAI-compatible LLM server |
| [`python/coding-agent/`](python/coding-agent/)                           | Claude probes a LIBERO task and writes its policy as code                               | CPU, Claude API key                  |
| [`python/ur10e-mujoco/`](python/ur10e-mujoco/)                           | A real-time session: a MuJoCo UR10e, a policy, teleop takeover, MCAP recording          | CPU                                  |
| [`cpp/chrono/`](cpp/chrono/)                                             | A Project Chrono robot served natively from C++ through the RLMesh C ABI                | CPU                                  |
| [`python/isaacsim/franka-reach/`](python/isaacsim/franka-reach/)         | A batched Isaac Sim Franka reach as a vector env                                        | RTX GPU                              |
| [`python/isaacsim/ur10e-pick-place/`](python/isaacsim/ur10e-pick-place/) | UR10e grasping with a resolved camera, pose and gripper adapter                         | RTX GPU                              |

## Setup

Install [`uv`](https://docs.astral.sh/uv/), and Docker for the container examples. Python examples
live in `python/`, the C++ one in `cpp/`. Each example has its own `pyproject.toml`; run
`uv run ...` from its folder and uv creates that folder's environment. Commands in the READMEs start
from the repository root unless they say otherwise.

Every example pins `rlmesh==0.2.0a2`. Use the same version in a client and the image it talks to:
`git grep -n -e 0.2.0a2 -e v0.2.0-alpha.2` lists every pin to move together.

A served env or model listens on port 7447, so run one example at a time or pick another port.

## Tests

```bash
uv run pytest              # CPU tests, a minute or so
uv run pytest -m docker    # tests that build and run Docker images
uv run ruff check . && uv run ruff format --check .
```

The root `pyproject.toml` holds the test and lint tools; the examples do not depend on it.

## License

MIT; see [LICENSE](LICENSE).
