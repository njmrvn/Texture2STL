@echo off
REM ================================================================
REM  Texture STL Tool — Windows Build Script
REM ================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "SPEC_FILE=texture_stl_tool.spec"
set "DIST_DIR=dist\TextureSTLTool"
set "EXE_NAME=TextureSTLTool.exe"

REM ---- Handle --clean flag ----
if "%1"=="--clean" (
    echo Cleaning build artifacts...
    if exist build  rmdir /s /q build
    if exist dist   rmdir /s /q dist
    echo Done.
    goto :eof
)

echo.
echo ============================================================
echo   Building Texture STL Tool for Windows
echo ============================================================
echo.
echo   Spec file : %SPEC_FILE%
echo   Output    : %DIST_DIR%\%EXE_NAME%
echo.

REM ---- Verify Python launcher exists ----
where py >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python launcher "py" not found on PATH.
    echo.
    pause
    exit /b 1
)

REM ---- Verify PyInstaller is installed ----
py -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller is not available for this Python installation.
    echo        Install it with:  py -m pip install pyinstaller
    echo.
    pause
    exit /b 1
)

REM ---- Clean previous build ----
echo [1/3] Cleaning previous build...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
echo       Done.
echo.

REM ---- Run PyInstaller ----
echo [2/3] Running PyInstaller (this may take several minutes)...
echo.

if "%1"=="--debug" (
    echo       ** DEBUG MODE — console window will be visible **
    py -m PyInstaller "%SPEC_FILE%" --noconfirm --log-level INFO 2>&1
) else (
    py -m PyInstaller "%SPEC_FILE%" --noconfirm --log-level WARN
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo   BUILD FAILED — see errors above.
    echo ============================================================
    echo.
    echo   Common fixes:
    echo     - Make sure all pip packages are installed
    echo     - Try:  py -m pip install pyinstaller --upgrade
    echo     - Try:  py -m pip install vtk pyvista pyvistaqt --force-reinstall
    echo.
    pause
    exit /b 1
)

REM ---- Verify output ----
echo.
echo [3/3] Verifying output...

if not exist "%DIST_DIR%\%EXE_NAME%" (
    echo.
    echo   WARNING: %EXE_NAME% not found in %DIST_DIR%
    echo   The build may have partially failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   BUILD SUCCESSFUL
echo ============================================================
echo.
echo   Executable : %DIST_DIR%\%EXE_NAME%
echo.
echo   To run:
echo     cd %DIST_DIR%
echo     %EXE_NAME%
echo.
echo   To distribute:
echo     Zip the entire %DIST_DIR% folder and share it.
echo     Users just unzip and double-click %EXE_NAME%.
echo.
echo   User data is stored in:
echo     %%APPDATA%%\TextureSTLTool\
echo ============================================================
echo.
pause