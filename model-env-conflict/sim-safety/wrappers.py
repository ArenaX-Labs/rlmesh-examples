import gymnasium


class SafetyToGymnasiumWithCost(gymnasium.Wrapper):
    def step(self, action):
        observation, reward, cost, terminated, truncated, info = self.env.step(action)
        return observation, reward, terminated, truncated, {**info, "cost": float(cost)}
