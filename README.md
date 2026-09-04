# CityMaps

![CityMaps logo](assets/logo.png)

CityMaps turns a place into an animated MP4. The studio draws the map with
[Prettymaps](https://github.com/marceloprates/prettymaps), animates its SVG
paths in headless Chrome, and encodes the result with FFmpeg. Those steps are
internal: generating a finished video takes one form and one button.

## Setup

CityMaps requires Python 3.12, Google Chrome, and FFmpeg. On macOS with
Homebrew:

```sh
brew install python@3.12 ffmpeg
./scripts/setup.sh
```

Prettymaps is installed as a pinned Python dependency. A separate checkout or
Prettymaps server is no longer needed.

## Run the studio

```sh
./scripts/run.sh
```

Open `http://localhost:8501`, choose a location and style, then select
**Generate animated map**. CityMaps displays the result and provides MP4, PNG,
and SVG downloads.

Generated files are also written to the ignored `output` directory.

## Free TikTok drafts

After rendering a video, expand **Send to TikTok for free**. CityMaps uploads
the MP4 to Cloudinary, then creates a private TikTok draft through Buffer. The
draft cannot publish until it is explicitly scheduled in Buffer.

Create free Buffer and Cloudinary accounts, connect TikTok to Buffer, and copy
the Buffer API key and Cloudinary URL into the studio. Neither secret is stored
in the repository. They can also be supplied when starting the studio:

```sh
BUFFER_API_KEY=your-key CLOUDINARY_URL=cloudinary://key:secret@cloud ./scripts/run.sh
```

On macOS, `scripts/run.sh` also reads credentials stored in Keychain under
`CityMaps Buffer API Key` and `CityMaps Cloudinary URL`. Environment variables
take precedence when present.

## Run from the command line

The command line calls the same renderer as the studio:

```sh
venv/bin/python -m citymaps "Palmanova, Italy"
```

Options include `--radius`, `--preset`, `--animation`, `--hold`, and `--output`.
Run `venv/bin/python -m citymaps --help` for details.

## Architecture

`citymaps.render.render_city_map()` is the single rendering interface. It owns
the complete sequence:

1. Fetch OpenStreetMap data and save the map as PNG and SVG.
2. Record the SVG line animation in headless Chrome.
3. Scale, pad, and encode the animation and final still into one H.264 MP4.

The Streamlit studio and command line are thin adapters around that interface.
The browser recording and FFmpeg implementation can therefore change without
changing how either entry point is used.

Map data © OpenStreetMap contributors. Map rendering by Prettymaps.
