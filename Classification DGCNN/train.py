# -*- coding: utf-8 -*-
"""Train.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1UBosPRy0pEg3TPT9AkmKjmNZ_C9SuBgj
"""

!pip install tensorboard

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import os
import matplotlib.pyplot as plt


writer = SummaryWriter(log_dir = log_dir)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

checkpoint_path = MODEL_SAVE_PATH

train_dataset = VascularDataset(data_root=folder_path, category='aorta', point_number=512, split='train')
val_dataset = VascularDataset(data_root=folder_path, category='aorta', point_number=512, split='val')
test_dataset = VascularDataset(data_root=folder_path, category='aorta', point_number=512, split='test')

train_dataloader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=2)
val_dataloader = DataLoader(val_dataset, batch_size=32, shuffle=False, num_workers=2)
test_dataloader = DataLoader(test_dataset, batch_size=32, shuffle=False, num_workers=2)

model = DGCNN().to(device)

criterion1 = nn.MSELoss()


optimizer = optim.Adam(model.parameters(), lr=0.001)

start_epoch = 0
resume = True

if resume and os.path.exists(checkpoint_path):
    print(f"Resuming training from checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    start_epoch = checkpoint["epoch"] + 1
    print(f"Resumed training from epoch {start_epoch}")


# TRAINING
num_epochs = 50
for epoch in range(start_epoch, num_epochs):
    model.train()
    running_loss1 = 0.0
    running_total_loss = 0.0

    with tqdm(total=len(train_dataloader), desc=f'Epoch [{epoch+1}/{num_epochs}]', unit='batch') as pbar:
        for step, batch in enumerate(train_dataloader):
            coordinates = batch['coord'].to(torch.float32).to(device)
            segments = batch['segment'].to(torch.float32).to(device).transpose(1, 2)
            time_steps = batch['time'].to(torch.float32).to(device)

            inputs = torch.cat((coordinates, time_steps), dim=2).transpose(1, 2)

            optimizer.zero_grad()
            outputs = model(inputs)

            loss1 = criterion1(outputs, segments)
            loss = loss1

            loss.backward()
            optimizer.step()

            running_loss1 += loss1.item()
            running_total_loss += loss.item()

            pbar.set_postfix(loss1=running_loss1 / (pbar.n + 1),
                             total_loss=running_total_loss / (pbar.n + 1))
            pbar.update(1)

            writer.add_scalar("Loss/train_loss1", loss1.item(), step + epoch * len(train_dataloader))
            writer.add_scalar("Loss/total_loss", loss.item(), step + epoch * len(train_dataloader))

    epoch_loss1 = running_loss1 / len(train_dataloader)
    epoch_total_loss = running_total_loss / len(train_dataloader)

    print(f'Epoch [{epoch+1}/{num_epochs}], Loss1: {epoch_loss1:.4f},Total Loss: {epoch_total_loss:.4f}')

    writer.add_scalar("Loss/train_loss1", epoch_loss1, epoch)
    writer.add_scalar("Loss/total_loss", epoch_total_loss, epoch)

    # VALIDATION
    model.eval()
    val_loss1 = 0.0
    val_total_loss = 0.0

    with torch.no_grad():
        for batch in val_dataloader:
            coordinates = batch['coord'].to(torch.float32).to(device)
            segments = batch['segment'].to(torch.float32).to(device).transpose(1, 2)
            time_steps = batch['time'].to(torch.float32).to(device)

            inputs = torch.cat((coordinates, time_steps), dim=2).transpose(1, 2)

            outputs = model(inputs)

            loss1 = criterion1(outputs, segments)
            loss = loss1

            val_loss1 += loss1.item()
            val_total_loss += loss.item()

    avg_val_loss1 = val_loss1 / len(val_dataloader)
    avg_val_total_loss = val_total_loss / len(val_dataloader)

    print(f'Validation Loss1: {avg_val_loss1:.4f}, Total Loss: {avg_val_total_loss:.4f}')

    writer.add_scalar("Loss/val_loss1", avg_val_loss1, epoch)
    writer.add_scalar("Loss/val_total_loss", avg_val_total_loss, epoch)

    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
    }
    torch.save(checkpoint, checkpoint_path)
    print(f"Checkpoint saved at epoch {epoch+1}")

writer.close()
print("Training complete!")

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
# %tensorboard --logdir=runs