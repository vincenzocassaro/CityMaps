# CityMaps

![CityMaps logo](assets/logo.png)

CityMaps turns a map from [Prettymaps](https://github.com/marceloprates/prettymaps) into an animated WebM video, converts it to MP4, and appends a still frame.

## Setup

The project uses Python 3.12 and FFmpeg. On macOS with Homebrew:

```sh
brew install python@3.12 ffmpeg
./scripts/setup.sh
```

The setup script clones Prettymaps next to this repository, creates `venv`, installs the Python packages, and creates the ignored working directories under `src`.

If Prettymaps lives somewhere else, pass its path:

```sh
PRETTYMAPS_DIR=/path/to/prettymaps ./scripts/setup.sh
```

## Generate the source map

Start the Prettymaps editor:

```sh
./scripts/prettymaps.sh
```

Open `http://localhost:8501` in Chrome. Choose a location and download both the PNG and SVG. Keep the OpenStreetMap and Prettymaps attribution included in the generated map.

## Build the animation

From `src`:

1. Put the downloaded PNG at `images/<city>.png` and the SVG at `<city>.svg`. Set a shell variable to that name. For example:

   ```sh
   city=palmanova
   ```

2. Copy the SVG from its opening `<svg>` tag onward into a fragment:

   ```sh
   sed -n '/<svg /,$p' "$city.svg" > "$city.fragment.svg"
   ```

3. Insert the SVG and animation CSS into the HTML template:

   ```sh
   sed \
     -e "/here goes svg/r $city.fragment.svg" \
     -e '/<\/svg>/r pcsstouse.txt' \
     template.html > "$city.html"
   ```

4. Serve the directory and open the generated page in Chrome:

   ```sh
   ../venv/bin/python -m http.server 8000
   ```

   Open `http://localhost:8000/palmanova.html`, replacing `palmanova` with your city. Chrome downloads the animation as `<city>.webm` after 15 seconds.

5. Move the recording to `videos/first/<city>.webm`, then convert and finish the video:

   ```sh
   ffmpeg -fflags +genpts \
     -i "videos/first/$city.webm" \
     -vf "scale=992:1380:force_original_aspect_ratio=decrease,pad=992:1380:(ow-iw)/2:(oh-ih)/2" \
     -r 24 -c:v libx264 -pix_fmt yuv420p \
     "videos/first/$city.mp4"
   ../venv/bin/python generate.py "$city"
   ../venv/bin/python mergevideos.py "$city"
   ```

The final file is written to `src/videos/final/<city>.mp4`.
