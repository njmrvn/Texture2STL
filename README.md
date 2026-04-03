# Texture STL Tool

Desktop application for applying grayscale textures as **real geometric displacement** to STL meshes. The texture is permanently embedded in the mesh geometry — not a visual shader or slicer trick.

## Features

- **STL Import/Export**: Load binary or ASCII STL files, export modified meshes
- **Interactive 3D Viewport**: Orbit, pan, zoom with PyVista/VTK
- **Face Selection**: Single face, connected region (flood fill), or normal-based selection
- **Texture Library**: Import, save, and reuse grayscale textures
- **Geometric Displacement**: Grayscale heightmap → actual vertex displacement along normals
- **Rich Parameters**: Depth, tiling, offset, invert, smoothing, contrast, clamping, displacement mode
- **Mesh Subdivision**: Increase mesh density before displacement for fine texture detail
- **Preview & Apply**: Preview displacement before committing, then export

## Requirements

- Python 3.10+
- Windows, macOS, or Linux

## Setup

```bash
# Clone or copy the project
cd texture_stl_tool

# Create virtual environment (recommended)
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Workflow

1. **Import STL**: Click "Import STL" or use File → Import STL
2. **Select Faces**: Enable Selection Mode, choose a selection type, click on the mesh
   - **Single Face**: Click individual triangles (toggle on/off)
   - **Connected Region**: Click a face to flood-fill connected faces within the angle threshold
   - **By Normal**: Click a face to select all faces with similar orientation
3. **Load Texture**: Load a grayscale image or pick from the built-in library
4. **Adjust Parameters**:
   - **Depth**: Displacement height in mm
   - **Tile X/Y**: Texture repetitions
   - **Offset X/Y**: Shift texture position
   - **Invert**: Flip black/white
   - **Smoothing**: Blur the heightmap
   - **Contrast**: Increase/decrease texture contrast
   - **Clamp Min/Max**: Limit displacement range
   - **Mode**: Positive (outward only) or Centered (both directions)
   - **Subdivision**: Increase mesh density (None, 1x, 2x, 3x)
5. **Preview**: See the displacement result before committing
6. **Apply**: Commit the displacement to the mesh
7. **Export**: Save the modified STL with geometry-embedded texture

## How It Works

The displacement algorithm:

```
new_vertex = original_vertex + vertex_normal × (grayscale_value × depth)
```

1. Selected faces define a mesh region
2. A local coordinate frame is computed from the region's geometry
3. Vertices are projected onto a 2D plane (planar projection)
4. UV coordinates are derived from the projection
5. The grayscale texture is sampled at each vertex's UV position
6. Each vertex is displaced along its normal by `sampled_value × depth`
7. Normals are recomputed after displacement

## Project Structure

```
texture_stl_tool/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── src/
│   ├── app.py              # Main window and workflow orchestration
│   ├── viewport.py         # 3D viewport (PyVista/VTK)
│   ├── mesh_manager.py     # Mesh I/O, subdivision, conversion
│   ├── selection.py        # Face selection algorithms
│   ├── texture_manager.py  # Texture library and image loading
│   ├── displacement.py     # Core displacement engine
│   ├── projection.py       # UV projection methods
│   ├── panels.py           # UI panel widgets
│   ├── workers.py          # Background thread workers
│   └── config.py           # App settings and persistence
├── tests/
│   ├── test_displacement.py
│   └── test_texture.py
├── textures/               # Sample textures (generated on first run)
└── library/
    └── library.json        # Texture library metadata
```

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Units

All dimensions assume **millimeters** unless your STL uses different units. The depth parameter is in the same units as the STL mesh coordinates.

## Extending

The code is structured for future additions:

- **Cylindrical/box projection**: `projection.py` has placeholder functions
- **Procedural textures**: Add generators to `texture_manager.py`
- **Additional export formats**: Extend `mesh_manager.py`
- **Brush selection**: Add to `selection.py` with VTK interaction in `viewport.py`
- **Curved surface mapping**: Enhance `projection.py`

## Sample Textures

On first run, the app generates five sample textures in the library:
- Checkerboard
- Diamond Plate
- Fine Noise
- Sine Waves
- Brick

## Troubleshooting

- **Black viewport**: Ensure VTK and PyVista are installed correctly. Try `pip install vtk --force-reinstall`
- **Picking doesn't work**: Make sure Selection Mode is enabled (button should be toggled on)
- **Slow subdivision**: Each level quadruples the triangle count. Use sparingly on dense meshes
- **Large export**: High subdivision + fine texture = many triangles. The app warns above 1M triangles
=======
# Texture2STL
A desktop tool to convert images (textures / heightmaps) into STL meshes for 3D printing and surface generation.
>>>>>>> 16e7b8e579874e5251e85c21b934e7c4d19d0470
