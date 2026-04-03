@echo off
REM ================================================================
REM  Texture STL Tool — Installer Build Script
REM ================================================================
REM
REM  This script compiles the Inno Setup .iss file into a Windows
REM  installer .exe.
REM
REM  Prerequisites:
REM    1. Inno Setup 6 installed (https://jrsoftware.org/isinfo.php)
REM    2. PyInstaller build already completed (build.bat in project root)
REM       Expected output: ..\dist\TextureSTLTool\TextureSTLTool.exe
REM
REM  Usage:
REM    build_installer.bat                  — build installer
REM    build_installer.bat --pyinstaller    — run PyInstaller first, then installer
REM    build_installer.bat --clean          — remove release folder
REM
REM  Output:
REM    ..\release\TextureSTLTool_Setup_1.0.0.exe
REM
REM ================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "ISS_FILE=TextureSTLTool.iss"
set "PROJECT_ROOT=.."
set "DIST_DIR=%PROJECT_ROOT%\dist\TextureSTLTool"
set "RELEASE_DIR=%PROJECT_ROOT%\release"
set "EXE_NAME=TextureSTLTool.exe"

REM ---- Handle --clean flag ----
if "%1"=="--clean" (
    echo Cleaning release folder...
    if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
    echo Done.
    goto :eof
)

REM ---- Print header ----
echo.
echo ============================================================
echo   Building Texture STL Tool Installer
echo ============================================================
echo.

REM ---- Optionally run PyInstaller first ----
if "%1"=="--pyinstaller" (
    echo [0/4] Running PyInstaller build first...
    echo.
    pushd "%PROJECT_ROOT%"
    call build.bat
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo PyInstaller build failed. Cannot create installer.
        popd
        pause
        exit /b 1
    )
    popd
    echo.
)

REM ---- Step 1: Verify PyInstaller output exists ----
echo [1/4] Checking for PyInstaller output...

if not exist "%DIST_DIR%\%EXE_NAME%" (
    echo.
    echo   ERROR: %DIST_DIR%\%EXE_NAME% not found!
    echo.
    echo   You need to run the PyInstaller build first:
    echo     cd %PROJECT_ROOT%
    echo     build.bat
    echo.
    echo   Or run this script with --pyinstaller flag:
    echo     build_installer.bat --pyinstaller
    echo.
    pause
    exit /b 1
)

echo       Found: %DIST_DIR%\%EXE_NAME%
echo.

REM ---- Step 2: Find Inno Setup compiler ----
echo [2/4] Locating Inno Setup compiler...

set "ISCC="

REM Check common install locations
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

REM Check PATH
if "!ISCC!"=="" (
    where iscc.exe >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "delims=" %%i in ('where iscc.exe') do set "ISCC=%%i"
    )
)

if "!ISCC!"=="" (
    echo.
    echo   ERROR: Inno Setup compiler (ISCC.exe) not found!
    echo.
    echo   Install Inno Setup 6 from:
    echo     https://jrsoftware.org/isdl.php
    echo.
    echo   Or add ISCC.exe to your PATH.
    echo.
    pause
    exit /b 1
)

echo       Found: !ISCC!
echo.

REM ---- Step 3: Create release directory ----
echo [3/4] Preparing release directory...
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
echo       Output will go to: %RELEASE_DIR%
echo.

REM ---- Step 4: Compile installer ----
echo [4/4] Compiling installer (this may take a minute)...
echo.

"!ISCC!" "%ISS_FILE%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo   INSTALLER BUILD FAILED — see errors above.
    echo ============================================================
    echo.
    echo   Common issues:
    echo     - Inno Setup script syntax error
    echo     - Source files not found (PyInstaller not run?)
    echo     - Insufficient disk space
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   INSTALLER BUILD SUCCESSFUL
echo ============================================================
echo.

REM List the output
for %%f in ("%RELEASE_DIR%\TextureSTLTool_Setup_*.exe") do (
    echo   Installer: %%f
    echo   Size:      %%~zf bytes
)

echo.
echo   To test:
echo     Double-click the installer .exe
echo     Install, launch, verify, then uninstall
echo.
echo   To distribute:
echo     Share the installer .exe — that's all users need.
echo.
echo ============================================================
echo.
pause
