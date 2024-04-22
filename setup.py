from cx_Freeze import setup, Executable

# Define additional options
options = {
    'build_exe': {
        'packages': [
            "os", "tkinter", "requests", "bs4", "threading",
            "customtkinter", "urllib3", "sys", "json"
        ],
        'excludes': [
            "matplotlib", "numpy", "aiohttp", "aiosignal",
            "altgraph", "ffmpeg", "Flask", "youtube_dl", "SQLAlchemy", "pytube"
        ],
        'include_files': [
            'resources/'  # Solo incluir recursos no Python aquí
        ],
        'optimize': 2,
    }
}

# Setup configuration for the executable
setup(
    name="ImageDownloaderApp",
    version="0.5.2",
    description="DownloaderApp.",
    options=options,
    executables=[Executable("main.py", base="Win32GUI", icon="resources/img/icon.ico")]
)