# Install Guide

## 1. Prerequisites

Recommended:

- Linux
- RTX4090
- Python `3.8`


## 2. Create A Conda Environment

```bash
conda create -n artgym python=3.8 -y
conda activate artgym
```
## 3. Install Pytorch

```bash
pip install torch==2.1.0+cu118 torchvision==0.16.0+cu118 torchaudio==2.1.0+cu118 \
  --index-url https://download.pytorch.org/whl/cu118
```
if you are using RTX 50s GPU, you need to install pytorch+cu12.x compatible with isaacgym.

## 3. Install Isaac Gym

This repo uses IsaacGym_TacSL, install it as follows:

```bash
pip install gdown && \
gdown 1nhLF4cKeUokCqU5LvEu8uYdEQtyJolXl && \
tar zxvf IsaacGym_Preview_TacSL_Package.tar.gz && \
pip install -e ./IsaacGym_Preview_TacSL_Package/isaacgym/python
```

## 4. Install Python Packages Used By This Repo

Install the core runtime packages:

```bash
pip install \
  gymnasium \
  numpy \
  scipy \
  matplotlib \
  imageio \
  hydra-core \
  omegaconf \
  gym \
  tensorboard \
  tensorboardX \
  pyyaml \
  psutil \
  setproctitle \
  opencv-python \
  wandb \
  pyvirtualdisplay \
  imageio[ffmpeg]
```

## 5. Install The Local `rl_games`

This workspace includes a local fork:

```text
rl_games/
```

Install it in editable mode:

```bash
pip install -e ./rl_games
```

## Prepared H100 development environment

The four-H100 host `ssh -p 30296 wangjiarui@10.14.0.73` has an isolated runtime
under `/home/wangjiarui/artgym-runtime`, with Python 3.8.20, PyTorch 2.1.0+cu121,
NumPy 1.23.5 and Isaac Gym TacSL. From `/home/wangjiarui/artgym`, activate it with:

```bash
source scripts/activate_wuji_runtime.sh
python -m pip check
python -m scripts.run_wuji_paper_pipeline --fingertip-filter --gpus 4 \
  --run-dir runs/wuji_knife_fingertip_4gpu --dry-run
```

This host uses the CUDA 12.1 build of the same PyTorch release because its
internal package mirror is reachable. Exact deployed versions and setup scripts
are recorded in `transfer/environment/h100-installed.txt` and `transfer/`.
`ARTGYM_RUNTIME_DIR` can override the runtime location. Isaac Gym must be imported
before PyTorch in simulation programs. See `paper_reproduction.md` for actual
four-GPU validation, sample budgets and checkpoint continuation rules.
