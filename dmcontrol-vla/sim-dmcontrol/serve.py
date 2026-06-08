from dm_control import suite
from rlmesh import EnvServer
from wrapper import RLMeshDmControlWrapper

ADDRESS = "tcp://127.0.0.1:5558"
INSTRUCTION = "bring the ball to the target"

env = RLMeshDmControlWrapper(
    suite.load(
        "manipulator",
        "bring_ball",
        task_kwargs={"random": 0, "time_limit": 4.0},
    ),
    instruction=INSTRUCTION,
    image_size=128,
)
EnvServer(env, ADDRESS).serve()
