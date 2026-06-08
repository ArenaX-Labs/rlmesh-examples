import os

import numpy as np


class Recorder:
    def __init__(self, path="videos/rollout.mp4", fps=30):
        import imageio.v2 as imageio

        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._writer = imageio.get_writer(path, fps=fps, macro_block_size=None)
        self._path = path

    def add(self, image):
        self._writer.append_data(np.asarray(image, dtype="uint8"))

    def close(self):
        self._writer.close()
        print(f"[agent] wrote {self._path}", flush=True)
