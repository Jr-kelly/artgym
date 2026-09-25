"""Choose one actor evaluation; privileged latent mixing is training-only."""


def teacher_mix_fraction(update_index, initial_fraction, decay_updates):
    if not 0.0 <= initial_fraction <= 1.0 or decay_updates < 0 or update_index < 0:
        raise ValueError('Invalid teacher latent mixing schedule')
    if initial_fraction == 0.0:
        return 0.0
    if decay_updates == 0:
        raise ValueError('A positive initial fraction requires a finite decay duration')
    return initial_fraction * max(0.0, 1.0 - update_index / decay_updates)


def distillation_action(player, observations, student_observations, teacher_encoder,
                        use_teacher, deterministic, student_eval_mode=False,
                        teacher_fraction=0.0, teacher_latent=None):
    if not 0.0 <= teacher_fraction <= 1.0:
        raise ValueError('Teacher fraction must lie in [0, 1]')
    if teacher_fraction and (use_teacher or teacher_latent is None):
        raise ValueError('Mixed rollout needs an explicit detached teacher latent and student path')
    network = player.model.a2c_network
    student_encoder = network.priv_encoder
    previous_override = network.actor_encoder_obs_override
    previous_fraction = getattr(network, '_distillation_teacher_fraction', None)
    mixture_hook = None
    student_modes = [(module, module.training) for module in student_encoder.modules()]
    try:
        network._distillation_teacher_fraction = teacher_fraction
        if use_teacher:
            # The normal model path normalizes privileged observations once.
            network.priv_encoder = teacher_encoder
            network.actor_encoder_obs_override = None
        else:
            network.actor_encoder_obs_override = student_observations
            if student_eval_mode:
                student_encoder.eval()
            if teacher_fraction:
                target = teacher_latent.detach()

                def mix_latent(module, inputs, predicted):
                    if predicted.shape != target.shape:
                        raise ValueError('Teacher/student latent shapes differ')
                    if teacher_fraction == 1.0:
                        return target
                    return (1.0 - teacher_fraction) * predicted + teacher_fraction * target

                mixture_hook = student_encoder.register_forward_hook(mix_latent)
        # Advance the actor RNN exactly once, using the policy driving physics.
        return player.get_action(observations, is_deterministic=deterministic)
    finally:
        if mixture_hook is not None:
            mixture_hook.remove()
        if previous_fraction is None:
            delattr(network, '_distillation_teacher_fraction')
        else:
            network._distillation_teacher_fraction = previous_fraction
        network.priv_encoder = student_encoder
        network.actor_encoder_obs_override = previous_override
        for module, training in student_modes:
            module.training = training
