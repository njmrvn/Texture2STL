# Building the Windows Installer

This folder contains the Inno Setup configuration for creating a professional
Windows installer for Texture STL Tool.

## What the Installer Does

- Installs the packaged app to `C:\Program Files\Texture STL Tool`
- Creates a Start Menu shortcut
- Optionally creates a Desktop shortcut
- Registers in Windows Add/Remove Programs for clean uninstall
- On uninstall, asks whether to remove user data from `%APPDATA%`
- Detects if the app is running and prevents install/uninstall conflicts
- Supports silent installs (`/SILENT` or `/VERYSILENT` command-line flags)
- Supports upgrades — installs over prior versions cleanly

## Prerequisites

### 1. Inno Setup 6

Download and install from: https://jrsoftware.org/isdl.php

Choose the default install location. The build script auto-detects it at:
- `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
- `C:\Program Files\Inno Setup 6\ISCC.exe`

### 2. Completed PyInstaller Build

The installer packages the output of PyInstaller. You must run the
PyInstaller build first:

```cmd
cd texture_stl_tool
build.bat
```

This produces `dist\TextureSTLTool\TextureSTLTool.exe` and all dependencies.

## Building the Installer

### Option A: Installer Only (PyInstaller already done)

```cmd
cd installer
build_installer.bat
```

### Option B: Full Pipeline (PyInstaller + Installer)

```cmd
cd texture_stl_tool
build_release.bat
```

Or from the installer folder:

```cmd
build_installer.bat --pyinstaller
```

### Option C: GUI (Inno Setup Compiler)

1. Open `TextureSTLTool.iss` in the Inno Setup Compiler application
2. Build → Compile (Ctrl+F9)
3. The output appears in `release\`

## Output

```
release\
└── TextureSTLTool_Setup_1.0.0.exe    ← distribute this single file
```

The installer `.exe` is self-contained. Users double-click it, follow the
wizard, and the app is installed.

## File Layout

```
installer/
├── TextureSTLTool.iss        ← Inno Setup script (edit version here)
├── build_installer.bat       ← Automated build script
└── README_INSTALLER.md       ← This file

project root/
├── build.bat                 ← PyInstaller build
├── build_release.bat         ← Full pipeline (PyInstaller + Installer)
├── icon.ico                  ← App icon (optional, auto-detected)
├── LICENSE.txt               ← License file (optional, auto-included)
└── dist/
    └── TextureSTLTool/       ← PyInstaller output (installer source)
```

## Updating the Version Number

When releasing a new version, update **one place** in the `.iss` file:

```iss
; At the top of TextureSTLTool.iss:
#define MyAppVersion     "1.0.0"    ← change this
```

This automatically updates:
- The installer filename: `TextureSTLTool_Setup_1.0.0.exe`
- The version shown in the install wizard
- The version in Add/Remove Programs
- The version metadata embedded in the installer `.exe`

### Version Numbering

Recommended: [Semantic Versioning](https://semver.org/)

| Version | Meaning |
|---------|---------|
| 1.0.0   | Initial release |
| 1.0.1   | Bug fix |
| 1.1.0   | New feature (backward compatible) |
| 2.0.0   | Major changes / breaking changes |

## Adding an Application Icon

1. Create or obtain a `.ico` file (multi-resolution, 256×256 recommended)
2. Save as `icon.ico` in the project root (next to `main.py`)
3. Both the PyInstaller spec and the Inno Setup script auto-detect it
4. Rebuild both: `build_release.bat`

Free ICO converter: https://convertico.com/

## Adding a License File

1. Save your license text as `LICENSE.txt` in the project root
2. The installer will include it in the install directory automatically

To show the license during installation (user must accept), add this to
the `.iss` file in `[Setup]`:

```iss
LicenseFile={#ProjectRoot}\LICENSE.txt
```

## Silent Install (for IT Deployment)

```cmd
TextureSTLTool_Setup_1.0.0.exe /SILENT
TextureSTLTool_Setup_1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES
```

Custom install directory:
```cmd
TextureSTLTool_Setup_1.0.0.exe /SILENT /DIR="D:\Apps\TextureSTLTool"
```

## Code Signing (Future)

To eliminate Windows SmartScreen warnings, sign both:

1. **The app exe** — sign `TextureSTLTool.exe` after PyInstaller but before
   running Inno Setup
2. **The installer exe** — sign the output `.exe` after Inno Setup

```cmd
REM Example with signtool (from Windows SDK):
signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\TextureSTLTool\TextureSTLTool.exe"

REM Then build installer, then sign installer:
signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com /td sha256 /fd sha256 "release\TextureSTLTool_Setup_1.0.0.exe"
```

Code signing certificates can be purchased from DigiCert, Sectigo, or
obtained free via SignPath.io for open-source projects.

## What Gets Installed vs. What Doesn't

### Installed to Program Files

Everything from `dist\TextureSTLTool\`:
- `TextureSTLTool.exe`
- `_internal\` (Python runtime, all DLLs)
- `textures\` (bundled sample textures — read-only seed data)
- `library\` (seed `library.json`)
- Qt plugins, VTK resources, etc.

### NOT in Program Files (created at runtime)

The app creates these in `%APPDATA%\TextureSTLTool\` on first launch:
- `config\settings.json` — window position, recent files
- `textures\` — writable copy of textures + user imports
- `library\library.json` — writable texture library metadata

This separation ensures:
- Program Files stays read-only (no UAC issues)
- User data survives app updates
- Multiple Windows users each get their own data

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ISCC not found | Install Inno Setup 6, or add its folder to PATH |
| "Source file not found" error | Run `build.bat` first to create `dist\TextureSTLTool\` |
| Installer is very large (500MB+) | Normal for VTK+Qt apps. LZMA compression reduces it significantly. |
| SmartScreen warning | Expected for unsigned apps. See Code Signing section above. |
| Antivirus flags installer | PyInstaller false-positive. Submit to your AV vendor for whitelisting. |
| Old version not detected on upgrade | Do NOT change the `AppId` GUID between versions |
