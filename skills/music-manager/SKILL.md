---
name: music-manager
description: Downloads and Tags new music files using yt-dlp, FFmpeg, and ID3 tools. Use this skill when the user provides a music URL (YouTube/SoundCloud) and wants a high-quality MP3 with proper metadata and artwork.
---
<MUSIC_MANAGER_SKILL>
When provided with a music URL (e.g. from YouTube), download the music file using the tools provided in the `personal-py` MCP server and tag it appropriately.

### Workflow
1.  **Inspect**: Use `get_music_metadata` (for single tracks) or `get_playlist_metadata` (for playlists) to retrieve the title, uploader, and structure of the content.
2.  **Download & Convert**: Use the `download_music` tool. This tool autonomously handles the download of the best audio format, manual conversion to high-quality MP3 (320kbps) via FFmpeg, and initial tagging (Title, Uploader as Artist, and Thumbnail).
3.  **Refine Metadata**: Use a web search to find the official Artist(s), Album, and Year.
4.  **Final Tagging**: Use the ID3 tagging tools to apply the refined metadata.
    - **Note**: `set_id3_artist` now accepts a **list of strings** to support multiple artists.
    - Always add the `link` tag (using `set_id3_links`) to store the original URL.
    - **Note**: Do not parallelize the ID3 tag tools for a single file to prevent file lock issues. They can be parallelized for different music files.
5.  **Rename**: The final file name should be just the `Title.{extension}`.

### Guidelines
- **Playlists**: If a playlist URL is provided, use `get_playlist_metadata` first. Compare the entries with the files already present in your target directory and only download the missing ones (you can call `download_music` with `noplaylist=True` in a loop for each missing song).
- **Thumbnails**: The `download_music` tool already embeds the best available thumbnail into the MP3. You only need to manually update it if you find better artwork during your search.
- **Album Names**: Ensure the album name does not redundantly contain the song title.
- **Artists**: Always prefer a list of actual artists over the YouTube uploader name when found via web search.

<CLASSICAL>
If the song is a classical performance (e.g., Ustad Nusrat Fateh Ali Khan's qawwali):
- Omit the album tag unless downloading a full performance/show playlist.
- For full show playlists, the album name should be: `[Location] ([Year])` if available.
- Rely on the metadata provided in the video title/description more than general web searches, as many different versions of these performances exist.
<CLASSICAL/>
</MUSIC_MANAGER_SKILL>
