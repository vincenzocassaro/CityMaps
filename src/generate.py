import argparse
from pathlib import Path

import cv2


def create_still_video(image_name: str, duration: float = 3, fps: int = 24) -> Path:
    project_dir = Path(__file__).resolve().parent
    image_path = project_dir / "images" / f"{image_name}.png"
    video_path = project_dir / "videos" / "second" / f"{image_name}.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)

    frame = cv2.imread(str(image_path))
    if frame is None:
        raise FileNotFoundError(f"Could not read source image: {image_path}")

    height, width = frame.shape[:2]
    if width % 2 or height % 2:
        frame = cv2.copyMakeBorder(
            frame,
            0,
            height % 2,
            0,
            width % 2,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255),
        )
        height, width = frame.shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

    for _ in range(round(duration * fps)):
        video.write(frame)

    video.release()
    return video_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the still ending clip.")
    parser.add_argument("city", help="Base name of the PNG in src/images")
    parser.add_argument("--duration", type=float, default=3)
    args = parser.parse_args()

    print(create_still_video(args.city, duration=args.duration))


if __name__ == "__main__":
    main()
