import argparse
from pathlib import Path

from moviepy.editor import VideoFileClip, concatenate_videoclips


def concatenate(video_clip_paths, output_path, method="compose"):
    """Concatenates several video files into one video file
    and save it to `output_path`. Note that extension (mp4, etc.) must be added to `output_path`
    `method` can be either 'compose' or 'reduce':
        `reduce`: Reduce the quality of the video to the lowest quality on the list of `video_clip_paths`.
        `compose`: type help(concatenate_videoclips) for the info"""
    # create VideoFileClip object for each video file
    clips = [VideoFileClip(str(path)) for path in video_clip_paths]
    final_clip = None
    try:
        if method == "reduce":
            min_height = min(clip.h for clip in clips)
            min_width = min(clip.w for clip in clips)
            clips = [clip.resize(newsize=(min_width, min_height)) for clip in clips]
            final_clip = concatenate_videoclips(clips)
        elif method == "compose":
            final_clip = concatenate_videoclips(clips, method="compose")
        else:
            raise ValueError(f"Unknown concatenation method: {method}")

        final_clip.write_videofile(str(output_path), codec="libx264", audio=False)
    finally:
        if final_clip is not None:
            final_clip.close()
        for clip in clips:
            clip.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Append the still clip to a map animation.")
    parser.add_argument("city", help="Base name shared by the input video files")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    video_dir = project_dir / "videos"
    output_path = video_dir / "final" / f"{args.city}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concatenate(
        [
            video_dir / "first" / f"{args.city}.mp4",
            video_dir / "second" / f"{args.city}.mp4",
        ],
        output_path,
    )
    print(output_path)


if __name__ == "__main__":
    main()
