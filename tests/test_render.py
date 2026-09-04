from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import GeometryCollection

from citymaps import RenderRequest
from citymaps import render as render_module
from citymaps.render import slugify


def test_slugify_produces_safe_filename():
    assert slugify("Città di Palmanova, Italy") == "citta-di-palmanova-italy"


def test_request_rejects_odd_video_dimensions():
    with pytest.raises(ValueError, match="even"):
        RenderRequest("Palmanova", output_width=991)


def test_animation_page_contains_svg_and_request_configuration(tmp_path):
    svg_path = tmp_path / "map.svg"
    html_path = tmp_path / "map.html"
    svg_path.write_text(
        '<?xml version="1.0"?><svg width="20" height="20"><path d="M0 0L20 20"/></svg>',
        encoding="utf-8",
    )
    request = RenderRequest("Palmanova", animation_seconds=7)

    render_module._write_animation_page(svg_path, html_path, request)

    html = html_path.read_text(encoding="utf-8")
    assert '<svg width="20" height="20">' in html
    assert '"animationDurationMs": 7000' in html
    assert "data-render-state=\"running\"" in html


def test_prettymaps_adapter_handles_an_empty_graph_layer(monkeypatch):
    import prettymaps.draw as draw

    monkeypatch.delattr(draw.gdf_to_shapely, "_citymaps_empty_safe", raising=False)
    render_module._make_prettymaps_empty_layers_safe()
    empty_graph = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    result = draw.gdf_to_shapely(
        "streets",
        empty_graph,
        width={"primary": 4},
    )

    assert isinstance(result, GeometryCollection)
    assert result.is_empty


def test_render_city_map_owns_the_complete_pipeline(tmp_path, monkeypatch):
    stages = []

    def fake_map(request, png_path, svg_path):
        png_path.write_bytes(b"png")
        svg_path.write_text("<svg></svg>", encoding="utf-8")

    def fake_record(html_path, webm_path, request):
        assert html_path.exists()
        assert request.animation_seconds == 15
        webm_path.write_bytes(b"webm")

    def fake_encode(webm_path, png_path, video_path, request):
        assert webm_path.read_bytes() == b"webm"
        assert png_path.read_bytes() == b"png"
        video_path.write_bytes(b"mp4")

    monkeypatch.setattr(render_module, "_render_map", fake_map)
    monkeypatch.setattr(render_module, "_record_animation", fake_record)
    monkeypatch.setattr(render_module, "_encode_final_video", fake_encode)

    result = render_module.render_city_map(
        RenderRequest("Palmanova, Italy"),
        tmp_path,
        on_stage=stages.append,
    )

    assert result.video_path.read_bytes() == b"mp4"
    assert result.png_path == Path(tmp_path, "palmanova-italy.png")
    assert stages == [
        "Drawing the map from OpenStreetMap data",
        "Animating the map lines",
        "Encoding the final MP4",
    ]
