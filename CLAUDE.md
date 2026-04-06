# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses uv)
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run the application
python main.py
```

No build step, test suite, or linter is configured.

## Architecture

**CoomerDL** is a PySide6 desktop app for downloading media from Coomer, Kemono, Erome, Bunkr, SimpCity, and JPG5.

### Layer separation

```
UI Layer (app/)          ←→ via FrontendBridge ←→     Downloader Layer (downloader/)
PySide6 widgets                                         Site-specific logic, threading
```

The downloader layer is UI-agnostic — it never imports PySide6. It communicates back to the UI exclusively through the `FrontendBridge` abstract interface (`app/interfaces/frontend_bridge.py`), implemented by `PySideFrontendBridge` (`app/adapters/pyside_frontend_bridge.py`).

### Key flows

- `main.py` → `PySideMainWindow` → `MainController.start_download()`
- `MainController` parses a `DownloadRequest`, picks a downloader via `DownloaderFactory`, spawns a daemon thread
- Downloader uses a `ThreadPoolExecutor` + per-domain `Semaphore` for concurrent, rate-limited downloads
- Progress/log callbacks flow back via Qt Signals (thread-safe queued connection)
- `cancel_event = threading.Event()` is polled in the download loop; call `active_downloader.request_cancel()` to stop

### Downloader structure

Each site has a downloader class (e.g., `downloader/bunkr.py`) that extends `BaseApiDownloader` (`downloader/core/base_api_downloader.py`) and wraps a corresponding adapter (e.g., `downloader/adapters/bunkr_adapter.py`) for scraping/API logic. `DownloaderFactory` (`app/adapters/downloader_factory.py`) instantiates the correct one.

### State & config

- `AppState` (`app/models/app_state.py`) — runtime state (current downloader, thread, flags)
- `SettingsService` (`app/services/settings_service.py`) — persists `resources/config/settings.json`
- `TranslationService` (`app/services/translation_service.py`) — key-based i18n, falls back to English; files in `resources/config/i18n/`
- `downloads.db` — SQLite, used to skip already-downloaded files

### Progress tracking

`ProgressStore` holds per-file progress keyed by a unique file key. `ProgressLogic` contains pure calculation logic. The `ProgressDialog` consumes both.
