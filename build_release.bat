@echo off
REM ================================================================
REM  Texture STL Tool — Full Release Build
REM ================================================================
REM
REM  Runs the complete build pipeline:
REM    1. PyInstaller → dist\TextureSTLTool\
REM    2. Inno Setup  → release\TextureSTLTool_Setup_X.Y.Z.exe
REM
REM  Prerequisites:
REM    - Python 3.10+ with all pip dependencies installed
REM    - PyInstaller installed
REM    - Inno Setup 6 installed
REM
REM  Usage:
REM    build_release.bat
REM
REM ================================================================

setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo   FULL RELEASE BUILD
echo   Step 1: PyInstaller packaging
echo   Step 2: Inno Setup installer
echo ============================================================
echo.

REM ---- Step 1: PyInstaller ----
echo ---- Step 1 of 2: PyInstaller ----
echo.
call build.bat

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Step 1 failed. Aborting.
    pause
    exit /b 1
)

REM ---- Step 2: Inno Setup ----
echo.
echo ---- Step 2 of 2: Inno Setup Installer ----
echo.
pushd installer
call build_installer.bat
set RESULT=%ERRORLEVEL%
popd

if %RESULT% NEQ 0 (
    echo.
    echo Step 2 failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   FULL RELEASE BUILD COMPLETE
echo ============================================================
echo.
echo   Packaged app:  dist\TextureSTLTool\TextureSTLTool.exe
echo.
for %%f in ("release\TextureSTLTool_Setup_*.exe") do (
    echo   Installer:     %%f
)
echo.
echo ============================================================
pause
