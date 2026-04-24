@echo off
title Build AppSys Serial Activation EXE

echo ==========================================
echo Building AppSys Serial Activation EXE
echo ==========================================

REM Go to the folder where this BAT file is located
cd /d "%~dp0"

REM Install required packages
echo.
echo Installing requirements...
python -m pip install --upgrade pip
python -m pip install pyinstaller pyodbc

REM Clean old build files
echo.
echo Cleaning old build files...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

REM Build EXE
echo.
echo Creating EXE...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "AppSysSerialActivation" ^
  --hidden-import pyodbc ^
  main.py

REM Copy config.txt next to the EXE
echo.
echo Copying config.txt...
copy config.txt dist\config.txt

echo.
echo ==========================================
echo DONE
echo Your EXE is here:
echo dist\AppSysSerialActivation.exe
echo ==========================================

pause