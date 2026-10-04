"""Adapt four thumb outputs while retaining the functional support mapping."""
import torch


def optimizer(model, thumb_learning_rate=3e-5):
    assert 1e-6<=thumb_learning_rate<=3e-4
    for layer in list(model.actor.children())[:-1]:
        for parameter in layer.parameters():parameter.requires_grad_(False)
    for parameter in [model.actor[-1].weight,model.actor[-1].bias,model.logstd]:
        mask=torch.zeros_like(parameter);mask[16:]=1
        parameter.register_hook(lambda gradient,mask=mask:gradient*mask)
    return torch.optim.Adam([
        dict(params=list(model.actor[-1].parameters())+[model.logstd],lr=thumb_learning_rate),
        dict(params=list(model.critic.parameters()),lr=3e-4)],eps=1e-5)


def support_snapshot(model):
    result={name:p.detach().clone() for name,p in model.actor.named_parameters()
            if not name.startswith(str(len(model.actor)-1)+'.')}
    result.update(output_weight=model.actor[-1].weight[:16].detach().clone(),
                  output_bias=model.actor[-1].bias[:16].detach().clone(),
                  support_logstd=model.logstd[:16].detach().clone())
    return result


def check_support_unchanged(model, initial):
    now=support_snapshot(model)
    assert all(torch.equal(now[k],v) for k,v in initial.items()),'Fixed functional support mapping changed'
