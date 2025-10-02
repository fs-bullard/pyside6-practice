import os
import glob
import re
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import numpy as np

def extract_exposure_time(filename):
    """
    Extract exposure time (in ms) from filename like '200ms_7196.tif'
    Returns integer value in ms.
    """
    match = re.search(r"(\d+)ms", os.path.basename(filename))
    if match:
        return int(match.group(1))
    else:
        return float("inf")

def plot_grid(files, title):
    # Sort by exposure time
    files.sort(key=extract_exposure_time)
    files = files[:12]

    fig, axes = plt.subplots(3, 4, figsize=(12, 9))
    fig.suptitle(title, fontsize=14)
    axes = axes.ravel()

    for i, file in enumerate(files):
        img = imageio.imread(file)  # 16-bit TIFF
        img_norm = img.astype(np.float32) / np.max(img)  # normalize 0–1
        axes[i].imshow(img_norm, cmap="gray", vmin=0, vmax=1)
        axes[i].set_title(f"{extract_exposure_time(file)} ms", fontsize=9)
        axes[i].axis("off")

    plt.tight_layout()
    plt.show()

def plot_tifs_two_sets(folder_path):
    files = glob.glob(os.path.join(folder_path, "*.tif"))

    corr_files = [f for f in files if os.path.basename(f).startswith("corr_")]
    raw_files = [f for f in files if not os.path.basename(f).startswith("corr_")]

    if len(corr_files) < 12 or len(raw_files) < 12:
        raise ValueError("Need at least 12 corr_ and 12 non-corr_ images.")

    plot_grid(raw_files, "Uncorrected Images")
    plot_grid(corr_files, "Corrected Images")

# Example usage:
plot_tifs_two_sets(r"C:\programming\pyside6-practice\Images\captured_images")
