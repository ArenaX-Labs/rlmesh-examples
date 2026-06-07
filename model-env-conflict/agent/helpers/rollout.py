import numpy as np
from tqdm import tqdm

from .recording import Recorder


def evaluate(policy, envs, *, seed=0, max_steps=1000, record=False):
    state = {}
    for name, env in envs.items():
        obs, _ = env.reset(seed=seed)
        state[name] = {
            "obs": np.asarray(obs),
            "ret": 0.0,
            "cost": 0.0,
            "steps": 0,
            "done": False,
        }

    recorder = Recorder(envs) if record else None
    if recorder:
        for name, env in envs.items():
            recorder.add(name, env)

    for _ in tqdm(range(max_steps), desc="stepping envs", unit="step"):
        if all(s["done"] for s in state.values()):
            break
        for name, env in envs.items():
            s = state[name]
            if s["done"]:
                continue
            obs, reward, terminated, truncated, info = env.step(policy(s["obs"]))
            s["obs"] = np.asarray(obs)
            s["ret"] += float(reward)
            s["cost"] += float(info.get("cost", 0.0))
            s["steps"] += 1
            s["done"] = terminated or truncated
            if recorder:
                recorder.add(name, env)

    if recorder:
        recorder.close()

    return {
        name: {
            "return": round(s["ret"], 2),
            "cost": round(s["cost"], 2),
            "steps": s["steps"],
        }
        for name, s in state.items()
    }


def close_all(envs):
    for env in envs.values():
        try:
            env.close()
        except Exception:
            pass
