"""FIFO of student-induced observations and frozen teacher labels.

Only supervised training reads this buffer. Sampling and extra dropout use
private random streams, leaving the environment/action RNG stream untouched.
"""
from contextlib import contextmanager

import torch


class LatentReplay:
    def __init__(self, capacity, observation_dim, latent_dim, device, seed):
        self.capacity = int(capacity)
        if self.capacity <= 0:
            raise ValueError('Replay capacity must be positive')
        self.device = torch.device(device)
        self.observations = torch.empty((capacity, observation_dim), device=device)
        self.labels = torch.empty((capacity, latent_dim), device=device)
        self.steps = torch.empty(capacity, dtype=torch.int64, device=device)
        self.generator = torch.Generator(device=device).manual_seed(seed)
        self.dropout_generator = torch.Generator(device=device).manual_seed(seed + 1)
        self.position = self.size = self.writes = self.samples = 0
        self.age_sum = self.age_max = 0
        self.older_than_60 = self.older_than_150 = 0

    @torch.no_grad()
    def append(self, observations, labels, step):
        count = len(observations)
        if count > self.capacity or labels.shape != (count, self.labels.shape[1]):
            raise ValueError('Batch does not fit the replay buffer')
        indices = (torch.arange(count, device=self.device) + self.position) % self.capacity
        self.observations[indices] = observations.detach()
        self.labels[indices] = labels.detach()
        self.steps[indices] = step
        self.position = (self.position + count) % self.capacity
        self.size = min(self.size + count, self.capacity)
        self.writes += count

    @torch.no_grad()
    def sample(self, count, current_step):
        if not self.size:
            raise ValueError('Cannot sample an empty replay buffer')
        ids = torch.randint(self.size, (count,), device=self.device, generator=self.generator)
        ages = current_step - self.steps[ids]
        assert (ages > 0).all(), 'Replay must contain past transitions only'
        self.samples += count
        self.age_sum += int(ages.sum())
        self.age_max = max(self.age_max, int(ages.max()))
        self.older_than_60 += int((ages > 60).sum())
        self.older_than_150 += int((ages > 150).sum())
        return self.observations[ids], self.labels[ids]

    @contextmanager
    def dropout_stream(self):
        devices = [self.device.index or 0] if self.device.type == 'cuda' else []
        with torch.random.fork_rng(devices=devices):
            if self.device.type == 'cuda':
                torch.cuda.set_rng_state(self.dropout_generator.get_state(), self.device)
            else:
                torch.set_rng_state(self.dropout_generator.get_state())
            try:
                yield
            finally:
                state = (torch.cuda.get_rng_state(self.device) if self.device.type == 'cuda'
                         else torch.get_rng_state())
                self.dropout_generator.set_state(state)

    def report(self):
        return dict(capacity=self.capacity, size=self.size, position=self.position,
                    writes=self.writes, sampled_transitions=self.samples,
                    mean_sample_age_steps=self.age_sum / max(1, self.samples),
                    maximum_sample_age_steps=self.age_max,
                    samples_older_than_60_steps=self.older_than_60,
                    samples_older_than_150_steps=self.older_than_150,
                    dtype=str(self.observations.dtype), private_rng=True,
                    bytes_allocated=sum(x.numel() * x.element_size() for x in
                                        [self.observations, self.labels, self.steps]))
