# AGENTS.md — YouTube2Audio

Long-term knowledge for AI agents and maintainers. Not a task tracker or changelog.

---

## Project Context

**YouTube2Audio** is a Windows desktop application that downloads YouTube videos and playlists as audio files. It wraps `yt-dlp` behind a modern GUI, supporting single videos, playlists, and YouTube Shorts/Music URLs. Intended for personal use on Windows 11.

---

## Architecture

The app follows a clean layered architecture:

```
main.py
└── src/app.py          # QApplication setup, theming, entry point
    └── src/ui/main_window.py  # MainWindow — orchestrates all panels and managers
        ├── src/core/download_manager.py   # Queue, concurrency, retry logic (QObject)
        ├── src/core/download_worker.py    # One QThread per active download
        ├── src/core/url_resolver.py       # URL resolution in a QThread
        ├── src/core/ytdlp_wrapper.py      # All yt-dlp calls (no Qt here)
        ├── src/ui/download_panel.py       # Left panel — queue list
        ├── src/ui/status_panel.py         # Right panel — log output
        ├── src/ui/url_input_bar.py        # URL entry widget
        ├── src/ui/settings_dialog.py      # Audio format/bitrate/concurrency dialog
        └── src/services/settings_service.py  # QSettings persistence
```

**Key design decisions:**

- `DownloadManager` is a `QObject` living on the main thread; it orchestrates workers via Qt signals and never blocks the UI.
- Each download runs in its own `QThread` (`DownloadWorker`). Workers emit signals; they never touch UI widgets directly.
- URL resolution (metadata fetch) also runs in a `QThread` (`UrlResolverWorker`) to avoid freezing on slow network lookups.
- `ytdlp_wrapper.py` is the sole boundary between the application and `yt-dlp`. All yt-dlp API calls live here.
- `src/services/` is reserved for I/O-layer services (currently just `settings_service.py`); keep yt-dlp calls in `src/core/`.

---

## Project Structure

| Path | Responsibility |
|------|---------------|
| `main.py` | CLI entry point — adds `src` to `sys.path`, calls `src.app.run()` |
| `src/app.py` | Creates `QApplication`, applies dark stylesheet, loads icon, launches `MainWindow` |
| `src/core/models.py` | `VideoItem` dataclass and `DownloadStatus` enum; `AppSettings` dataclass |
| `src/core/ytdlp_wrapper.py` | `extract_metadata()`, `download_audio()`, `DownloadCancelled` exception |
| `src/core/url_resolver.py` | `UrlResolverWorker(QThread)` — calls `extract_metadata` off the main thread |
| `src/core/download_worker.py` | `DownloadWorker(QThread)` — calls `download_audio` off the main thread |
| `src/core/download_manager.py` | `DownloadManager(QObject)` — queue, concurrency cap, retry timers |
| `src/ui/main_window.py` | Top-level window; wires all signals; handles drag-and-drop, URL parsing |
| `src/ui/download_panel.py` | Left panel: scrollable list of `VideoItem` rows |
| `src/ui/status_panel.py` | Right panel: scrollable log text |
| `src/ui/url_input_bar.py` | Input field + Add button; emits `url_submitted` signal |
| `src/ui/settings_dialog.py` | Modal dialog for audio format, bitrate, concurrent download limit |
| `src/ui/styles.py` | `DARK_STYLESHEET` — single global dark-mode QSS string |
| `src/services/settings_service.py` | `load_settings()` / `save_settings()` via `QSettings` |
| `src/utils/constants.py` | App-wide constants: URLs patterns, format lists, defaults |
| `src/utils/validators.py` | `is_valid_youtube_url()`, `extract_urls_from_text()` |
| `src/utils/formatters.py` | Human-readable size/speed/time formatters |
| `music.ico` | App window icon; bundled with PyInstaller via `sys._MEIPASS` path |

---

## Data / Storage Layer

### Read-only Data
None — all data is fetched at runtime from YouTube via yt-dlp.

### Writable Data
- **Downloaded audio files**: written to the user-selected output folder (`%(title)s.%(ext)s` naming via yt-dlp's `outtmpl`).
- **Settings**: persisted via `QSettings` using org name `"YouTube2Audio"` and app name `"YouTube2Audio"`. On Windows this writes to the registry under `HKCU\Software\YouTube2Audio\YouTube2Audio`. Stored keys: `output_folder`, `audio_format`, `audio_bitrate`, `max_concurrent`, `window_geometry`, `splitter_state`.

### Generated Data
- `.pyc` cache files in `src/**/__pycache__/`; safe to delete.

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **PySide6** (not PyQt6, Tkinter, or wxPython) | Official Qt binding under LGPL; best Windows HiDPI support; modern signal/slot system; PyInstaller-friendly |
| **yt-dlp** (not youtube-dl) | Actively maintained fork; better playlist and format support |
| **QThread per download** | Keeps UI fully responsive; simpler cancellation via `_cancelled` flag checked in progress hook |
| **`DownloadCancelled` exception** | Clean mechanism to interrupt yt-dlp's blocking `ydl.download()` call from inside the progress hook |
| **Placeholder item pattern** | When a URL is submitted, a `RESOLVING` placeholder is added immediately so the UI feels instant; it's updated or replaced after metadata resolution completes |
| **`extract_flat=True` for metadata** | Fast playlist extraction without downloading each video's full metadata page |
| **Playlist URL normalization** | URLs containing `list=` are rewritten to `youtube.com/playlist?list=...` before extraction to reliably get all playlist entries |
| **`QSettings` for persistence** | Zero-dependency; integrates naturally with PySide6; survives app restarts |
| **Dark stylesheet via QSS** | Single string in `styles.py`; applied once at startup; avoids per-widget palette management |

---

## Conventions

- **GUI framework**: PySide6 throughout — do not mix with PyQt6 or add tkinter.
- **Threading**: UI updates only on the main thread via Qt signals. Workers never access Qt widgets directly.
- **yt-dlp isolation**: All yt-dlp imports and calls stay in `src/core/ytdlp_wrapper.py`. No direct `import yt_dlp` elsewhere.
- **Constants**: Add app-wide magic values to `src/utils/constants.py`, not inline.
- **Settings persistence**: Use `settings_service.py` functions; do not instantiate `QSettings` directly outside that module.
- **No comments on obvious code**: Follow the project convention of sparse comments; only document non-obvious constraints or workarounds.
- **Python 3.12**: Codebase uses `int | None` union syntax and `dataclass` field defaults — requires Python 3.10+.

---

## Known Constraints

- **Windows-only**: App is designed and tested on Windows 11. No macOS/Linux paths have been validated (path separators, icon loading, `QStandardPaths` defaults may differ).
- **FFmpeg required for MP3 and bitrate conversion**: yt-dlp's `FFmpegExtractAudio` postprocessor requires `ffmpeg.exe` to be on `PATH` or bundled. m4a best-audio download works without FFmpeg.
- **No persistent download queue**: The queue is in-memory only; closing the app discards all queued/downloading items.
- **Cancellation is cooperative**: `DownloadWorker.cancel()` sets a flag; yt-dlp checks it inside the progress hook. Very large downloads may take a moment to actually stop.
- **PyInstaller packaging**: `music.ico` must be added to the PyInstaller `--add-data` list. The `sys._MEIPASS` path is already handled in `src/app.py`.

---

## Project History & Previous Decisions

- **v1.0.0** is the initial public release (commit `c3d486b`). The architecture was designed from scratch; no prior codebase was migrated.
- The `src/services/` package was created with future services in mind (e.g., update checking, analytics). Currently only `settings_service.py` lives there.

---

## Rules For Future Agents

1. Read the relevant source files before making assumptions about behavior — especially `ytdlp_wrapper.py` for download logic and `download_manager.py` for queue/retry behavior.
2. Do not add direct `yt_dlp` imports outside `src/core/ytdlp_wrapper.py`.
3. Do not update UI widgets from worker threads — always use Qt signals.
4. When adding new settings, update both `AppSettings` in `models.py` and `settings_service.py` together.
5. Keep `src/utils/constants.py` as the single source of truth for magic values.
6. Update this file when architecture changes, new modules are added, or important technical decisions are made.
