from model import VLAModel
from recorder import Recorder
from rlmesh.numpy import Model
from tqdm import tqdm
from wrapper import RLMeshVLAWrapper

ENV_ADDRESS = "tcp://127.0.0.1:5558"
RECORD = True

model = VLAModel()
model.load()
vla = RLMeshVLAWrapper(model)
recorder = Recorder() if RECORD else None
progress = tqdm(desc="VLA", unit="step")


def predict(observation):
    if recorder is not None:
        recorder.add(observation["image"])
    progress.update(1)
    return vla.predict(observation)


try:
    Model(predict, on_episode_end=lambda *_: vla.reset()).run(ENV_ADDRESS, episodes=1)
finally:
    progress.close()
    if recorder is not None:
        recorder.close()
    model.close()
print("[agent] done", flush=True)
