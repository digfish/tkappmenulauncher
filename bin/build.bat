rem @echo off
set VIRTUALENV=%1
echo %VIRTUALENV%
%VIRTUALENV%\Scripts\activate && pyinstaller --onefile --windowed --name AppMenuLauncher ^
    --paths ../envlibloader -i ../app-menu-launcher.ico ^
    --workpath . --distpath dist --specpath launcher launcher/main.py

