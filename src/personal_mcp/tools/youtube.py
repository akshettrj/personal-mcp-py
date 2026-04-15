import os
import subprocess
from pathlib import Path

import yt_dlp
from personal_mcp import MCP_SERVER
from .mutagen import add_id3_title, set_id3_artist, set_id3_thumbnail


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

            # Handle playlist vs single video
            if "entries" in info:
                return {
                    "type": "playlist",
                    "title": info.get("title"),
                    "video_count": len(info.get("entries", [])),
                    "uploader": info.get("uploader"),
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
                "type": "video",
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
def get_playlist_metadata(url: str) -> dict:
    """
    Fetch a list of all songs in a playlist with their metadata using flat-playlist extraction.

    Args:
        url: The YouTube playlist URL.
    """
    args = [
        "--cookies-from-browser",
        "brave::Personal",
        "--flat-playlist",
        "--dump-single-json",
        "--quiet",
        "--no-warnings",
        url,
    ]

    ydl_opts = get_ydl_opts(args)
    ydl_opts["quiet"] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                return {"error": "Could not fetch playlist metadata."}

            entries = []
            for entry in info.get("entries", []):
                if not entry:
                    continue
                entries.append(
                    {
                        "id": entry.get("id"),
                        "title": entry.get("title"),
                        "url": entry.get("url")
                        or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        "duration": entry.get("duration"),
                        "duration_string": entry.get("duration_string"),
                        "uploader": entry.get("uploader"),
                        "playlist_index": entry.get("playlist_index"),
                    }
                )

            return {
                "playlist_title": info.get("title"),
                "playlist_id": info.get("id"),
                "uploader": info.get("uploader"),
                "entries_count": len(entries),
                "entries": entries,
            }
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}


def _process_downloaded_file(info: dict, source_path: str) -> str:
    """Helper to convert a single file to MP3 and apply metadata."""
    target_path = str(Path(source_path).with_suffix(".mp3"))
    
    # Use ffmpeg to convert to MP3 with best quality (320k or -q:a 0)
    # We use -q:a 0 for best VBR or -b:a 320k for best CBR. 
    cmd = [
        "ffmpeg", "-i", source_path,
        "-codec:a", "libmp3lame",
        "-b:a", "320k",
        "-map", "0:a", # Only map audio for the actual audio stream
        "-y", # overwrite
        target_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        return f"ffmpeg error for {source_path}: {e.stderr.decode()}"
        
    # Apply metadata using mutagen tools
    title = info.get("title")
    uploader = info.get("uploader")
    
    if title:
        add_id3_title(target_path, title)
    if uploader:
        set_id3_artist(target_path, [uploader])
        
    # Handle thumbnail
    # Since we used --embed-thumbnail, yt-dlp might have downloaded it.
    # We'll check for the thumbnail file.
    base_path = os.path.splitext(source_path)[0]
    for ext in [".jpg", ".png", ".webp", ".jpeg"]:
        thumb_path = base_path + ext
        if os.path.exists(thumb_path):
            try:
                set_id3_thumbnail(target_path, thumb_path)
                os.remove(thumb_path)
                break
            except:
                pass

    # Clean up original file
    if os.path.exists(source_path) and source_path != target_path:
        os.remove(source_path)
        
    return target_path


@MCP_SERVER.tool()
def download_music(
    url: str, output_dir: str = "~/Downloads", noplaylist: bool = False
) -> str:
    """
    Download music from YouTube using yt-dlp and manually convert to MP3.
    Always selects the best available quality.

    Args:
        url: The YouTube URL to download from.
        output_dir: The directory to save the downloaded file. Defaults to ~/Downloads.
        noplaylist: Whether to only download a single video even if the URL contains a playlist. Defaults to False.
    """
    expanded_dir = os.path.expanduser(output_dir)
    os.makedirs(expanded_dir, exist_ok=True)

    # Download best audio and embed thumbnail (yt-dlp will also keep the thumb file if requested,
    # or we can use --write-thumbnail to be sure we have a file to embed into the MP3 later)
    args = [
        "--cookies-from-browser",
        "brave::Personal",
        "--format",
        "bestaudio",
        "--embed-thumbnail",
        "--write-thumbnail",
        "--output",
        os.path.join(expanded_dir, "%(title)s.%(ext)s"),
        "--quiet",
        "--no-warnings",
        url,
    ]

    if noplaylist:
        args.append("--no-playlist")
    else:
        args.append("--yes-playlist")

    ydl_opts = get_ydl_opts(args)
    ydl_opts["quiet"] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return f"Error downloading: Could not find content for this URL."

            if "entries" in info:
                results = []
                for entry in info["entries"]:
                    if not entry:
                        continue
                    source_path = ydl.prepare_filename(entry)
                    res = _process_downloaded_file(entry, source_path)
                    results.append(res)
                return f"Successfully downloaded and converted playlist '{info.get('title')}' ({len(results)} items) to {expanded_dir}"

            source_path = ydl.prepare_filename(info)
            _process_downloaded_file(info, source_path)
            title = info.get("title", "Unknown Title")
            return f"Successfully downloaded and converted: {title} to {expanded_dir}"
    except Exception as e:
        return f"Error: {str(e)}"
