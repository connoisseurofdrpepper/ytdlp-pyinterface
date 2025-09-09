# presets.py
# Full translation of TheFrenchGhosty's Ultimate YouTube-DL Scripts Collection

from typing import List, Dict

GHOSTY_PRESETS: Dict[str, List[str]] = {
    # === ARCHIVIST SCRIPTS ===
    "Archivist - Channels": [
        "--format", "bestvideo+bestaudio/best",
        "--verbose", "--force-ipv4",
        "--sleep-requests", "1", "--sleep-interval", "5", "--max-sleep-interval", "30",
        "--ignore-errors", "--no-continue", "--no-overwrites",
        "--download-archive", "archive.log",
        "--add-metadata",
        "--parse-metadata", "%(title)s:%(meta_title)s",
        "--parse-metadata", "%(uploader)s:%(meta_artist)s",
        "--write-description", "--write-info-json", "--write-annotations",
        "--write-thumbnail", "--embed-thumbnail",
        "--all-subs", "--embed-subs",
        "--check-formats", "--concurrent-fragments", "5",
        "--match-filter", "!is_live & !live",
        "--output", "%(uploader)s/%(uploader)s - %(upload_date)s - %(title)s/%(uploader)s - %(upload_date)s - %(title)s [%(id)s].%(ext)s",
        "--merge-output-format", "mkv",
        "--throttled-rate", "100K",
        "--batch-file", "Source - Channels.txt"
    ],
    "Archivist - Playlists": [
        "--format", "bestvideo+bestaudio/best",
        "--verbose", "--force-ipv4",
        "--sleep-requests", "1", "--sleep-interval", "5", "--max-sleep-interval", "30",
        "--ignore-errors", "--no-continue", "--no-overwrites",
        "--download-archive", "archive.log",
        "--add-metadata",
        "--parse-metadata", "%(title)s:%(meta_title)s",
        "--parse-metadata", "%(uploader)s:%(meta_artist)s",
        "--write-description", "--write-info-json", "--write-annotations",
        "--write-thumbnail", "--embed-thumbnail",
        "--all-subs", "--embed-subs",
        "--check-formats", "--concurrent-fragments", "5",
        "--match-filter", "!is_live & !live",
        "--output", "%(playlist)s - (%(uploader)s)/%(upload_date)s - %(title)s/%(upload_date)s - %(title)s [%(id)s].%(ext)s",
        "--merge-output-format", "mkv",
        "--throttled-rate", "100K",
        "--batch-file", "Source - Playlists.txt"
    ],
    "Archivist - Unique": [
        "--format", "bestvideo+bestaudio/best",
        "--verbose", "--force-ipv4",
        "--sleep-requests", "1", "--sleep-interval", "5", "--max-sleep-interval", "30",
        "--ignore-errors", "--no-continue", "--no-overwrites",
        "--download-archive", "archive.log",
        "--add-metadata",
        "--parse-metadata", "%(title)s:%(meta_title)s",
        "--parse-metadata", "%(uploader)s:%(meta_artist)s",
        "--write-description", "--write-info-json", "--write-annotations",
        "--write-thumbnail", "--embed-thumbnail",
        "--all-subs", "--embed-subs",
        "--check-formats", "--concurrent-fragments", "5",
        "--match-filter", "!is_live & !live",
        "--output", "%(title)s - %(uploader)s - %(upload_date)s/%(title)s - %(uploader)s - %(upload_date)s [%(id)s].%(ext)s",
        "--merge-output-format", "mkv",
        "--throttled-rate", "100K",
        "--batch-file", "Source - Unique.txt"
    ],

    # === AUDIO-ONLY ===
    "Audio Only - Best Quality": [
        "--format", "(bestaudio[acodec^=opus]/bestaudio)/best",
        "--verbose", "--force-ipv4",
        "--sleep-requests", "1", "--sleep-interval", "5", "--max-sleep-interval", "30",
        "--ignore-errors", "--no-continue", "--no-overwrites",
        "--download-archive", "archive.log",
        "--add-metadata",
        "--parse-metadata", "%(title)s:%(meta_title)s",
        "--parse-metadata", "%(uploader)s:%(meta_artist)s",
        "--extract-audio", "--check-formats",
        "--concurrent-fragments", "5",
        "--output", "%(uploader)s - %(upload_date)s - %(title)s [%(id)s].%(ext)s",
        "--throttled-rate", "100K",
        "--batch-file", "Source - Audio Only.txt"
    ],

    # === VIDEO SCRIPTS ===
    "Video - Mobile Devices": [
        "--format", "(bestvideo[vcodec^=avc1][height<=1080][fps<=30]/bestvideo[vcodec^=avc1][height<=720]/bestvideo[vcodec^=avc1][height<=480]/bestvideo[vcodec^=avc1][height<=360])+(bestaudio[acodec^=mp4a]/bestaudio)/best",
        "--verbose", "--force-ipv4",
        "--ignore-errors", "--no-continue", "--no-overwrites",
        "--download-archive", "archive.log",
        "--add-metadata",
        "--parse-metadata", "%(title)s:%(meta_title)s",
        "--parse-metadata", "%(uploader)s:%(meta_artist)s",
        "--all-subs", "--embed-subs",
        "--check-formats", "--concurrent-fragments", "5",
        "--output", "%(uploader)s - %(upload_date)s - %(title)s [%(id)s].%(ext)s",
        "--merge-output-format", "mkv",
        "--throttled-rate", "100K",
        "--batch-file", "Source - Video.txt"
    ],
    "Video - PC": [
        "--format", "bestvideo+bestaudio/best",
        "--verbose", "--force-ipv4",
        "--ignore-errors", "--no-continue", "--no-overwrites",
        "--download-archive", "archive.log",
        "--add-metadata",
        "--parse-metadata", "%(title)s:%(meta_title)s",
        "--parse-metadata", "%(uploader)s:%(meta_artist)s",
        "--all-subs", "--embed-subs",
        "--check-formats", "--concurrent-fragments", "5",
        "--output", "%(uploader)s - %(upload_date)s - %(title)s [%(id)s].%(ext)s",
        "--merge-output-format", "mkv",
        "--throttled-rate", "100K",
        "--batch-file", "Source - Video.txt"
    ],

    # === CHECK SCRIPTS ===
    "Check Unavailability": [
        "--verbose", "--force-ipv4",
        "--ignore-errors", "--no-continue", "--no-overwrites",
        "--download-archive", "archive.log",
        "--add-metadata",
        "--parse-metadata", "%(title)s:%(meta_title)s",
        "--parse-metadata", "%(uploader)s:%(meta_artist)s",
        "--skip-download",
        "--write-info-json",
        "--output", "check/%(uploader)s/%(upload_date)s - %(title)s [%(id)s].%(ext)s",
        "--batch-file", "Source - Check.txt"
    ],
}

def list_presets():
    return list(GHOSTY_PRESETS.keys())

def preset_args(name: str) -> List[str]:
    # Return a copy to prevent modification of the original list
    return GHOSTY_PRESETS.get(name, []).copy()