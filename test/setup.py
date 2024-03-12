from cx_Freeze import setup, Executable

setup(
    name="Coomer",
    version="V1.0.5",
    description="Coomer app",
    executables=[
        Executable("main.py", base="Win32GUI", icon="icono.ico")  # Reemplaza "icono.ico" con el nombre de tu archivo de icono
    ],
    options={
        "build_exe": {
            "include_files": ["about.gif", "icono.ico"]  # Reemplaza "about.gif" con el nombre de tu archivo GIF y "icono.ico" con el nombre de tu archivo de icono
        }
    }
)


#python setup.py build