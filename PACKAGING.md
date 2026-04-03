# Packaging Texture STL Tool as a Windows .exe

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  BUNDLED (read-only, inside dist/TextureSTLTool/)           │
│  ├── TextureSTLTool.exe                                     │
│  ├── textures/          ← sample textures shipped with app  │
│  ├── library/           ← seed library.json                 │
│  ├── icon.ico           ← app icon (optional)               │
│  └── [Python runtime, DLLs, Qt plugins, VTK libs...]        │
└─────────────────────────────────────────────────────────────┘
                            │
               On first launch, assets are
               copied to the user data folder
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  USER DATA (writable, %APPDATA%\TextureSTLTool\)            │
│  ├── config/settings.json   ← app settings, recent files   │
│  ├── textures/              ← user-imported + sample imgs   │
│  └── library/library.json   ← texture library metadata      │
└─────────────────────────────────────────────────────────────┘
```

### Why One-Folder Build?

VTK and PySide6 depend on many shared libraries (.dll), OpenGL drivers, and Qt
plugin directories.  A one-file build extracts everything to a temp folder on
each launch which:
- Is slow (several seconds startup)
- Often triggers antivirus false-positives
- Can break OpenGL context initialization on some GPUs

A one-folder build keeps everything in a stable directory and launches
instantly.

## Prerequisites

1. **Python 3.10+** on PATH
2. All app dependencies installed:
   ```
   pip install -r requirements.txt
   ```
3. PyInstaller installed (included in requirements.txt):
   ```
   pip install pyinstaller
   ```

## Building

### Quick Build

Double-click `build.bat` or run in a terminal:

```cmd
cd texture_stl_tool
build.bat
```

### Build Variants

```cmd
build.bat              # Normal build (no console, optimized)
build.bat --debug      # Build with console window for debugging
build.bat --clean      # Delete build/ and dist/ folders only
```

### Manual Build (if build.bat doesn't work)

```cmd
cd texture_stl_tool
pyinstaller texture_stl_tool.spec --noconfirm
```

## Output

After a successful build:

```
dist/
└── TextureSTLTool/
    ├── TextureSTLTool.exe    ← double-click to run
    ├── textures/             ← bundled sample textures
    ├── library/              ← seed library data
    ├── _internal/            ← Python runtime + dependencies
    └── ...                   ← DLLs, Qt plugins, VTK resources
```

## Distribution

1. Zip the entire `dist/TextureSTLTool/` folder
2. Share the zip file
3. End users unzip and double-click `TextureSTLTool.exe`
4. No Python installation needed on the target machine

## User Data Location

The app stores all user-modifiable data in:

```
%APPDATA%\TextureSTLTool\
├── config\settings.json    ← window position, recent files
├── textures\               ← imported texture images
└── library\library.json    ← texture library metadata
```

To reset the app to factory defaults, delete this folder.

## Adding an Application Icon

1. Place an `icon.ico` file in the project root (next to `main.py`)
2. The spec file automatically detects and uses it
3. Recommended size: 256×256 multi-resolution .ico
4. Free converter: https://convertico.com/

## Testing the Packaged Build

After building, verify these scenarios work:

### Checklist

- [ ] **Launch**: Double-click `TextureSTLTool.exe` — window appears, no crash
- [ ] **Viewport**: Dark 3D viewport is visible with axes gizmo
- [ ] **Import STL**: File → Import STL → load any .stl file → mesh appears
- [ ] **Orbit/Pan/Zoom**: Left-drag rotates, middle-drag pans, scroll zooms
- [ ] **Selection**: Enable Selection Mode → click faces → they turn red
- [ ] **Texture Library**: Sample textures appear in library list on left panel
- [ ] **Load Texture**: Double-click a library texture → preview shows
- [ ] **Preview Displacement**: Click "Preview Displacement" → mesh deforms
- [ ] **Apply**: Click "Apply" → displacement committed
- [ ] **Export STL**: Click "Export STL" → save dialog → file is written
- [ ] **Verify Export**: Open exported STL in another viewer — texture geometry is present
- [ ] **Persistence**: Close and reopen app — recent files and library are preserved
- [ ] **Add to Library**: Import a new texture → it appears in library on next launch

## Troubleshooting

### Build Errors

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'vtkmodules'` | `pip install vtk --force-reinstall` |
| `ModuleNotFoundError: No module named 'pyvistaqt'` | `pip install pyvistaqt` |
| `ImportError: DLL load failed` | Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| `pyinstaller: command not found` | `pip install pyinstaller` or activate your venv |
| Build takes forever / hangs | VTK has many submodules. First build can take 5-10 min. Be patient. |

### Runtime Errors (after build)

| Error | Fix |
|-------|-----|
| Black/empty viewport | GPU driver issue. Update graphics drivers. Try `--debug` build to see errors. |
| App crashes on launch | Run `--debug` build, check console output for missing module errors |
| "Failed to load STL" | Ensure the STL file is valid binary or ASCII STL |
| Textures don't show in library | Check `%APPDATA%\TextureSTLTool\library\library.json` exists |
| Settings not saving | Check write permissions on `%APPDATA%\TextureSTLTool\` |
| Antivirus blocks exe | Add `dist\TextureSTLTool\` to exclusion list. This is a known PyInstaller false-positive. |

### Reducing Build Size

The default build can be 500MB+ due to VTK and Qt. To reduce:

1. Use a clean virtual environment with only required packages
2. Optionally add more entries to the `excludes` list in the spec file
3. UPX compression is enabled by default (saves ~20%)

## Technical Notes

### How Path Resolution Works

The `src/paths.py` module detects the execution context:

```python
# Frozen (.exe)
sys.frozen == True
sys._MEIPASS == "C:\\Users\\...\\AppData\\Local\\Temp\\_MEI12345"

# Source (python main.py)
sys.frozen is not set
Path(__file__) points to the actual source file
```

Read-only bundled assets always come from `sys._MEIPASS` (frozen) or the
project root (source).  Writable user data always goes to `%APPDATA%`
(frozen) or the project root (source).

### PyInstaller Hidden Imports

VTK is the main offender for missing imports.  The spec file uses
`collect_submodules('vtkmodules')` to grab every VTK module, which is
heavy but reliable.  If you want a slimmer build, you can replace this
with a curated list — but test thoroughly.

### Qt Plugins

PyInstaller usually handles PySide6 plugin detection automatically via
its built-in hooks.  If you see `qt.qpa.plugin: Could not find the Qt
platform plugin "windows"`, the PySide6 hook failed — reinstall PySide6
and rebuild.
