import json
from pathlib import Path

from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TXXX, ID3NoHeaderError
from personal_mcp import MCP_SERVER


def _load_id3(filepath: str) -> tuple[Path, ID3]:
    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Expected a file path, got directory: {path}")

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    return path, tags


def _set_txxx_links(tags: ID3, links: dict[str, str] | None) -> None:
    tags.delall("TXXX:Links")
    if not links:
        return

    tags.add(TXXX(encoding=3, desc="Links", text=[json.dumps(links)]))


@MCP_SERVER.tool()
def add_id3_title(filepath: str, title: str | None) -> str:
    """Set or remove the ID3 title (`TIT2`) tag for a local audio file."""
    path, tags = _load_id3(filepath)

    if title is None or title == "":
        tags.delall("TIT2")
    else:
        tags.setall("TIT2", [TIT2(encoding=3, text=title)])

    tags.save(path)
    return f"Updated title tag for {path}"


@MCP_SERVER.tool()
def set_id3_artist(filepath: str, artists: list[str] | None) -> str:
    """Set or remove the ID3 artists (`TPE1`) tag for a local audio file."""
    path, tags = _load_id3(filepath)

    if not artists:
        tags.delall("TPE1")
    else:
        # Pass the list of artists directly to TPE1
        tags.setall("TPE1", [TPE1(encoding=3, text=artists)])

    tags.save(path)
    return f"Updated artist tag for {path}"


@MCP_SERVER.tool()
def set_id3_album(filepath: str, album: str | None) -> str:
    """Set or remove the ID3 album (`TALB`) tag for a local audio file."""
    path, tags = _load_id3(filepath)

    if album is None or album == "":
        tags.delall("TALB")
    else:
        tags.setall("TALB", [TALB(encoding=3, text=album)])

    tags.save(path)
    return f"Updated album tag for {path}"


@MCP_SERVER.tool()
def set_id3_year(filepath: str, year: str | None) -> str:
    """Set or remove the ID3 recording date/year (`TDRC`) tag for a local audio file."""
    path, tags = _load_id3(filepath)

    if year is None or year == "":
        tags.delall("TDRC")
    else:
        tags.setall("TDRC", [TDRC(encoding=3, text=year)])

    tags.save(path)
    return f"Updated year tag for {path}"


@MCP_SERVER.tool()
def set_id3_thumbnail(
    filepath: str, image_path: str, mime_type: str = "image/jpeg"
) -> str:
    """Embed a cover image into the file by replacing existing `APIC` thumbnail frames."""
    path, tags = _load_id3(filepath)
    cover_path = Path(image_path).expanduser().resolve()
    if not cover_path.exists():
        raise FileNotFoundError(f"Image not found: {cover_path}")
    if not cover_path.is_file():
        raise IsADirectoryError(
            f"Expected an image file path, got directory: {cover_path}"
        )

    image_data = cover_path.read_bytes()
    tags.delall("APIC")
    tags.add(
        APIC(
            encoding=3,
            mime=mime_type,
            type=3,
            desc="Cover",
            data=image_data,
        )
    )
    tags.save(path)
    return f"Embedded thumbnail from {cover_path} into {path}"


@MCP_SERVER.tool()
def set_id3_links(filepath: str, links: dict[str, str] | None) -> str:
    """
    Store or remove JSON-encoded external links in the custom `TXXX:Links` ID3 frame.
    The platform (key in links dictionary) should be lowercase
    """
    path, tags = _load_id3(filepath)
    _set_txxx_links(tags, links)
    tags.save(path)
    return f"Updated TXXX:Links tag for {path}"


@MCP_SERVER.tool()
def read_id3_tags(filepath: str) -> dict[str, str | list[str] | None]:
    """Read common ID3 fields and summarize title, artist, album, year, links, and artwork state."""
    path, tags = _load_id3(filepath)

    def _get_text(frame_id: str) -> list[str] | None:
        frame = tags.get(frame_id)
        if frame is None:
            return None
        text = getattr(frame, "text", None)
        if not text:
            return None
        return [str(t) for t in text]

    def _first_text(frame_id: str) -> str | None:
        text_list = _get_text(frame_id)
        return text_list[0] if text_list else None

    links_frame = tags.get("TXXX:Links")
    links = None
    if links_frame is not None and getattr(links_frame, "text", None):
        links = str(links_frame.text[0])

    return {
        "filepath": str(path),
        "title": _first_text("TIT2"),
        "artist": _get_text("TPE1"),
        "album": _first_text("TALB"),
        "year": _first_text("TDRC"),
        "links": links,
        "has_thumbnail": "yes" if tags.getall("APIC") else "no",
    }
