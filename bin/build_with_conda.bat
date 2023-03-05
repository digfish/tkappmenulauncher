@echo off
rem conda activate appmenulauncher-venv
set PYWIN32_LIB=%PYTHONHOME%\Lib\site-packages\pywin32_system32
set PATH=%PYWIN32_LIB%;%PATH%
pyinstaller --onefile --windowed --name AppMenuLauncher ^
    --paths ../envlibloader --paths %PYWIN32_LIB% -i ../app-menu-launcher.ico ^
    --workpath launcher --distpath . --specpath launcher launcher/main.py
rem call bin\install.bat %1
