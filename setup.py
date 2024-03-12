from cx_Freeze import setup, Executable

# Opciones adicionales
build_exe_options = {
    "packages": ["os", "tkinter", "requests", "bs4", "threading", "customtkinter","urllib3"],  # Añade los paquetes adicionales que uses
    "excludes": ["matplotlib.tests", "numpy.random._examples"],  # Excluye lo que no necesitas
    "include_files": ["app/", "downloader/"] # Si necesitas incluir archivos o carpetas adicionales
}

# Configuración del ejecutable
setup(
    name="Coomer Downloader App",
    version="0.1",
    description="Una aplicación para descargar imágenes y vídeos.",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base="Win32GUI")]  # Asegúrate de que "main.py" sea tu script principal
)
