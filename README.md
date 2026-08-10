![Windows Compatibility](https://img.shields.io/badge/Windows-10%2C%2011-blue)
![Downloads](https://img.shields.io/github/downloads/emy69/CoomerDL/total)

# CoomerDL

**CoomerDL** is a desktop app for Windows that downloads images, videos, and files from supported websites. You paste a URL, pick a folder, and the app downloads everything for you — with progress bars, retries, and a database that prevents downloading the same file twice.

Built with Python and a modern **PySide6 (Qt)** interface.

---

## Supported sites

| Site | Status | Notes |
|------|--------|-------|
| [coomerfans.com](https://coomerfans.com/) | ✅ Working | Alternative to Coomer |
| [pawchive.pw](https://pawchive.pw/) | ✅ Working | Alternative to Kemono |
| [erome.com](https://www.erome.com/) | ✅ Working | Albums and profiles |
| [bunkr](https://bunkr-albums.io/) | ✅ Working | Any bunkr domain (bunkr.si, bunkr.site, etc.) |
| [simpcity.cr](https://simpcity.cr/) | ✅ Working | May require cookies (see [Cookies](#simpcity-cookies)) |
| ~~coomer.st~~ | ❌ Not working | The site blocks the app — use **coomerfans.com** instead |
| ~~kemono.cr~~ | ❌ Not working | The site blocks the app — use **pawchive.pw** instead |
| ~~jpg5.su~~ | ❌ Not working | Downloads from this site currently fail |

> **Note:** Sites marked ❌ no longer work with the app. If you paste one of their URLs, the app shows a message pointing you to the working alternative instead of attempting the download.

---

## Getting started

There are two ways to use CoomerDL:

### Option A — Download a release (recommended)

Grab the latest build from the [Releases page](https://github.com/Emy69/CoomerDL/releases). No Python installation needed.

### Option B — Run from source

Requires **Python 3.10+** on **Windows 10/11**. Dependencies (installed from `requirements.txt`): PySide6, requests, beautifulsoup4, and cloudscraper (only needed for SimpCity).

```bash
git clone https://github.com/Emy69/CoomerDL.git
cd CoomerDL
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies and run:

```bash
pip install -r requirements.txt
python main.py
```

---

## How to use

1. Launch the application
2. Paste a URL from a supported site
3. Select your download folder
4. Choose the content types you want (images, videos, compressed files)
5. Click **Download**

https://github.com/user-attachments/assets/f11a4681-4c6f-4797-a8a5-8eabe5e2cdfa

Downloaded files are organized into subfolders by type (`images`, `videos`, `documents`, `compressed`).

---

## Features

- Modern **PySide6** desktop interface
- Multithreaded downloads with configurable limits
- Per-file and global progress tracking (speed, ETA)
- Automatic retries with configurable interval
- SQLite database to skip files already downloaded
- Configurable file naming modes and folder structure
- Exportable logs
- Cookies support for SimpCity
- English and Spanish included, community translations supported

### Supported file types

| Type | Extensions |
|------|-----------|
| Videos | `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.flv`, `.wmv`, `.m4v` |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff` |
| Documents | `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx` |
| Compressed | `.zip`, `.rar`, `.7z`, `.tar`, `.gz` |

---

## Settings

Open **Settings** from the main window:

- **General** — language selection
- **Downloads** — max simultaneous downloads, retries, retry interval, file naming mode, folder structure (these apply to every supported site)
- **Cookies** — SimpCity cookies (import, save, clear), with a status line showing how many cookies are stored and a built-in tutorial for extracting them from your browser
- **Database** — browse download records grouped by user and post, search by user or file name, see totals (users, files, size), export the database, or delete records

### SimpCity cookies

SimpCity may require cookies depending on the content or your session. In **Settings > Cookies** you can:

- paste cookies as JSON
- import cookies from a file
- save or clear saved cookies

These cookies are only used for SimpCity downloads.

### Download database

CoomerDL keeps a record of every downloaded file in a local SQLite database so it can skip files you already have. You can export or manage records from **Settings > Database**.

Default location: `resources/config/downloads.db`

### Logs

The app shows domain-tagged logs in the UI and can export them to a file:

```text
bunkr: Resolving /f/ URL ...
erome: Processing album URL ...
system: Download settings were applied successfully.
```

Default logs folder: `resources/config/logs/`

---

## Translations

Officially maintained languages: **English** and **Español**. Other languages can be added by the community through forks.

Translation files live in:

```text
resources/config/i18n/
    languages.json
    en.json
    es.json
```

### Adding a new language

1. Fork the repository
2. Copy `en.json` and rename it to your language code (e.g. `fr.json`, `ja.json`, `pt_br.json`)
3. Translate the **values only** — never change the keys
4. Keep placeholders like `{url}`, `{error}`, `{path}`, `{version}` unchanged
5. Register the language in `languages.json`:

```json
{
  "official": [
    { "code": "en", "name": "English" },
    { "code": "es", "name": "Español" }
  ],
  "community": [
    { "code": "fr", "name": "Français" }
  ]
}
```

6. Run the app and select the language from **Settings > General**

If a key is missing in a community language, the app falls back to English.

---

## Contributing / forking

1. Fork the repository on GitHub
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/CoomerDL.git
cd CoomerDL
```

3. Add the original repository as upstream:

```bash
git remote add upstream https://github.com/Emy69/CoomerDL.git
```

4. Keep your fork updated:

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

5. Work on your own branch:

```bash
git checkout -b my-changes
```

---

## Related CLI projects

Prefer the command line? Check out:

- **[Coomer CLI](https://github.com/Emy69/Coomer-cli)**
- **[SimpCity CLI](https://github.com/Emy69/SimpCityCLI)**

---

## Support

If this project helps you, you can support it here:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00.svg?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/emy_69)
[![Support on Patreon](https://img.shields.io/badge/Support%20on%20Patreon-FF424D.svg?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/emy69)

## Community

[![Join Discord](https://img.shields.io/badge/Join-Discord-7289DA.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ku8gSPsesh)

## Downloads

Latest public builds are on the [Releases page](https://github.com/Emy69/CoomerDL/releases).
