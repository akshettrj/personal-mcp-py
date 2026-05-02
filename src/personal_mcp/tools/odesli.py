from typing import Any

from odesli.Odesli import Odesli
from requests import RequestException

from personal_mcp import MCP_SERVER

ODESLI_CLIENT = Odesli()


def _entity_to_dict(entity: Any) -> dict[str, Any] | None:
    if entity is None:
        return None

    return {
        "id": entity.id,
        "type": entity.getType(),
        "provider": entity.provider,
        "title": entity.title,
        "artist_name": entity.artistName,
        "thumbnail_url": entity.thumbnailUrl,
        "thumbnail_width": entity.thumbnailWidth,
        "thumbnail_height": entity.thumbnailHeight,
        "links_by_platform": entity.linksByPlatform,
    }


def _result_to_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "songLink"):
        entity_type = "song"
        page_url = result.songLink
        requested_entity = result.song
        entities_by_provider = result.songsByProvider
    elif hasattr(result, "albumLink"):
        entity_type = "album"
        page_url = result.albumLink
        requested_entity = result.album
        entities_by_provider = result.albumsByProvider
    else:
        raise TypeError(f"Unsupported Odesli result type: {type(result).__name__}")

    links_by_platform = {}
    for entity in entities_by_provider.values():
        links_by_platform.update(entity.linksByPlatform)

    return {
        "type": entity_type,
        "page_url": page_url,
        "requested_entity": _entity_to_dict(requested_entity),
        "entities_by_provider": {
            provider: _entity_to_dict(entity)
            for provider, entity in entities_by_provider.items()
        },
        "links_by_platform": links_by_platform,
    }


def _odesli_error(error: Exception) -> dict[str, str]:
    return {"error": f"{type(error).__name__}: {error}"}


@MCP_SERVER.tool()
def odesli_get_by_url(url: str) -> dict[str, Any]:
    """Get results from Odesli API for a given URL."""
    try:
        return _result_to_dict(ODESLI_CLIENT.getByUrl(url))
    except (
        RequestException,
        KeyError,
        NotImplementedError,
        TypeError,
        ValueError,
    ) as e:
        return _odesli_error(e)


@MCP_SERVER.tool()
def odesli_get_by_id(id: str, platform: str, type: str) -> dict[str, Any]:
    """
    Get results from Odesli API for a platform entity ID.

    Args:
        id: Entity ID on the source platform.
        platform: Source platform, for example spotify, appleMusic, youtube, or youtubeMusic.
        type: Entity type, either song or album.
    """
    try:
        return _result_to_dict(ODESLI_CLIENT.getById(id, platform, type))
    except (
        RequestException,
        KeyError,
        NotImplementedError,
        TypeError,
        ValueError,
    ) as e:
        return _odesli_error(e)
