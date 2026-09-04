import subprocess
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from citymaps.render import (
    RenderRequest,
    _encode_final_video,
    _record_animation,
    _write_animation_page,
)


def launch_chrome(playwright):
    try:
        return playwright.chromium.launch(channel="chrome", headless=True)
    except PlaywrightError:
        return playwright.chromium.launch(headless=True)


def test_line_drawing_is_visible_during_the_first_second(tmp_path):
    svg_path = tmp_path / "map.svg"
    html_path = tmp_path / "animation.html"
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
    request = RenderRequest(
        "early-motion-test",
        animation_seconds=5,
        hold_seconds=0,
        output_width=160,
        output_height=160,
    )
    _write_animation_page(svg_path, html_path, request)
    assert "visibility: hidden" in html_path.read_text(encoding="utf-8")

    with sync_playwright() as playwright:
        browser = launch_chrome(playwright)
        try:
            page = browser.new_page()
            page.goto(html_path.as_uri(), wait_until="load")
            page.wait_for_timeout(100)
            first_frame_fractions = page.evaluate(
                """() => {
                    const paths = document.querySelectorAll('path');
                    return [3, 4].map(index => {
                        const path = paths[index];
                        return 1 - Number.parseFloat(getComputedStyle(path).strokeDashoffset) / path.getTotalLength();
                    });
                }"""
            )
            page.wait_for_timeout(900)
            drawn_fractions = page.evaluate(
                """() => {
                    const paths = document.querySelectorAll('path');
                    return [3, 4].map(index => {
                        const path = paths[index];
                        return 1 - Number.parseFloat(getComputedStyle(path).strokeDashoffset) / path.getTotalLength();
                    });
                }"""
            )
            visibility = page.locator("svg").evaluate(
                "svg => getComputedStyle(svg).visibility"
            )
        finally:
            browser.close()

    assert max(first_frame_fractions) < 0.01
    assert drawn_fractions[0] > 0.25
    assert drawn_fractions[1] < 0.05
    assert visibility == "visible"


def test_recording_reports_svg_loading_time(tmp_path):
    svg_path = tmp_path / "slow-map.svg"
    html_path = tmp_path / "animation.html"
    webm_path = tmp_path / "animation.webm"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160">
        <script>const until = performance.now() + 750; while (performance.now() &lt; until) {}</script>
        <path d="M0 0H160V160H0Z"/><path d="M2 2H158V158H2Z"/>
        <path d="M4 4H156V156H4Z"/><path d="M30 30H130V130H30Z"/>
        <path d="M50 50H110V110H50Z"/><path d="M10 10L20 20"/>
        <path d="M140 140L150 150"/>
        </svg>""",
        encoding="utf-8",
    )
    request = RenderRequest(
        "slow-map",
        animation_seconds=0.5,
        hold_seconds=0,
        output_width=160,
        output_height=160,
    )
    _write_animation_page(svg_path, html_path, request)

    animation_start = _record_animation(html_path, webm_path, request)

    assert animation_start > 0.5


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
    animation_start = _record_animation(html_path, webm_path, request)
    _encode_final_video(
        webm_path,
        png_path,
        video_path,
        request,
        animation_start=animation_start,
    )
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

    duration = subprocess.run(
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
        check=True,
        capture_output=True,
        text=True,
    )
    assert float(duration.stdout) >= request.animation_seconds
