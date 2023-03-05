set PYWIN32_LIB=%CONDA_PREFIX%\Lib\site-packages\pywin32_system32
mkdir  %1
copy AppMenuLauncher.exe %1
copy %PYWIN32_LIB%\*.dll %1
