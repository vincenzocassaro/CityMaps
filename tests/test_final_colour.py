import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from citymaps.render import (
    RenderRequest,
    _encode_final_video,
    _record_animation,
    _write_animation_page,
)


def test_animation_records_its_final_coloured_frame(tmp_path):
    svg_path = tmp_path / "map.svg"
    png_path = tmp_path / "map.png"
    html_path = tmp_path / "animation.html"
    webm_path = tmp_path / "animation.webm"
    video_path = tmp_path / "animation.mp4"
    final_frame_path = tmp_path / "final.png"

    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160">
        <path d="M0 0H160V160H0Z" style="fill:#ffffff;stroke:none"/>
        <path d="M2 2H158V158H2Z" style="fill:none;stroke:#111111"/>
        <path d="M4 4H156V156H4Z" style="fill:none;stroke:#111111"/>
        <path d="M30 30H130V130H30Z" style="fill:#ff0000;stroke:#111111"/>
        <path d="M50 50H110V110H50Z" style="fill:#0055ff;stroke:#111111"/>
        <path d="M10 10L20 20" style="fill:none;stroke:#111111"/>
        <path d="M140 140L150 150" style="fill:none;stroke:#111111"/>
        </svg>""",
        encoding="utf-8",
    )
    image = Image.new("RGB", (160, 160), "white")
    ImageDraw.Draw(image).rectangle((30, 30, 130, 130), fill="red")
    image.save(png_path)

    request = RenderRequest(
        "colour-test",
        animation_seconds=0.75,
        hold_seconds=0,
        output_width=160,
        output_height=160,
    )
    _write_animation_page(svg_path, html_path, request)
    _record_animation(html_path, webm_path, request)
    _encode_final_video(webm_path, png_path, video_path, request)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-sseof",
            "-0.1",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(final_frame_path),
        ],
        check=True,
        capture_output=True,
    )

    frame = Image.open(final_frame_path).convert("RGB")
    red_pixels = sum(
        1
        for red, green, blue in frame.get_flattened_data()
        if red > 180 and green < 100 and blue < 100
    )

    assert red_pixels / (frame.width * frame.height) > 0.15
