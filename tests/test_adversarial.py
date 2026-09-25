import numpy as np
import torch

from surgical_skill2.adversarial import _GradientReverse, train_adversarial


def test_gradient_reversal_has_documented_sign_and_strength():
    values = torch.tensor([1.0, -2.0], requires_grad=True)
    (_GradientReverse.apply(values, 0.3).sum()).backward()
    np.testing.assert_allclose(values.grad.numpy(), [-0.3, -0.3])


def test_adversarial_training_is_reproducible_at_fixed_seed():
    rng = np.random.default_rng(4)
    values = rng.normal(size=(20, 4))
    target = values[:, 0] - values[:, 1]
    identity = np.array(["a", "b"] * 10)
    kwargs = dict(identity_strength=0.1, seed=9, hidden=6, latent=3, epochs=10, learning_rate=0.01, weight_decay=0.0)
    first = train_adversarial(values, target, identity, **kwargs)
    second = train_adversarial(values, target, identity, **kwargs)
    np.testing.assert_array_equal(first.predict(values), second.predict(values))
    np.testing.assert_array_equal(first.encode(values), second.encode(values))
