# VLA adapters

Four VLA checkpoints and three manipulation envs, 12 pairings, and no hand-written adapter between
any of them: each env tags its fields by role, each model declares its payload, and RLMesh resolves
the conversion per pair.

## Run it

```bash
uv run --directory python/vla-adapters run.py                                 # every model x env pair
uv run --directory python/vla-adapters run.py --model xvla --env libero      # one pairing
```

The dry run needs no simulator, GPU or server: it pushes a synthetic observation through each
resolved adapter and prints `adapter.explain()`, the model payload and the env-ready action. For
`xvla` on `libero`, the cameras are resized to 256x256, `robot0_eef_quat` is converted
`quat_xyzw -> rot6d_rowmajor` and padded to the checkpoint's 20 state dims, and the 10-dim EE6D
action is converted back to axis-angle.

## The RLMesh part

An env tags its spaces, and knows nothing about models ([`envs/libero.py`](envs/libero.py)):

```python
TAGS = adapt.EnvTags(
    observation={
        "agentview_image": adapt.ImageTag(adapt.IMAGE_PRIMARY),
        "robot0_eye_in_hand_image": adapt.ImageTag(adapt.IMAGE_WRIST),
        "robot0_eef_pos": adapt.StateTag(adapt.EEF_POS),
        "robot0_eef_quat": adapt.StateTag(adapt.EEF_ROT, encoding="quat_xyzw"),
        "robot0_gripper_qpos": adapt.StateTag(adapt.GRIPPER_POS),
        "instruction": adapt.TextTag(adapt.INSTRUCTION),
    },
    action=adapt.Action(...),
)
```

A model declares what its checkpoint ingests and emits, and knows nothing about envs
([`models/smolvla.py`](models/smolvla.py)):

```python
SPEC = adapt.ModelSpec(
    allow=("rebind_camera", "drop_action"),
    input={
        "observation.images.image": adapt.Image(adapt.IMAGE_PRIMARY, size=224, fit="stretch"),
        "observation.images.image2": adapt.Image(adapt.IMAGE_WRIST, size=224, fit="stretch"),
        "observation.state": adapt.Concat(
            adapt.EEF_POS,
            adapt.State(adapt.EEF_ROT, encoding="axis_angle"),
            adapt.GRIPPER_POS,
            container="list",
        ),
        "instruction": adapt.Text(adapt.INSTRUCTION),
    },
    output=adapt.Action(...),
)
```

and one call pairs them ([`run.py`](run.py)):

```python
adapt.resolve(env.tags, env.observation_space, env.action_space, model_entry.spec)
```

Against a live env that publishes its tags, `Model(predict, spec=SPEC)` resolves the same adapter
from the session contract alone.

## Needs

CPU. Live runs need a served env and a real checkpoint behind `load_predict_fn()`.

## Next

- **Add a model:** a `models/<name>.py` with `SPEC` and `load_predict_fn()`, plus one line in
  `models/__init__.py`. It then runs on every registered env.
- **Add an env:** an `envs/<name>.py` with `TAGS`, its spaces and a `sample_obs()`, plus one line in
  `envs/__init__.py`, or serve it with `rlmesh.EnvServer(env, "127.0.0.1:7447/libero", tags=TAGS)`
  and skip the registry. A flat `Box` observation is tagged with a `Split` of fields in order
  ([`envs/metaworld.py`](envs/metaworld.py)).
- **Live endpoint:**
  `RLMESH_ENV_ADDRESS='127.0.0.1:7447#<key>/libero' uv run --directory python/vla-adapters run.py --model smolvla --env libero`.
  The address carries the session key, so pass it in the environment rather than `--address`.
- **Lossy projections need consent.** Specs here `allow` dropping MetaWorld's unused rotation
  command, reading one of LIBERO's two finger positions, and rebinding Bridge's only camera to a
  wrist input; review those for a real checkpoint. Roles bind only on identical strings, and
  matching fields never makes a checkpoint good at a task it was not trained for.
- **Escape hatches:** [`models/act.py`](models/act.py) wraps the resolved adapter with stateful
  temporal ensembling of action chunks (`AdapterBase`), and [`overrides/`](overrides/) replaces the
  adapter for one specific pairing. A spec can also carry a `Custom(transform=fn)` input; specs are
  data, and an entrypoint string is imported only with `trust_entrypoints=True`.
