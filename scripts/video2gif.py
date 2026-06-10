"""
批量视频转GIF工具
用法: python video2gif.py [输入目录] [输出目录] [选项]
示例: python video2gif.py ./videos ./gifs --fps 15 --width 640
"""

import argparse
import subprocess
from pathlib import Path


def convert_video_to_gif(
    input_path: Path,
    output_path: Path,
    fps: int = 15,
    width: int = 640,
    quality: int = 80,
) -> bool:
    """将单个视频转换为GIF"""
    # 生成调色板提高质量
    palette_cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,palettegen=stats_mode=diff",
        "-frames:v", "1",
        "palette.png",
    ]

    convert_cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-i", "palette.png",
        "-lavfi", f"fps={fps},scale={width}:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
        "-loop", "0",
        str(output_path),
    ]

    try:
        subprocess.run(palette_cmd, capture_output=True, check=True, timeout=60)
        subprocess.run(convert_cmd, capture_output=True, check=True, timeout=120)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"  [ERROR] {e}")
        return False
    finally:
        # 清理临时调色板
        Path("palette.png").unlink(missing_ok=True)


def batch_convert(
    input_dir: Path,
    output_dir: Path,
    fps: int = 15,
    width: int = 640,
    quality: int = 80,
) -> None:
    """批量转换目录下所有视频"""
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}
    videos = [f for f in input_dir.iterdir() if f.suffix.lower() in video_exts]

    if not videos:
        print(f"No video files found in {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(videos)
    success = 0

    print(f"Found {total} videos, converting...\n")

    for i, video in enumerate(videos, 1):
        gif_name = video.stem + ".gif"
        gif_path = output_dir / gif_name
        print(f"[{i}/{total}] {video.name} -> {gif_name}")

        if convert_video_to_gif(video, gif_path, fps, width, quality):
            size_mb = gif_path.stat().st_size / 1024 / 1024
            print(f"  [OK] {size_mb:.1f} MB")
            success += 1
        else:
            print(f"  [FAIL]")

    print(f"\nDone: {success}/{total} converted")


def main():
    parser = argparse.ArgumentParser(description="Batch video to GIF converter")
    parser.add_argument("input_dir", nargs="?", default=".", help="Input directory with videos")
    parser.add_argument("output_dir", nargs="?", default="./gifs", help="Output directory for GIFs")
    parser.add_argument("--fps", type=int, default=15, help="Frames per second (default: 15)")
    parser.add_argument("--width", type=int, default=640, help="Output width in pixels (default: 640)")
    parser.add_argument("--quality", type=int, default=80, help="Quality 1-100 (default: 80)")
    args = parser.parse_args()

    batch_convert(Path(args.input_dir), Path(args.output_dir), args.fps, args.width, args.quality)


if __name__ == "__main__":
    main()
