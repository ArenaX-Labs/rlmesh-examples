import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

IMAGE_SIZE = 224
CHUNK = 8
TEXT_VOCAB = 256
STATE_DIM = 44
ACTION_DIM = 5


class _InstructionEncoder(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self._embed = nn.Embedding(TEXT_VOCAB, dim)

    def forward(self, instruction):
        codes = [min(ord(char), TEXT_VOCAB - 1) for char in instruction] or [0]
        tokens = torch.tensor(codes, dtype=torch.long)
        return self._embed(tokens).mean(dim=0, keepdim=True)


class _VisionLanguageActionNet(nn.Module):
    def __init__(self, state_dim, action_dim, dim=128):
        super().__init__()
        self._vision = nn.Sequential(
            nn.Conv2d(3, 16, 5, stride=3),
            nn.ReLU(),
            nn.Conv2d(16, 32, 5, stride=3),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(32, dim),
            nn.ReLU(),
        )
        self._instruction = _InstructionEncoder(dim)
        self._state = nn.Sequential(nn.Linear(state_dim, dim), nn.ReLU())
        self._head = nn.Sequential(
            nn.Linear(dim * 3, dim),
            nn.ReLU(),
            nn.Linear(dim, CHUNK * action_dim),
        )
        self._action_dim = action_dim

    def forward(self, image, state, instruction):
        fused = torch.cat(
            [self._vision(image), self._instruction(instruction), self._state(state)],
            dim=-1,
        )
        return torch.tanh(self._head(fused).view(CHUNK, self._action_dim))


class VLAModel:
    def __init__(self, state_dim=STATE_DIM, action_dim=ACTION_DIM, *, seed=0):
        self._state_dim = state_dim
        self._action_dim = action_dim
        self._seed = seed
        self._net = None

    def load(self):
        torch.manual_seed(self._seed)
        self._net = _VisionLanguageActionNet(self._state_dim, self._action_dim).eval()

    def predict_chunk(self, image, instruction, state):
        pixels = self._pixels(image)
        proprio = torch.from_numpy(np.array(state, dtype=np.float32)).unsqueeze(0)
        with torch.no_grad():
            chunk = self._net(pixels, proprio, instruction)
        return chunk.numpy().astype(np.float32)

    def close(self):
        self._net = None

    def _pixels(self, image):
        array = np.asarray(image, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
        return F.interpolate(
            tensor, size=IMAGE_SIZE, mode="bilinear", align_corners=False
        )
