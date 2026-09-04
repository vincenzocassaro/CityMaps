"""Command-line entry point for CityMaps."""

import argparse
from pathlib import Path

from . import RenderRequest, render_city_map


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an animated city map.")
    parser.add_argument("location", help="Location understood by OpenStreetMap")
    parser.add_argument("--radius", type=int, default=750, help="Map radius in metres")
    parser.add_argument("--preset", default="default", help="Prettymaps preset")
    parser.add_argument("--animation", type=float, default=15, help="Animation seconds")
    parser.add_argument("--hold", type=float, default=3, help="Final still seconds")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()

    request = RenderRequest(
        location=args.location,
        radius_m=args.radius,
        preset=args.preset,
        animation_seconds=args.animation,
        hold_seconds=args.hold,
    )
    result = render_city_map(request, args.output, on_stage=print)
    print(f"Created {result.video_path}")


if __name__ == "__main__":
    main()
