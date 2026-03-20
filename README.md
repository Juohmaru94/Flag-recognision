# Flag Recognition Typer

A Windows-focused Python 3.11+ desktop utility that captures a flag from the screen, recognizes the country offline, and types the country name into the currently focused application.

## Features

- Global hotkey mode with a lightweight drag-to-select overlay.
- Fixed-region mode for one-shot capture or continuous watch mode.
- Offline local-first recognition using precomputed descriptors from a folder of reference flag images.
- Configurable confidence threshold, typing delay, Enter key behavior, debug capture saving, and loop interval.
- Modular architecture so the recognition backend can later be swapped for an online vision API.
- Calibration helper for saving a fixed capture region.

## Project structure

```text
flag_recognition/
  capture/
  recognition/
  config.py
  hotkeys.py
  typing_utils.py
  app.py
assets/
  flags/
config.sample.json
requirements.txt
main.py
```

## Installation

1. Install Python 3.11 or newer on Windows.
2. Create and activate a virtual environment:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Create your working config from the sample:
   ```powershell
   copy config.sample.json config.json
   ```
5. Add reference flags in `assets/flags/`. The folder is gitignored so your local dataset stays out of commits.

## Reference dataset

- Add one image per country to `assets/flags/`.
- Recommended naming: lowercase with underscores, e.g. `united_states.png`.
- The repository keeps only a text placeholder file in this folder; add images locally.
- The recognizer loads and preprocesses all reference images at startup and keeps descriptors in memory.
- If no dataset exists, the app exits with setup guidance.

### Included starter dataset

This repository intentionally keeps the dataset folder text-only. Add your own reference flag images locally, for example:
- `assets/flags/france.png`
- `assets/flags/germany.png`
- `assets/flags/japan.png`

Add a full reference set locally for broader coverage.

## Configuration

Edit `config.json`:

- `hotkey`: Global capture hotkey.
- `fixed_region`: `{left, top, width, height}` rectangle in screen coordinates.
- `confidence_threshold`: Skip typing below this score.
- `type_delay_ms`: Delay before typing.
- `press_enter`: Press Enter after typing when `true`.
- `debug`: Save captures to disk when enabled.
- `loop_interval_ms`: Delay between loops in fixed watch mode.
- `min_region_size`: Minimum accepted selection size.
- `dataset_dir`: Reference flag folder.
- `debug_dir`: Optional debug screenshot output folder.

## Usage

### Hotkey mode

```powershell
python main.py --mode hotkey
```

- Press `Ctrl+Shift+S`.
- Drag a rectangle around the flag.
- The app captures only that region, recognizes the best country match, and types the country name into the active window.

### Fixed mode, one shot

```powershell
python main.py --mode fixed
```

### Fixed mode, watch loop

```powershell
python main.py --mode fixed --loop
```

### Calibration helper

Print region coordinates:

```powershell
python main.py --calibrate
```

Print and save the region into `config.json`:

```powershell
python main.py --calibrate --save-region
```

## How recognition works

1. Each reference image is resized with aspect-ratio preservation and padding.
2. The app builds a combined descriptor from HSV color histograms and a tiny normalized thumbnail.
3. The captured flag region is processed with the same pipeline.
4. Cosine similarity is converted into a confidence score.
5. The best match and top 3 candidates are logged.
6. If confidence is below the configured threshold, the app logs `low confidence` and does not type.

This approach is fast, fully offline, and robust to modest scaling changes.

## Console logs

The app logs:
- capture triggered
- image size
- top 3 candidate matches
- selected result
- confidence
- typed output or skipped output

## Swapping in another backend later

The recognizer implements a backend interface in `flag_recognition/recognition/engine.py`.
You can add another recognizer class, such as a CLIP or API-backed recognizer, and inject it into the app with minimal changes.

## Notes and limitations

- On Windows, some global hotkey libraries can require elevated privileges depending on the target application.
- `pyautogui` types into the currently focused window, so make sure the target app has focus before the typing delay elapses.
- This repository does not ship reference images; practical use requires you to add a complete local flag reference set.
- The selection overlay uses Tkinter, which ships with standard Python on Windows.

## Troubleshooting

- **Hotkey registration fails**: Try running the terminal as Administrator or pick another hotkey.
- **No typing occurs**: Check confidence logs and lower the threshold only if needed.
- **Dataset error**: Add images under `assets/flags/` and rerun.
- **Incorrect match**: Use cleaner reference flags with consistent aspect ratios and higher resolution.
