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


def _get_txxx_links(tags: ID3) -> dict[str, str]:
    links_frame = tags.get("TXXX:Links")
    if links_frame is None or not getattr(links_frame, "text", None):
        return {}

    links = json.loads(str(links_frame.text[0]))
    if not isinstance(links, dict):
        raise ValueError("Expected TXXX:Links to contain a JSON object")

    return links


def _handle_id3_title(tags: ID3, title: str | None):
    if title is None or title == "":
        tags.delall("TIT2")
    else:
        tags.setall("TIT2", [TIT2(encoding=3, text=title)])


def _handle_id3_artists(tags: ID3, artists: list[str] | None):
    if not artists:
        tags.delall("TPE1")
    else:
        tags.setall("TPE1", [TPE1(encoding=3, text=artists)])


def _handle_id3_album(tags: ID3, album: str | None):
    if album is None or album == "":
        tags.delall("TALB")
    else:
        tags.setall("TALB", [TALB(encoding=3, text=album)])


def _handle_id3_year(tags: ID3, year: str | None):
    if year is None or year == "":
        tags.delall("TDRC")
    else:
        tags.setall("TDRC", [TDRC(encoding=3, text=year)])


@MCP_SERVER.tool()
def set_id3_tags(
    filepath: str,
    title: str | None,
    artists: list[str] | None,
    album: str | None,
    year: str | None,
) -> str:
    """
    Sets the ID3 tags corresponding to the non-null given inputs
    for a local audio file.

    - title: TIT2 tag
    - artists: TPE1 tag
    - album: TALB tag
    - year: TDRC tag

    If any input is passed as null (or falsy value), then it will not
    be modified.
    """
    path, tags = _load_id3(filepath)

    modified_tags = []

    if title:
        modified_tags.append("title")
        _handle_id3_title(tags, title)

    if artists:
        modified_tags.append("artists")
        _handle_id3_artists(tags, artists)

    if album:
        modified_tags.append("album")
        _handle_id3_album(tags, album)

    if year:
        modified_tags.append("year")
        _handle_id3_year(tags, year)

    tags.save(path)

    return f"Modified Fields: {','.join(modified_tags)}"


@MCP_SERVER.tool()
def unset_id3_tags(
    filepath: str,
    title: bool,
    artists: bool,
    album: bool,
    year: bool,
) -> str:
    """
    Deletes the tags which are passed as `true` in the inputs for a local audio file.

    - title: TIT2 tag
    - artists: TPE1 tag
    - album: TALB tag
    - year: TDRC tag
    """
    path, tags = _load_id3(filepath)

    deleted_tags = []

    if title:
        deleted_tags.append("title")
        _handle_id3_title(tags, None)

    if artists:
        deleted_tags.append("artists")
        _handle_id3_artists(tags, None)

    if album:
        deleted_tags.append("album")
        _handle_id3_album(tags, None)

    if year:
        deleted_tags.append("year")
        _handle_id3_year(tags, None)

    tags.save(path)

    return f"Deleted Fields: {','.join(deleted_tags)}"


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
    merged_links = None if links is None else {**_get_txxx_links(tags), **links}
    _set_txxx_links(tags, merged_links)
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
