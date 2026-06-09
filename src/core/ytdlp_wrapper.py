import yt_dlp
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class DownloadCancelled(Exception):
    pass


def _normalize_playlist_url(url: str) -> tuple[str, bool]:
    """If URL contains a list= parameter, convert to a playlist URL.
    Returns (url, is_playlist)."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    list_id = params.get("list", [None])[0]
    if list_id:
        playlist_url = urlunparse((
            parsed.scheme, parsed.netloc, "/playlist",
            "", urlencode({"list": list_id}), "",
        ))
        return playlist_url, True
    return url, False


def extract_metadata(url: str) -> list[dict]:
    """Extract metadata for a URL. Returns a list of dicts (one per video, multiple for playlists)."""
    playlist_url, is_playlist = _normalize_playlist_url(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "ignoreerrors": True,
    }

    # Extract playlist first if URL had list= parameter
    if is_playlist:
        results = _extract_playlist(playlist_url, ydl_opts)
        if results:
            return results

    # Fall back to single video extraction
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info is None:
            return []
        return [{
            "url": info.get("webpage_url") or info.get("url", url),
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration"),
        }]


def _extract_playlist(playlist_url: str, ydl_opts: dict) -> list[dict]:
    """Extract all entries from a playlist URL."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        if info is None or "entries" not in info:
            return []

        results = []
        for entry in info["entries"]:
            if entry is None:
                continue
            entry_url = entry.get("url", "")
            if entry_url and not entry_url.startswith("http"):
                entry_url = f"https://www.youtube.com/watch?v={entry_url}"
            results.append({
                "url": entry.get("webpage_url") or entry_url,
                "title": entry.get("title", "Unknown"),
                "duration": entry.get("duration"),
            })
        return results


def download_audio(
    url: str,
    output_dir: str,
    audio_format: str = "m4a",
    audio_bitrate: str = "0",
    progress_hook=None,
    cancel_flag=None,
) -> str:
    """Download audio from a URL. Returns the path of the downloaded file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outtmpl = str(output_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "continuedl": True,
        "noprogress": True,
        "noplaylist": True,
    }

    # Always remux/re-encode to the requested audio format so the output
    # extension is correct regardless of which stream yt-dlp selected.
    ydl_opts["postprocessors"] = [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": audio_format,
        "preferredquality": audio_bitrate if audio_bitrate != "0" else "0",
    }]

    downloaded_file = None

    def _progress_hook(d):
        nonlocal downloaded_file
        if cancel_flag and cancel_flag():
            raise DownloadCancelled("Download cancelled by user")

        if d["status"] == "downloading":
            if progress_hook:
                progress_hook({
                    "status": "downloading",
                    "downloaded_bytes": d.get("downloaded_bytes", 0),
                    "total_bytes": d.get("total_bytes") or d.get("total_bytes_estimate"),
                    "speed": d.get("speed"),
                    "eta": d.get("eta"),
                })
        elif d["status"] == "finished":
            downloaded_file = d.get("filename", "")
            if progress_hook:
                progress_hook({
                    "status": "finished",
                    "filename": downloaded_file,
                })

    ydl_opts["progress_hooks"] = [_progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return downloaded_file or ""
