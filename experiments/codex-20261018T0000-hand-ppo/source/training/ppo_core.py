"""Small explicit PPO implementation for bounded carrying residuals.

Gaussian latent actions are squashed to physical residuals by the environment.
PPO ratios use latent log probabilities consistently; the transform is fixed.
"""
import torch
from torch import nn
from torch.distributions import Normal


class ResidualActorCritic(nn.Module):
    def __init__(self,observation_dim=89,action_dim=20):
        super().__init__()
        self.actor=nn.Sequential(nn.Linear(observation_dim,128),nn.ELU(),nn.Linear(128,128),nn.ELU(),nn.Linear(128,action_dim))
        self.critic=nn.Sequential(nn.Linear(observation_dim,128),nn.ELU(),nn.Linear(128,128),nn.ELU(),nn.Linear(128,1))
        nn.init.zeros_(self.actor[-1].weight);nn.init.zeros_(self.actor[-1].bias)
        self.log_std=nn.Parameter(torch.full((action_dim,),-1.9))

    def distribution(self,obs):
        return Normal(self.actor(obs),self.log_std.clamp(-4,0).exp())

    def value(self,obs):
        return self.critic(obs).squeeze(-1)

    def sample(self,obs):
        dist=self.distribution(obs);action=dist.sample()
        return action,dist.log_prob(action).sum(-1),self.value(obs)


def advantages(rewards,values,next_values,terminated,done,gamma=.99,lam=.95):
    """Bootstrap time limits, but never carry advantage across episode resets."""
    output=torch.zeros_like(rewards);carry=torch.zeros_like(rewards[0])
    for t in reversed(range(len(rewards))):
        delta=rewards[t]+gamma*next_values[t]*(~terminated[t])-values[t]
        carry=delta+gamma*lam*(~done[t])*carry
        output[t]=carry
    return output,output+values


def update(model,optimizer,observations,actions,old_logprob,returns,advantage,epochs=4,minibatch=512):
    flat=lambda x:x.flatten(0,1)
    observations,actions,old_logprob,returns,advantage=map(flat,(observations,actions,old_logprob,returns,advantage))
    advantage=(advantage-advantage.mean())/(advantage.std(unbiased=False)+1e-8)
    stats=[];updates=0
    for _ in range(epochs):
        for ids in torch.randperm(len(observations),device=observations.device).split(minibatch):
            dist=model.distribution(observations[ids]);lp=dist.log_prob(actions[ids]).sum(-1)
            ratio=(lp-old_logprob[ids]).exp()
            policy=-torch.minimum(ratio*advantage[ids],ratio.clamp(.8,1.2)*advantage[ids]).mean()
            value=.5*(model.value(observations[ids])-returns[ids]).square().mean()
            entropy=dist.entropy().sum(-1).mean()
            loss=policy+value-.001*entropy
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite PPO loss')
            optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step()
            stats.append([float(policy.detach()),float(value.detach()),float(entropy.detach())]);updates+=1
    return {'optimizer_steps':updates,'loss_means':torch.tensor(stats).mean(0).tolist()}
