# -*- coding: utf-8 -*-
"""Segmentation DGCNN Model.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1OnYmOaOQyGQT5dVYAiWHlavcnsaP7E2W
"""

import torch
import torch as t
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F
import numpy as np


def knn(x, k):
    inner = -2 * t.matmul(x.transpose(2, 1), x)
    xx = t.sum(x ** 2, dim=1, keepdim=True)
    pairwise_distance = -xx - inner - xx.transpose(2, 1)

    idx = pairwise_distance.topk(k=k, dim=-1)[1]  # (batch_size, num_points, k)
    return idx


def get_graph_feature(x, k=20, idx=None):
    batch_size = x.size(0)
    num_points = x.size(2)
    x = x.view(batch_size, -1, num_points)
    if idx is None:
        idx = knn(x, k=k)  # (batch_size, num_points, k)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    idx_base = t.arange(0, batch_size, device=device).view(-1, 1, 1) * num_points

    idx = idx + idx_base

    idx = idx.view(-1)

    _, num_dims, _ = x.size()

    x = x.transpose(2,
                    1).contiguous()  # (batch_size, num_points, num_dims)  -> (batch_size*num_points, num_dims) #   batch_size * num_points * k + range(0, batch_size*num_points)
    feature = x.view(batch_size * num_points, -1)[idx, :]
    feature = feature.view(batch_size, num_points, k, num_dims)
    x = x.view(batch_size, num_points, 1, num_dims).repeat(1, 1, k, 1)

    feature = t.cat((feature - x, x), dim=3).permute(0, 3, 1, 2)

    return feature


class DGCNN(nn.Module):
  def __init__(self, emb_dims=512, k=20, dropout=0.5, in_channels=8, out_channels=4):
        super(DGCNN, self).__init__()
        self.emb_dims = emb_dims
        self.out_channels = out_channels
        self.k = k
        self.dropout = dropout
        self.in_channels = in_channels

        self.bn1 = nn.BatchNorm2d(64)
        self.bn2 = nn.BatchNorm2d(64)
        self.bn3 = nn.BatchNorm2d(64)
        self.bn4 = nn.BatchNorm2d(64)
        self.bn5 = nn.BatchNorm2d(64)
        self.bn6 = nn.BatchNorm1d(self.emb_dims)
        self.bn7 = nn.BatchNorm1d(64)
        self.bn8 = nn.BatchNorm1d(256)
        self.bn9 = nn.BatchNorm1d(256)
        self.bn10 = nn.BatchNorm1d(128)

        self.conv1 = nn.Sequential(nn.Conv2d(self.in_channels, 64, kernel_size=1, bias=False),
                                   self.bn1,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.conv2 = nn.Sequential(nn.Conv2d(64, 64, kernel_size=1, bias=False),
                                   self.bn2,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.conv3 = nn.Sequential(nn.Conv2d(64 * 2, 64, kernel_size=1, bias=False),
                                   self.bn3,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.conv4 = nn.Sequential(nn.Conv2d(64, 64, kernel_size=1, bias=False),
                                   self.bn4,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.conv5 = nn.Sequential(nn.Conv2d(64 * 2, 64, kernel_size=1, bias=False),
                                   self.bn5,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.conv6 = nn.Sequential(nn.Conv1d(192, self.emb_dims, kernel_size=1, bias=False),
                                   self.bn6,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.conv7 = nn.Sequential(nn.Conv1d(16, 64, kernel_size=1, bias=False),
                                   self.bn7,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.conv8 = nn.Sequential(nn.Conv1d(2240, 256, kernel_size=1, bias=False),
                                   self.bn8,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.dp1 = nn.Dropout(p=self.dropout)
        self.conv9 = nn.Sequential(nn.Conv1d(256, 256, kernel_size=1, bias=False),
                                   self.bn9,
                                   nn.LeakyReLU(negative_slope=0.2))
        self.dp2 = nn.Dropout(p=self.dropout)
        self.conv10 = nn.Sequential(nn.Conv1d(256, 128, kernel_size=1, bias=False),
                                    self.bn10,
                                    nn.LeakyReLU(negative_slope=0.2))
        self.conv11 = nn.Conv1d(128, self.out_channels, kernel_size=1, bias=False)

  def forward(self, x):
      batch_size = x.size(0)
      num_points = x.size(2)


      x = get_graph_feature(x, k=self.k)
      x = self.conv1(x)
      x = self.conv2(x)
      x1 = x.max(dim=-1, keepdim=False)[0]

      x = get_graph_feature(x1, k=self.k)
      x = self.conv3(x)
      x = self.conv4(x)
      x2 = x.max(dim=-1, keepdim=False)[0]

      x = get_graph_feature(x2, k=self.k)
      x = self.conv5(x)
      x3 = x.max(dim=-1, keepdim=False)[0]

      x = torch.cat((x1, x2, x3), dim=1)

      x = self.conv6(x)
      x = x.max(dim=-1, keepdim=True)[0]

      x = x.repeat(1, 1, num_points)

      x = torch.cat((x, x1, x2, x3), dim=1)

      x = self.conv8(x)
      x = self.dp1(x)
      x = self.conv9(x)
      x = self.dp2(x)
      x = self.conv10(x)
      x = self.conv11(x)

      return x