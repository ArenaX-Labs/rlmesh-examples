# Coding agent

Claude solves a LIBERO task by writing its policy as code: it probes the env by hand, writes
`policy.py`, evaluates it through RLMesh and fixes it until it passes. Claude is never in the
control loop; the finished policy runs at the env's own rate with no model calls.

## Run it

With the LIBERO venv from [Needs](#needs), serve a task and run the agent:

```bash
~/libero-venv/bin/python python/coding-agent/libero_env.py --suite libero_spatial --task-id 0
uv run --directory python/coding-agent run.py --skill libero_spatial_0    # in a second terminal
```

The agent prints its narration, tool calls and evaluation results; a passing policy lands in
`workdir/skills/libero_spatial_0.py`.

## The RLMesh part

The agent's `step` tool drives the served env through a `RemoteEnv`, and its `evaluate` tool turns
the written `predict` into a model and runs it on layouts the agent never explored
([`run.py`](run.py)):

```python
obs, reward, terminated, truncated, info = env.step(np.asarray(action, dtype=np.float32))
...
predict = runpy.run_path(str(POLICY))["predict"]
session.disconnect()  # the env server takes one client at a time
model = Model(lambda obs: np.asarray(predict(obs), np.float32))
result = model.run(session.address, seeds=seeds)
```

The env side is a plain object with spaces, `reset` and `step`, served as is
([`libero_env.py`](libero_env.py)):

```python
server = rlmesh.EnvServer(env, args.address)
server.serve()
```

The agent reads the task from `info["instruction"]` on reset, so it works against any RLMesh env
that provides one.

## Needs

- CPU and an `ANTHROPIC_API_KEY`.
- A separate Python 3.10 environment for upstream
  [LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO), whose pinned robosuite and MuJoCo
  must not share the agent's:

  ```bash
  git clone https://github.com/Lifelong-Robot-Learning/LIBERO.git ~/LIBERO
  uv venv ~/libero-venv --python 3.10
  uv pip install --python ~/libero-venv/bin/python -e ~/LIBERO --config-settings editable_mode=compat
  uv pip install --python ~/libero-venv/bin/python \
    robosuite==1.4.1 mujoco==2.3.7 torch==2.5.1 bddl==1.0.1 \
    easydict gym cloudpickle imageio future matplotlib h5py termcolor tqdm pyyaml \
    "rlmesh[numpy]==0.2.0a2"
  ```

  `mujoco==2.3.7` because robosuite 1.4.1 breaks on MuJoCo 3, and `torch==2.5.1` because newer
  `torch.load` refuses LIBERO's pickled initial states. Answer `N` to LIBERO's dataset path prompt
  (`LIBERO_CONFIG_PATH=~/.libero-rlmesh` keeps it apart from another checkout's config).

- **A sandbox for the agent.** `evaluate` executes the code the model writes, in the agent's
  process: run the agent in a container or VM. On real hardware the env's `step()` must enforce
  workspace, joint and speed limits whatever action it receives, and the agent must not be able to
  edit the env or the drivers.

## Next

- **Record a video:** add `--trace run/trace.jsonl` to the env and `--log run/agent.jsonl` to the
  agent, then
  `uv run python/coding-agent/make_video.py run/trace.jsonl run/agent.jsonl --out run/agent_run.mp4`.
  It renders from the saved scene and joint positions in MuJoCo 3, with no OpenGL.
- `run.py --model` picks another Claude model and `--max-iterations` caps the turns (default 60);
  `libero_env.py --suite` and `--task-id` pick the task, `--max-steps` the budget (`520` for
  `libero_10`). Both take `--address` (default `127.0.0.1:5555`).
- **Vision:** render in `libero_env.py` (`MUJOCO_GL=egl`), add a `look(camera)` tool and drop the
  privileged object poses. **Another model:** the five tools are plain functions; swap the
  `tool_runner` loop. **Memory:** load `workdir/skills/` into the prompt so later tasks reuse
  earlier policies.
