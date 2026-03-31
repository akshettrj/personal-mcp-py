import os

import yt_dlp
from personal_mcp import MCP_SERVER


def get_ydl_opts(args: list[str]) -> dict:
    """
    Use yt-dlp's own parser to convert CLI-style arguments into a ydl_opts dictionary.
    This ensures the behavior is identical to the CLI.
    """
    parser, opts, urls, ydl_opts = yt_dlp.parse_options(args)
    return ydl_opts


@MCP_SERVER.tool()
def get_music_metadata(url: str) -> dict:
    """
    Fetch metadata for a YouTube video/audio using yt-dlp.
    Uses the same logic as the CLI to ensure consistency.

    Args:
        url: The YouTube URL to fetch metadata for.
    """
    # Simulate CLI arguments for metadata fetching
    args = [
        "--cookies-from-browser",
        "brave::Personal",
        "--quiet",
        "--no-warnings",
        "--ignore-errors",
        "--print-json",
        url,
    ]

    ydl_opts = get_ydl_opts(args)
    ydl_opts["quiet"] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                return {
                    "error": "Could not fetch metadata for this URL. It might be private, restricted, or deleted."
                }

            formats = [
                {
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "quality": f.get("quality"),
                    "note": f.get("format_note"),
                }
                for f in info.get("formats", [])
                if f.get("acodec") != "none"
            ]

            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "description": (
                    info.get("description")[:200] + "..."
                    if info.get("description")
                    else None
                ),
                "formats": formats,
                "error": "No audio formats available" if not formats else None,
            }
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}


@MCP_SERVER.tool()
def download_music(
    url: str, output_dir: str = "~/Downloads", quality: str = "320"
) -> str:
    """
    Download music from YouTube using yt-dlp.
    Uses the same logic as the CLI to ensure consistency.

    Args:
        url: The YouTube URL to download from.
        output_dir: The directory to save the downloaded file. Defaults to ~/Downloads.
        quality: The preferred quality for audio extraction (e.g., "320", "192", "128"). Defaults to "320".
    """
    expanded_dir = os.path.expanduser(output_dir)
    os.makedirs(expanded_dir, exist_ok=True)

    # Simulate CLI arguments for downloading
    args = [
        "--cookies-from-browser",
        "brave::Personal",
        "--format",
        "bestaudio",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        quality,
        "--embed-thumbnail",
        "--add-metadata",
        "--output",
        os.path.join(expanded_dir, "%(title)s.%(ext)s"),
        "--quiet",
        "--no-warnings",
        url,
    ]

    ydl_opts = get_ydl_opts(args)
    ydl_opts["quiet"] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return f"Error downloading music: Could not find audio for this URL."
            title = info.get("title", "Unknown Title")
            return f"Successfully downloaded: {title} (Quality: {quality}kbps) to {expanded_dir}"
    except Exception as e:
        return f"Error downloading music: {str(e)}"
