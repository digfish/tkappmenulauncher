@ECHO OFF

SET PWD=%0/../..
SET PYTHONPATH=%PWD%/../pystray/lib;%PWD%/../envlibloader 
python %PWD%/launcher/main.py
