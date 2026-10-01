<h1 align="center">DigiHand</h1> 

<p align="center">Turning Chicken Scratch to Text, written in <b>Python</b>.</p>

DigiHand is an innovative handwriting digitization platform that is powerful and easy to use, converting scanned PDFs of handwriting into digital text. After selecting a model, utilize its intuitive side-by-side editor to adjust raw output.

> [!NOTE]
> DigiHand runs its vision models and LLMs **locally** on your machine to keep your data private and secure.

---

The initial output:
<img src="/images/readme_example.png" alt="converted page example">


## Features

- **Solve PDF** by selecting a model in the dropdown and then clicking the lightning bolt.
- **Solver Dialogue** provides user on model updates, includes a progress bar.
- **Synced Scroll** automatically displays the PDF's corresponding output file.
- **Auto Save** detects any changes made, allowing for effortless editing.
- **PDF Viewer** can zoom in, zoom out, fit original, fit to width, rotate, and jump to any page.
- **Text Editor** can change font, font size, and text alignment; supports bold, italics, and underline.

Solver Dialogue:
<img src="/images/readme_example_dialogue.png" alt="solver dialogue example">


Edited output:
<!-- <img src="/images/readme_example.png" alt="converted page example"> -->

## Hardware Acceleration

DigiHand supports CUDA on Windows and Linux. 

### CUDA

CUDA 13.3 requires an NVIDIA Turing-class or newer GPU and an R610 or newer driver. Check NVIDIA's official [CUDA toolkit, driver, and architecture matrix](https://docs.nvidia.com/datacenter/tesla/drivers/cuda-toolkit-driver-and-architecture-matrix.html) and install the [latest NVIDIA driver](https://www.nvidia.com/en-us/drivers/).


### CPU

CPU inference is available for supported workloads but is substantially slower.

## Models Available:
- Qwen 2.5
- Florence2
- Moondream2
