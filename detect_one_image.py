import argparse
import glob
import os

import numpy as np
import torch

from src.masksim import MaskSim
from src.dataset import MaskSimDataset


CLASS_NAMES = [
    "sd1",
    "sd2",
    "sdxl",
    "dalle2",
    "dalle3",
    "midjourney",
    "firefly",
]
IMG_SIZE = 512

ROOT = os.path.dirname(os.path.realpath(__file__))


def detect_one_image(fname: str,
                     compress_Q: int):
    if compress_Q < 0:
        comp_or_uncomp = "uncompress"
    else:
        comp_or_uncomp = f"compress_Q{compress_Q}"

    device = torch.device("cpu")

    # 1. load model
    train_models = dict()
    for class_name in CLASS_NAMES:
        ckpt_fpattern = os.path.join(ROOT, f"checkpoints/{comp_or_uncomp}/{class_name}" + "*.ckpt")
        print("ckpt_fpattern:", ckpt_fpattern)
        ckpt_fnames = glob.glob(ckpt_fpattern)
        ckpt_fnames.sort(key=os.path.getctime)
        ckpt_fname = ckpt_fnames[-1]

        model = MaskSim.load_from_checkpoint(ckpt_fname, map_location=device).float()
        model.eval()
        train_models[class_name] = model

    # 2. process image
    dataset = MaskSimDataset(img_dir_real_list=[], img_dir_fake_list=[], img_size=IMG_SIZE,
                             channels=3, color_space="RGB", mode="test")

    imgs = dataset.process(fname, label=None)
    
    # 3. compute scores
    scores_all = []
    with torch.no_grad():
        for class_name in CLASS_NAMES:
            model: MaskSim = train_models[class_name]
            scores : torch.Tensor = model.compute_probs(imgs)
            scores_all.append(scores.detach().cpu().numpy())
    
    score_final = np.concatenate(scores_all).max()
    print("score final:", score_final)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='python detect_one_image.py',
        description='MaskSim: Detection of synthetic images by masked spectrum similarity analysis. (c) 2024 Yanhao Li. Under license GNU AGPL.'
    )

    parser.add_argument('-i', '--img_filename', type=str, required=True,
                        help='tested image file name')
    parser.add_argument('-c', '--compress_rate', type=int, required=False,
                        help='the JPEG compression quality factor', choices=[-1, 90, 80, 70], default=-1)
    args = parser.parse_args()

    fname = args.img_filename
    compress_Q = args.compress_rate

    if compress_Q < 0:
        print("Loading model weights for detecting uncompressed images. \n")
    else:
        print("Loading model weights for detecting images compressed by JPEG at quality factor", compress_Q)

    detect_one_image(fname, compress_Q)
