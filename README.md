![Windows Compatibility](https://img.shields.io/badge/Windows-10%2C%2011-blue)
![Downloads](https://img.shields.io/github/downloads/emy69/CoomerDL/total)

# CoomerDL

**CoomerDL** is a Python desktop downloader for supported media pages such as Coomer, Kemono, Erome, Bunkr, SimpCity, and JPG5.

The app now uses a **PySide6 / Qt** interface. The old Tkinter / CustomTkinter UI is no longer the active desktop UI.

---

## Features

- Modern **PySide6** desktop interface
- Download images, videos, and compressed files from supported sites
- Multithreaded downloads with configurable limits
- Per-file and global progress tracking
- Exportable logs
- Cookies support for SimpCity
- SQLite download database
- Configurable naming modes
- Configurable folder structure
- English and Spanish included by default
- Community/fork-friendly translation system

### Supported file types

**Videos**
- `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.flv`, `.wmv`, `.m4v`

**Images**
- `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`

**Documents**
- `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`

**Compressed**
- `.zip`, `.rar`, `.7z`, `.tar`, `.gz`

---

## Supported sites

- [coomer.su](https://coomer.su/)
- [kemono.su](https://kemono.su/)
- [erome.com](https://www.erome.com/)
- [bunkr-albums.io](https://bunkr-albums.io/)
- [simpcity.su](https://simpcity.su/)
- [jpg5.su](https://jpg5.su/)

---

## Screenshots / usage

1. Launch the application
2. Paste a supported URL
3. Select your download folder
4. Choose the content types you want
5. Click **Download**

![Usage GIF](https://github.com/Emy69/CoomerDL/blob/main/resources/screenshots/0627.gif)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Emy69/CoomerDL.git
cd CoomerDL
```

### 2. Create and activate a virtual environment

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (CMD)**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python main.py
```

---

## Requirements

- Python 3.10+
- Windows 10 or Windows 11

---

## Settings overview

The Settings window currently includes:

- **General**: language selection
- **Downloads**: max downloads, retries, retry interval, naming mode, folder structure
- **Cookies**: SimpCity cookies import/save/clear
- **Database**: browse, export, and manage download records

---

## Language support

Officially maintained in this repository:

- English
- Español

Other languages can be added by the community through forks.

### Translation file structure

Translations are loaded from locale JSON files. The project uses stable translation keys instead of using full text strings as keys.

Example structure:

```text
resources/config/i18n/
    languages.json
    en.json
    es.json
```

### How to add a new language in a fork

1. Fork the repository
2. Create a new translation file by copying `en.json`
3. Rename it to your language code, for example:
   - `fr.json`
   - `ja.json`
   - `pt_br.json`
4. Translate the values, but keep the keys unchanged
5. Register the language inside `languages.json`
6. Run the app and test the new language from **Settings > General**

Example `languages.json`:

```json
{
  "languages": [
    { "code": "en", "name": "English", "official": true },
    { "code": "es", "name": "Español", "official": true },
    { "code": "fr", "name": "Français", "official": false }
  ]
}
```

### Translation rules

- Do not change translation keys
- Only translate the values
- Keep placeholders unchanged, for example:
  - `{url}`
  - `{error}`
  - `{path}`
  - `{version}`
- If a key is missing in a community language, the app should fall back to English

---

## Fork guide

If you want to customize the project:

### 1. Fork on GitHub
Use the GitHub **Fork** button on the repository page.

### 2. Clone your fork

```bash
git clone https://github.com/YOUR_USERNAME/CoomerDL.git
cd CoomerDL
```

### 3. Add the original repository as upstream

```bash
git remote add upstream https://github.com/Emy69/CoomerDL.git
```

### 4. Keep your fork updated

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

### 5. Create your own branch

```bash
git checkout -b my-changes
```

---

## SimpCity cookies

SimpCity may require cookies for access depending on the content or session state.

The app includes a **Cookies** tab where you can:

- paste cookies JSON
- import cookies from a file
- save cookies
- clear saved cookies

These cookies are only intended for SimpCity support inside the app.

---

## Download database

CoomerDL stores downloaded file records in a local SQLite database so it can:

- avoid re-downloading known files
- export database records
- manage entries from the Settings window

Default database location:

```text
resources/config/downloads.db
```

---

## Logs

The app keeps exportable logs and uses a domain-aware log format in the UI.

Example:

```text
bunkr: Resolving /f/ URL ...
coomer: Fetching user posts ...
erome: Processing album URL ...
system: Download settings were applied successfully.
```

Default logs folder:

```text
resources/config/logs/
```

---

## CLI projects

If you prefer command-line tools, check these related projects:

- **[Coomer CLI](https://github.com/Emy69/Coomer-cli)**
- **[SimpCity CLI](https://github.com/Emy69/SimpCityCLI)**

---

## Support

If this project helps you, you can support it here:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00.svg?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/emy_69)
[![Support on Patreon](https://img.shields.io/badge/Support%20on%20Patreon-FF424D.svg?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/emy69)

---

## Community

Join the Discord server:

[![Join Discord](https://img.shields.io/badge/Join-Discord-7289DA.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ku8gSPsesh)

---

## Downloads

You can find the latest public builds on the GitHub Releases page:

- [Releases](https://github.com/Emy69/CoomerDL/releases)