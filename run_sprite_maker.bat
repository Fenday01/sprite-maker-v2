@echo off
setlocal
cd /d "%~dp0"

rem Use a working local Python installation without requiring Python on PATH.
if exist "C:\Program Files\FreeCAD 0.21\bin\pythonw.exe" (
    start "" "C:\Program Files\FreeCAD 0.21\bin\pythonw.exe" "%~dp0main.py"
    exit /b 0
)

if exist "C:\Program Files\Labcenter Electronics\Proteus 9 Professional\Tools\Python\pythonw.exe" (
    start "" "C:\Program Files\Labcenter Electronics\Proteus 9 Professional\Tools\Python\pythonw.exe" "%~dp0main.py"
    exit /b 0
)

where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0main.py"
    exit /b 0
)

echo No working Python installation with Tkinter was found.
echo Install Python from https://www.python.org/downloads/windows/
echo and enable "Add python.exe to PATH" during installation.
pause
exit /b 1
