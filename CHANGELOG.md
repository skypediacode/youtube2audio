# Changelog

All notable changes to YouTube2Audio are documented here.

---

## [1.1.0] - 2026-06-09

### Fixed
- **Audio-only output** — downloads now always produce the selected audio format (M4A, MP3, etc.) instead of occasionally saving an MP4 video file. The format selector fallback `/best` was silently picking combined video+audio streams; replaced with a guaranteed `FFmpegExtractAudio` postprocessor pipeline.

---

## [1.0.0] - 2026-06-07

### Initial release

- Drag & drop YouTube URLs from your browser
- Playlist support — auto-expands playlists into individual tracks
- Concurrent downloads (1–10 simultaneous)
- Real-time progress bars, download speed, and ETA
- Pause / Resume downloads
- Auto retry on failure (up to 3 times)
- Audio formats: M4A, MP3, Opus, WAV
- Bitrate selection: 128, 192, 256, 320 kbps or best available
- Dark theme UI
- Persistent settings between sessions
