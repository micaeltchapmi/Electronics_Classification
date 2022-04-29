# pytorch
# Baselines: 1 hidden layer NN | 5 layer CNN
# 

import torch
import torch.nn as nn
import torch.nn.functional as F

class KeypointModel(nn.Module):
    def __init__(self):
        super(KeypointModel, self).__init__()
        self.conv1 = nn.Conv2d(1, 6, kernel_size=5) # takes in 1 input image channel
        self.conv2 = nn.Conv2d(6, 16, kernel_size=3)

        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 6) #output is # of coordinates (3 keypoints)

        self.pool = nn.MaxPool2d(2, 2)

        
    def forward(self, x):
         x = F.relu(self.conv1(x))
         x = self.pool(x)
         x = F.relu(self.conv2(x))
         x = self.pool(x)
         x = torch.flatten(x, 1) # Flatten all dims except batch dimension

         x = F.relu(self.fc1(x))
         x = F.relu(self.fc2(x))
         out = self.fc3(x) 
         
         return out
