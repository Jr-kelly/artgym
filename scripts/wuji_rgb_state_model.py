"""A camera/proprioception state estimator; no current object truth is an input."""
import torch
from torch import nn

OUTPUT_SCALES=(.001,.001,.001,.02,.02,.02,.0005)


class RGBStateModel(nn.Module):
    def __init__(self,mean,scale):
        super().__init__()
        self.register_buffer('feature_mean',torch.as_tensor(mean).float().clone())
        self.register_buffer('feature_scale',torch.as_tensor(scale).float().clone())
        assert self.feature_mean.shape==self.feature_scale.shape==(96,)
        self.camera=nn.Sequential(nn.Conv2d(3,16,5,2,2),nn.ELU(),
            nn.Conv2d(16,32,3,2,1),nn.ELU(),nn.Conv2d(32,64,3,2,1),nn.ELU(),
            nn.Conv2d(64,64,3,2,1),nn.ELU(),nn.AdaptiveAvgPool2d((10,10)),
            nn.Flatten(),nn.Linear(6400,256),nn.ELU())
        self.head=nn.Sequential(nn.Linear(352,256),nn.ELU(),nn.Linear(256,7))
        nn.init.zeros_(self.head[-1].weight);nn.init.zeros_(self.head[-1].bias)

    def forward(self,image,features,mask_image=False):
        assert image.shape[1:]==(3,320,320) and features.shape[-1]==96
        if mask_image:image=torch.zeros_like(image)
        observable=((features-self.feature_mean)/self.feature_scale).clamp(-10,10)
        return self.head(torch.cat([self.camera(image),observable],-1))
