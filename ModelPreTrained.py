# pytorch

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import pretrainedmodels

class KeypointPretrainedModel(nn.Module):
    def __init__(self, args):
        super(KeypointPretrainedModel, self).__init__()

        #self.model = torchvision.models.vgg16() # loads model architecture with random weights
        #self.model = torchvision.models.vgg16(pretrained = True) # loads model architecture with pretrained weights
        #self.model = torchvision.models.vgg16_bn(pretrained = True) # loads model architecture (with batch norm) with pretrained weights
        self.model = torchvision.models.resnet18(pretrained = True)
        #self.model = pretrainedmodels.__dict__['resnet18'](pretrained='imagenet')
        
        #for param in self.model.parameters(): # Freeze model weights (remove to unfreeze all weights)
        #    param.requires_grad = False
        
        # Change input to 1 channel (changes requires_grad to False automatically)
        self.model.conv1 = nn.Conv2d(1, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False) 
        
        self.model.features = nn.Sequential(*(list(self.model.children())[0:9]))
        self.features = nn.Sequential(*(list(self.model.children())[0:9]))

        numFeatures = self.model.fc.in_features
        self.fc = nn.Linear(numFeatures, 6) # change depending on where importing model from
        
    def forward(self, x):
        batch, _, _, _ = x.shape
        x = self.features(x)
        #x = x.view(x.size(0), -1)
        x = F.adaptive_avg_pool2d(x, 1).reshape(batch, -1)
        out = self.fc(x)
        
        return out
