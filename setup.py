from cx_Freeze import setup, Executable

# Definir las opciones adicionales
options = {
    'build_exe': {
        'packages': ["os", "tkinter", "requests", "bs4", "threading", "customtkinter", "urllib3"],  # Paquetes necesarios
        'excludes': ["matplotlib", "numpy","aiohttp","aiosignal","altgraph","ffmpeg","Flask","youtube-dl","SQLAlchemy","pytube"],  # Excluir paquetes que no son necesarios
        'include_files': ['app/', 'downloader/'],  # Incluir directorios adicionales
    }
}

# Configuración del ejecutable
setup(
    name="ImageDownloaderApp",
    version="0.1",
    description="Una aplicación para descargar imágenes y vídeos de manera asincrónica.",
    options=options,
    executables=[Executable("main.py", base="Win32GUI")]  # Asegúrate de que "main.py" sea el punto de entrada de tu app
)
