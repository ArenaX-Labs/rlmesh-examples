import numpy as np


class RLMeshVLAWrapper:
    def __init__(self, model, *, action_low=-1.0, action_high=1.0):
        self._model = model
        self._low = np.float32(action_low)
        self._high = np.float32(action_high)
        self._chunk = None
        self._cursor = 0

    def predict(self, observation):
        if self._chunk is None or self._cursor >= len(self._chunk):
            self._chunk = self._model.predict_chunk(
                observation["image"], observation["instruction"], observation["state"]
            )
            self._cursor = 0
        action = self._chunk[self._cursor]
        self._cursor += 1
        return self._rescale(action)

    def reset(self):
        self._chunk = None
        self._cursor = 0

    def _rescale(self, action):
        unit = (np.asarray(action, dtype=np.float32) + 1.0) / 2.0
        return (self._low + unit * (self._high - self._low)).astype(np.float32)
