"""Turn one location request into downloadable CityMaps assets."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from matplotlib import pyplot as plt
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from shapely.geometry import GeometryCollection

import prettymaps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANIMATION_SCRIPT = PROJECT_ROOT / "src" / "addattribute.js"
StageCallback = Callable[[str], None]


class RenderError(RuntimeError):
    """A failure that can be explained directly to a CityMaps user."""


@dataclass(frozen=True)
class RenderRequest:
    location: str
    radius_m: int = 750
    preset: str = "default"
    circular: bool = False
    palette: tuple[str, ...] = ()
    animation_seconds: float = 15
    hold_seconds: float = 3
    fps: int = 24
    output_width: int = 992
    output_height: int = 1380
    filename: str | None = None

    def __post_init__(self) -> None:
        if not self.location.strip():
            raise ValueError("Location cannot be empty.")
        if self.radius_m <= 0:
            raise ValueError("Radius must be greater than zero.")
        if self.animation_seconds <= 0 or self.hold_seconds < 0:
            raise ValueError("Video durations must be positive.")
        if self.fps <= 0:
            raise ValueError("Frame rate must be greater than zero.")
        if self.output_width <= 0 or self.output_height <= 0:
            raise ValueError("Output dimensions must be greater than zero.")
        if self.output_width % 2 or self.output_height % 2:
            raise ValueError("Output dimensions must be even for MP4 encoding.")

    @property
    def output_name(self) -> str:
        return slugify(self.filename or self.location)


@dataclass(frozen=True)
class RenderResult:
    name: str
    png_path: Path
    svg_path: Path
    video_path: Path


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "citymap"


def render_city_map(
    request: RenderRequest,
    output_dir: Path | str = PROJECT_ROOT / "output",
    on_stage: StageCallback | None = None,
) -> RenderResult:
    """Generate the map, animate it, and return the final downloadable assets."""
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    name = request.output_name
    png_path = output_dir / f"{name}.png"
    svg_path = output_dir / f"{name}.svg"
    video_path = output_dir / f"{name}.mp4"

    _notify(on_stage, "Drawing the map from OpenStreetMap data")
    _render_map(request, png_path, svg_path)

    _notify(on_stage, "Animating the map lines")
    with tempfile.TemporaryDirectory(prefix="citymaps-") as temporary_dir:
        temporary_path = Path(temporary_dir)
        webm_path = temporary_path / f"{name}.webm"
        html_path = temporary_path / f"{name}.html"
        _write_animation_page(svg_path, html_path, request)
        animation_start = _record_animation(html_path, webm_path, request)

        _notify(on_stage, "Encoding the final MP4")
        _encode_final_video(
            webm_path,
            png_path,
            video_path,
            request,
            animation_start=animation_start,
        )

    return RenderResult(name, png_path, svg_path, video_path)


def _render_map(request: RenderRequest, png_path: Path, svg_path: Path) -> None:
    _make_prettymaps_empty_layers_safe()
    figure_size = (request.output_width / 120, request.output_height / 120)
    figure, axis = plt.subplots(figsize=figure_size, dpi=120)
    style = {"building": {"palette": list(request.palette)}} if request.palette else {}

    try:
        plot = prettymaps.plot(
            request.location,
            radius=request.radius_m,
            circle=request.circular,
            preset=request.preset,
            style=style,
            figsize=figure_size,
            fig=figure,
            ax=axis,
            show=False,
        )
        plot.fig.savefig(png_path, format="png", bbox_inches="tight", pad_inches=0, dpi=120)
        plot.fig.savefig(svg_path, format="svg", bbox_inches="tight", pad_inches=0)
    except Exception as error:
        raise RenderError(
            "The map could not be generated. Check the location name and network connection."
        ) from error
    finally:
        plt.close(figure)


def _make_prettymaps_empty_layers_safe() -> None:
    """Isolate a small upstream bug until the fix is available in Prettymaps."""
    import prettymaps.draw as draw

    original = draw.gdf_to_shapely
    if getattr(original, "_citymaps_empty_safe", False):
        return

    def empty_safe_gdf_to_shapely(layer, gdf, *args, **kwargs):
        if gdf.empty:
            return GeometryCollection()
        return original(layer, gdf, *args, **kwargs)

    empty_safe_gdf_to_shapely._citymaps_empty_safe = True
    draw.gdf_to_shapely = empty_safe_gdf_to_shapely


def _write_animation_page(
    svg_path: Path,
    html_path: Path,
    request: RenderRequest,
) -> None:
    svg = svg_path.read_text(encoding="utf-8")
    svg_start = svg.find("<svg")
    if svg_start == -1:
        raise RenderError("Prettymaps produced an SVG without an SVG element.")

    script = ANIMATION_SCRIPT.read_text(encoding="utf-8")
    configuration = json.dumps(
        {
            "animationDurationMs": round(request.animation_seconds * 1000),
            "drawDelayMs": 0,
            "finalFrameHoldMs": 500,
        }
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Rendering {request.output_name}</title>
  <style>
    html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: white; }}
    svg {{ display: block; width: 100vw; height: 100vh; }}
  </style>
</head>
<body data-render-state="running">
{svg[svg_start:]}
<script>window.CITYMAPS_CONFIG = {configuration};</script>
<script>{script}</script>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")


def _record_animation(
    html_path: Path,
    webm_path: Path,
    request: RenderRequest,
) -> float:
    timeout_ms = round((request.animation_seconds + 30) * 1000)

    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
            except PlaywrightError:
                browser = playwright.chromium.launch(headless=True)

            try:
                context = browser.new_context(
                    viewport={
                        "width": request.output_width,
                        "height": request.output_height,
                    },
                    record_video_dir=str(webm_path.parent),
                    record_video_size={
                        "width": request.output_width,
                        "height": request.output_height,
                    },
                )
                recording_started = time.monotonic()
                page = context.new_page()
                recording = page.video
                page.goto(html_path.as_uri(), wait_until="load")
                animation_start = max(
                    0,
                    time.monotonic() - recording_started - 0.15,
                )
                page.wait_for_function(
                    "document.body.dataset.renderState === 'complete'",
                    timeout=timeout_ms,
                )
                context.close()
                recorded_path = Path(recording.path())
                webm_path.unlink(missing_ok=True)
                recorded_path.replace(webm_path)
            finally:
                browser.close()
    except RenderError:
        raise
    except PlaywrightError as error:
        raise RenderError(
            "Chrome could not render the animation. Install Google Chrome and try again."
        ) from error

    if not webm_path.exists() or webm_path.stat().st_size == 0:
        raise RenderError("Chrome finished without producing an animation.")

    return animation_start


def _encode_final_video(
    webm_path: Path,
    png_path: Path,
    video_path: Path,
    request: RenderRequest,
    animation_start: float = 0,
) -> None:
    if shutil.which("ffmpeg") is None:
        raise RenderError("FFmpeg is required. Install it with: brew install ffmpeg")
    if shutil.which("ffprobe") is None:
        raise RenderError("FFprobe is required and is normally installed with FFmpeg.")

    recorded_duration = _video_duration(webm_path)
    captured_animation = max(
        recorded_duration - animation_start,
        1 / request.fps,
    )
    requested_animation = request.animation_seconds + 0.5
    timing_factor = requested_animation / captured_animation

    size_filter = (
        f"scale={request.output_width}:{request.output_height}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={request.output_width}:{request.output_height}:"
        "(ow-iw)/2:(oh-ih)/2:color=white,setsar=1"
    )
    animation_filter = (
        f"[0:v]trim=start={animation_start:.3f},"
        f"setpts={timing_factor:.6f}*(PTS-STARTPTS),"
        f"fps={request.fps},{size_filter}[animation]"
    )
    command = [
        "ffmpeg",
        "-y",
        "-fflags",
        "+genpts",
        "-i",
        str(webm_path),
    ]

    if request.hold_seconds:
        still_filter = (
            f"[1:v]fps={request.fps},{size_filter},"
            f"trim=duration={request.hold_seconds},setpts=PTS-STARTPTS[still]"
        )
        filters = (
            f"{animation_filter};{still_filter};"
            "[animation][still]concat=n=2:v=1:a=0[video]"
        )
        command.extend(
            [
                "-loop",
                "1",
                "-framerate",
                str(request.fps),
                "-i",
                str(png_path),
            ]
        )
    else:
        filters = animation_filter.replace("[animation]", "[video]")

    command.extend(
        [
            "-filter_complex",
            filters,
            "-map",
            "[video]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    )
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode != 0:
        details = "\n".join(process.stderr.splitlines()[-12:])
        raise RenderError(f"FFmpeg could not create the final video.\n{details}")


def _video_duration(video_path: Path) -> float:
    process = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float(process.stdout.strip())
    except ValueError as error:
        raise RenderError("FFprobe could not read the animation duration.") from error


def _notify(callback: StageCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)
