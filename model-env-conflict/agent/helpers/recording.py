import os


class Recorder:
    def __init__(self, envs, out_dir="videos"):
        import imageio.v2 as imageio
        import numpy as np

        self._np = np
        os.makedirs(out_dir, exist_ok=True)
        self._paths = {}
        self._writers = {}
        for name, env in envs.items():
            fps = int(env.metadata.get("render_fps", 30))
            path = os.path.join(out_dir, name.replace("/", "-") + ".mp4")
            self._paths[name] = path
            self._writers[name] = imageio.get_writer(
                path, fps=fps, macro_block_size=None
            )

    def add(self, name, env):
        frame = env.render()
        if frame is not None:
            self._writers[name].append_data(self._np.asarray(frame, dtype="uint8"))

    def close(self):
        for name, writer in self._writers.items():
            writer.close()
            print(f"wrote {self._paths[name]}")
