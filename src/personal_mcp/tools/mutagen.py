import json
from pathlib import Path

from mutagen.flac import FLAC, Picture
from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TDRC,
    TIT2,
    TPE1,
    TRCK,
    TXXX,
    ID3NoHeaderError,
)

from personal_mcp import MCP_SERVER

AudioTags = ID3 | FLAC


def _load_audio_tags(filepath: str) -> tuple[Path, AudioTags]:
    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Expected a file path, got directory: {path}")

    if path.suffix.lower() == ".flac":
        return path, FLAC(path)

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    return path, tags


def _save_audio_tags(path: Path, tags: AudioTags) -> None:
    if isinstance(tags, ID3):
        tags.save(path)
    else:
        tags.save()


def _set_links(tags: AudioTags, links: dict[str, str] | None) -> None:
    if isinstance(tags, FLAC):
        if "links" in tags:
            del tags["links"]
        if links:
            tags["links"] = [json.dumps(links)]
        return

    tags.delall("TXXX:Links")
    if not links:
        return

    tags.add(TXXX(encoding=3, desc="Links", text=[json.dumps(links)]))


def _get_links(tags: AudioTags) -> dict[str, str]:
    if isinstance(tags, FLAC):
        links_text = tags.get("links")
        if not links_text:
            return {}

        links = json.loads(str(links_text[0]))
        if not isinstance(links, dict):
            raise ValueError("Expected links to contain a JSON object")

        return links

    links_frame = tags.get("TXXX:Links")
    if links_frame is None or not getattr(links_frame, "text", None):
        return {}

    links = json.loads(str(links_frame.text[0]))
    if not isinstance(links, dict):
        raise ValueError("Expected TXXX:Links to contain a JSON object")

    return links


def _set_flac_text(tags: FLAC, key: str, values: list[str] | None) -> None:
    if not values:
        if key in tags:
            del tags[key]
        return

    tags[key] = values


def _handle_title(tags: AudioTags, title: str | None):
    if isinstance(tags, FLAC):
        _set_flac_text(tags, "title", [title] if title else None)
        return

    if title is None or title == "":
        tags.delall("TIT2")
    else:
        tags.setall("TIT2", [TIT2(encoding=3, text=title)])


def _handle_artists(tags: AudioTags, artists: list[str] | None):
    if isinstance(tags, FLAC):
        _set_flac_text(tags, "artist", artists)
        return

    if not artists:
        tags.delall("TPE1")
    else:
        tags.setall("TPE1", [TPE1(encoding=3, text=artists)])


def _handle_album(tags: AudioTags, album: str | None):
    if isinstance(tags, FLAC):
        _set_flac_text(tags, "album", [album] if album else None)
        return

    if album is None or album == "":
        tags.delall("TALB")
    else:
        tags.setall("TALB", [TALB(encoding=3, text=album)])


def _handle_year(tags: AudioTags, year: str | None):
    if isinstance(tags, FLAC):
        _set_flac_text(tags, "date", [year] if year else None)
        return

    if year is None or year == "":
        tags.delall("TDRC")
    else:
        tags.setall("TDRC", [TDRC(encoding=3, text=year)])


def _handle_track_number(tags: AudioTags, track_number: str | None):
    if isinstance(tags, FLAC):
        _set_flac_text(tags, "tracknumber", [track_number] if track_number else None)
        return

    if track_number is None or track_number == "":
        tags.delall("TRCK")
    else:
        tags.setall("TRCK", [TRCK(encoding=3, text=track_number)])


@MCP_SERVER.tool()
def set_id3_tags(
    filepath: str,
    title: str | None,
    artists: list[str] | None,
    album: str | None,
    year: str | None,
    track_number: str | None,
) -> str:
    """
    Sets the audio tags corresponding to the non-null given inputs
    for a local MP3 or FLAC file.

    - title: TIT2 ID3 frame or FLAC title field
    - artists: TPE1 ID3 frame or FLAC artist field
    - album: TALB ID3 frame or FLAC album field
    - year: TDRC ID3 frame or FLAC date field
    - track_number: TRCK ID3 frame or FLAC tracknumber field

    If any input is passed as null (or falsy value), then it will not
    be modified.
    """
    path, tags = _load_audio_tags(filepath)

    modified_tags = []

    if title:
        modified_tags.append("title")
        _handle_title(tags, title)

    if artists:
        modified_tags.append("artists")
        _handle_artists(tags, artists)

    if album:
        modified_tags.append("album")
        _handle_album(tags, album)

    if year:
        modified_tags.append("year")
        _handle_year(tags, year)

    if track_number:
        modified_tags.append("track_number")
        _handle_track_number(tags, track_number)

    _save_audio_tags(path, tags)

    return f"Modified Fields: {','.join(modified_tags)}"


@MCP_SERVER.tool()
def unset_id3_tags(
    filepath: str,
    title: bool,
    artists: bool,
    album: bool,
    year: bool,
    track_number: bool,
) -> str:
    """
    Deletes the tags which are passed as `true` in the inputs for a local MP3 or FLAC file.

    - title: TIT2 ID3 frame or FLAC title field
    - artists: TPE1 ID3 frame or FLAC artist field
    - album: TALB ID3 frame or FLAC album field
    - year: TDRC ID3 frame or FLAC date field
    - track_number: TRCK ID3 frame or FLAC tracknumber field
    """
    path, tags = _load_audio_tags(filepath)

    deleted_tags = []

    if title:
        deleted_tags.append("title")
        _handle_title(tags, None)

    if artists:
        deleted_tags.append("artists")
        _handle_artists(tags, None)

    if album:
        deleted_tags.append("album")
        _handle_album(tags, None)

    if year:
        deleted_tags.append("year")
        _handle_year(tags, None)

    if track_number:
        deleted_tags.append("track_number")
        _handle_track_number(tags, None)

    _save_audio_tags(path, tags)

    return f"Deleted Fields: {','.join(deleted_tags)}"


@MCP_SERVER.tool()
def set_id3_thumbnail(
    filepath: str, image_path: str, mime_type: str = "image/jpeg"
) -> str:
    """Embed a cover image by replacing existing ID3 APIC frames or FLAC pictures."""
    path, tags = _load_audio_tags(filepath)
    cover_path = Path(image_path).expanduser().resolve()
    if not cover_path.exists():
        raise FileNotFoundError(f"Image not found: {cover_path}")
    if not cover_path.is_file():
        raise IsADirectoryError(
            f"Expected an image file path, got directory: {cover_path}"
        )

    image_data = cover_path.read_bytes()
    if isinstance(tags, FLAC):
        picture = Picture()
        picture.type = 3
        picture.mime = mime_type
        picture.desc = "Cover"
        picture.data = image_data
        tags.clear_pictures()
        tags.add_picture(picture)
        _save_audio_tags(path, tags)
        return f"Embedded thumbnail from {cover_path} into {path}"

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
    _save_audio_tags(path, tags)
    return f"Embedded thumbnail from {cover_path} into {path}"


@MCP_SERVER.tool()
def set_id3_links(filepath: str, links: dict[str, str] | None) -> str:
    """
    Store or remove JSON-encoded external links in an MP3 `TXXX:Links` frame or FLAC `links` field.
    The platform (key in links dictionary) should be lowercase
    """
    path, tags = _load_audio_tags(filepath)
    merged_links = None if links is None else {**_get_links(tags), **links}
    _set_links(tags, merged_links)
    _save_audio_tags(path, tags)
    return f"Updated links tag for {path}"


@MCP_SERVER.tool()
def read_id3_tags(filepath: str) -> dict[str, str | list[str] | None]:
    """Read common MP3 or FLAC fields and summarize title, artist, album, year, track number, links, and artwork state."""
    path, tags = _load_audio_tags(filepath)

    def _get_text(frame_id: str) -> list[str] | None:
        if isinstance(tags, FLAC):
            values = tags.get(frame_id)
            return [str(v) for v in values] if values else None

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

    links = None
    if isinstance(tags, FLAC):
        links_text = tags.get("links")
        if links_text:
            links = str(links_text[0])
    else:
        links_frame = tags.get("TXXX:Links")
        if links_frame is not None and getattr(links_frame, "text", None):
            links = str(links_frame.text[0])

    return {
        "filepath": str(path),
        "title": _first_text("title" if isinstance(tags, FLAC) else "TIT2"),
        "artist": _get_text("artist" if isinstance(tags, FLAC) else "TPE1"),
        "album": _first_text("album" if isinstance(tags, FLAC) else "TALB"),
        "year": _first_text("date" if isinstance(tags, FLAC) else "TDRC"),
        "track_number": _first_text("tracknumber" if isinstance(tags, FLAC) else "TRCK"),
        "links": links,
        "has_thumbnail": (
            "yes"
            if (tags.pictures if isinstance(tags, FLAC) else tags.getall("APIC"))
            else "no"
        ),
    }
