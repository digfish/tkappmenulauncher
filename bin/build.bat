@echo off
rem conda activate appmenulauncher-venv
pyinstaller --onefile --windowed --name AppMenuLauncher ^
    --paths ../envlibloader -i ../app-menu-launcher.ico ^
    --workpath launcher --distpath . --specpath launcher launcher/main.py
rem call bin\install.bat %1

