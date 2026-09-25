"""Compact gradient-reversal encoder for Phase 4 I4."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn


class _GradientReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx, values: torch.Tensor, strength: float) -> torch.Tensor:
        ctx.strength = strength
        return values.view_as(values)

    @staticmethod
    def backward(ctx, gradient: torch.Tensor) -> tuple[torch.Tensor, None]:
        return -ctx.strength * gradient, None


class AdversarialEncoder(nn.Module):
    def __init__(self, inputs: int, hidden: int, latent: int, identities: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(inputs, hidden), nn.ReLU(), nn.Linear(hidden, latent))
        self.task_head = nn.Linear(latent, 1)
        self.identity_head = nn.Linear(latent, identities)

    def forward(self, values: torch.Tensor, identity_strength: float) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        representation = self.encoder(values)
        task = self.task_head(representation).squeeze(1)
        reversed_representation = _GradientReverse.apply(representation, identity_strength)
        identity = self.identity_head(reversed_representation)
        return task, identity, representation


@dataclass
class TrainedAdversarial:
    model: AdversarialEncoder
    target_mean: float
    target_sd: float
    identity_classes: np.ndarray

    def predict(self, values: np.ndarray) -> np.ndarray:
        self.model.eval()
        with torch.no_grad():
            tensor = torch.as_tensor(values, dtype=torch.float32)
            prediction, _, _ = self.model(tensor, 0.0)
        return prediction.numpy().astype(float) * self.target_sd + self.target_mean

    def encode(self, values: np.ndarray) -> np.ndarray:
        self.model.eval()
        with torch.no_grad():
            tensor = torch.as_tensor(values, dtype=torch.float32)
            _, _, representation = self.model(tensor, 0.0)
        return representation.numpy().astype(float)

    def training_identity_accuracy(self, values: np.ndarray, identities: np.ndarray) -> float:
        self.model.eval()
        with torch.no_grad():
            tensor = torch.as_tensor(values, dtype=torch.float32)
            _, logits, _ = self.model(tensor, 0.0)
            prediction = logits.argmax(dim=1).numpy()
        index = {label: position for position, label in enumerate(self.identity_classes)}
        truth = np.array([index[str(label)] for label in identities])
        return float(np.mean(prediction == truth))


def train_adversarial(
    values: np.ndarray,
    target: np.ndarray,
    identities: np.ndarray,
    *,
    identity_strength: float,
    seed: int,
    hidden: int,
    latent: int,
    epochs: int,
    learning_rate: float,
    weight_decay: float,
) -> TrainedAdversarial:
    torch.manual_seed(int(seed))
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    values_tensor = torch.as_tensor(values, dtype=torch.float32)
    target = np.asarray(target, dtype=float)
    target_mean = float(np.mean(target))
    target_sd = float(np.std(target)) or 1.0
    target_tensor = torch.as_tensor((target - target_mean) / target_sd, dtype=torch.float32)
    identity_classes = np.array(sorted(np.unique(identities).astype(str)))
    identity_index = {label: index for index, label in enumerate(identity_classes)}
    identity_tensor = torch.as_tensor([identity_index[str(label)] for label in identities], dtype=torch.long)

    model = AdversarialEncoder(values.shape[1], hidden, latent, len(identity_classes))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    task_loss = nn.MSELoss()
    identity_loss = nn.CrossEntropyLoss()
    model.train()
    for _ in range(int(epochs)):
        optimizer.zero_grad(set_to_none=True)
        task_prediction, identity_prediction, _ = model(values_tensor, float(identity_strength))
        loss = task_loss(task_prediction, target_tensor) + identity_loss(identity_prediction, identity_tensor)
        loss.backward()
        optimizer.step()
    return TrainedAdversarial(model, target_mean, target_sd, identity_classes)
