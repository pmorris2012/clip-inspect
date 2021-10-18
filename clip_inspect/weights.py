from collections import OrderedDict
from typing import Tuple, Union
from pathlib import Path

import numpy as np
import torch
import jax.numpy as jnp
import haiku as hk


def model_info(state_dict: dict):
    vit = "visual.proj" in state_dict

    info = {}

    if vit:
        info['vision_width'] = state_dict["visual.conv1.weight"].shape[0]
        info['vision_layers'] = len([k for k in state_dict.keys() if k.startswith("visual.") and k.endswith(".attn.in_proj_weight")])
        info['vision_patch_size'] = state_dict["visual.conv1.weight"].shape[-1]
        info['grid_size'] = round((state_dict["visual.positional_embedding"].shape[0] - 1) ** 0.5)
        info['image_resolution'] = info['vision_patch_size'] * info['grid_size']
    else:
        counts = [len(set(k.split(".")[2] for k in state_dict if k.startswith(f"visual.layer{b}"))) for b in [1, 2, 3, 4]]
        info['vision_layers'] = tuple(counts)
        info['vision_width'] = state_dict["visual.layer1.0.conv1.weight"].shape[0]
        info['output_width'] = round((state_dict["visual.attnpool.positional_embedding"].shape[0] - 1) ** 0.5)
        info['vision_patch_size'] = None
        assert output_width ** 2 + 1 == state_dict["visual.attnpool.positional_embedding"].shape[0]
        info['image_resolution'] = info['output_width'] * 32

    info['embed_dim'] = state_dict["text_projection"].shape[1]
    info['context_length'] = state_dict["positional_embedding"].shape[0]
    info['vocab_size'] = state_dict["token_embedding.weight"].shape[0]
    info['transformer_width'] = state_dict["ln_final.weight"].shape[0]
    info['transformer_heads'] = info['transformer_width'] // 64
    info['transformer_layers'] = len(set(k.split(".")[2] for k in state_dict if k.startswith(f"transformer.resblocks")))

    return info


def clean_state_dict(state_dict: dict):
    for key in ["input_resolution", "context_length", "vocab_size"]:
        if key in state_dict:
            del state_dict[key]
    return state_dict


def load(model_name, base_path="/clip-inspect/weights/"):
    path = Path(base_path, F"{Path(model_name).stem}.pt")
    state_dict = torch.jit.load(path, map_location="cpu").eval().state_dict()
    
    info_dict = model_info(state_dict)
    state_dict = clean_state_dict(state_dict)

    return state_dict, info_dict
