import os

import gymnasium as gym
from stable_baselines3 import SAC

SEED = 0
TIMESTEPS = 100_000
OUTPUT = "models/sac-halfcheetah-v5-modern.zip"


def main():
    env = gym.make("HalfCheetah-v5")
    model = SAC("MlpPolicy", env, seed=SEED, device="cpu", verbose=1)
    model.learn(total_timesteps=TIMESTEPS, log_interval=10)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    model.save(OUTPUT)
    env.close()
    print(f"saved {OUTPUT}")


if __name__ == "__main__":
    main()
