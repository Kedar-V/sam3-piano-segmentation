# piano-segmentation

Segment a performer and a grand piano from vertical piano-performance video with Meta's official SAM 3 / 3.1, then export transparent layers for Remotion.

## Layout
- `colab/sam3_segment.ipynb` - GPU step (SAM 3.1 tracking, performer and piano passes) run on Colab; raw masks go to Google Drive.
- `src/`, `scripts/`, `configs/` - Mac-side preprocessing, refinement, export, validation (in progress).
- `remotion-preview/` - sample composition (in progress).

## Colab
Colab: File > Open notebook > GitHub > this repo > `colab/sam3_segment.ipynb`. Needs Hugging Face access to `facebook/sam3` and `facebook/sam3.1` and a Colab secret `HF_TOKEN`.
