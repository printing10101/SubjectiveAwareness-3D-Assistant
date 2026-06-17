import os
import sys

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Import unsloth FIRST before any other ML libraries
import unsloth
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from train_lora import train

train()
