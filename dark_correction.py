import os
import glob
import re


import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

from SLDevicePythonWrapper import (
    SLDevice,
    DeviceInterface,
    SLError,
    ExposureModes,
    SLImage,
    SLBufferInfo,
)

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

def plot_grid(files):
    # Sort by exposure time
    files.sort(key=extract_exposure_time)
    files = files[:12]

    fig, axes = plt.subplots(3, 4, figsize=(12, 9))
    axes = axes.ravel()

    for i, file in enumerate(files):
        img = imageio.imread(file)  # 16-bit TIFF
        img_norm = img.astype(np.float32) / np.max(img)  # normalize 0–1
        axes[i].imshow(img_norm, cmap="gray", vmin=0, vmax=1)
        axes[i].set_title(f"{extract_exposure_time(file)} ms", fontsize=9)
        axes[i].axis("off")

    plt.tight_layout()
    plt.show()

def invert_image(image: SLImage):
    return SLImage.Array2Frame(2**14 - 1 - image.Frame2Array(0))

if __name__ == '__main__':
    print('Applying dark correction')

    xdim, ydim = 1031, 1536

    fig, axes = plt.subplots(3, 4, figsize=(12, 9))
    axes = axes.ravel()

    # Load images
    folder_path = r'C:\programming\pyside6-practice\Images\York\single-capture'
    files = glob.glob(os.path.join(folder_path, "*.tif"))
    files.sort(key=extract_exposure_time)


    for i, file in enumerate(files):
        image = SLImage(xdim, ydim)
        SLImage.ReadTiffImage(file, image)
        exp_time = extract_exposure_time(file)
        print(f'Exposure time: {exp_time}ms')

        # Initialise dark image object 
        dark_image = SLImage(xdim, ydim)

        # If dark image doesn't exist in directory, capture one
        filename_dark = f'C:\programming\pyside6-practice\Images\York\correction_images\\dark_frame_{exp_time}.tif'
        if not os.path.exists(filename_dark):
            # Try and capture dark image
            print('No dark image found.')
            continue

        # Load dark image
        err = SLImage.ReadTiffImage(filename_dark, dark_image)
        if err != True:
            print(f'Failed to read dark image')
            continue

        # Apply offset correction
        err = SLImage.OffsetCorrection(image, dark_image, darkOffset=50)
        if err != SLError.SL_ERROR_SUCCESS:
            print(f'Failed to apply dark correction with error: {err}')
            continue    
        print('Offset correction applied')
        
        # Crop image
        cropped_image = SLImage(xdim, ydim)
        image.GetSubImage(image, cropped_image, 370, 617, 500, 200)

        # Invert Image
        inverted_image = invert_image(cropped_image)

        # Save image
        inverted_image.WriteTiffImage(f'C:\programming\pyside6-practice\Images\York\corrected_images\cropped_{exp_time}ms.tif')

        img = inverted_image.Frame2Array(0)
        img_norm = img.astype(np.float32) / np.max(img)  # normalize 0–1
        axes[i].imshow(img_norm, cmap="gray", vmin=0, vmax=1)
        axes[i].set_title(f"{exp_time} ms", fontsize=9)
        axes[i].axis("off")
        
    plt.show()