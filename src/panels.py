"""UI panels for the application sidebar controls."""

import os
from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QFileDialog, QSlider, QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox, QScrollArea,
    QSizePolicy, QProgressBar,
)
from PIL import Image

from .config import DisplacementParams
from .texture_manager import TextureManager, TextureEntry


def _pil_to_qpixmap(img: Image.Image, max_size: int = 64) -> QPixmap:
    """Convert PIL Image to QPixmap thumbnail."""
    img = img.copy()
    img.thumbnail((max_size, max_size))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    data = img.tobytes('raw', 'RGBA')
    qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class ImportPanel(QGroupBox):
    """File import controls and mesh info display."""

    import_requested = Signal(str)
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Import", parent)
        layout = QVBoxLayout(self)

        self.btn_import = QPushButton("Import STL")
        self.btn_import.clicked.connect(self._on_import)
        layout.addWidget(self.btn_import)

        self.btn_reset = QPushButton("Reset to Original")
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(lambda: self.reset_requested.emit())
        layout.addWidget(self.btn_reset)

        self.lbl_info = QLabel("No mesh loaded")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.lbl_info)

        self._last_dir = ""

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open STL File", self._last_dir,
            "STL Files (*.stl);;All Files (*)"
        )
        if path:
            self._last_dir = str(Path(path).parent)
            self.import_requested.emit(path)

    def update_info(self, stats):
        if stats is None:
            self.lbl_info.setText("No mesh loaded")
            self.btn_reset.setEnabled(False)
            return
        self.btn_reset.setEnabled(True)
        size = stats.bbox_size
        self.lbl_info.setText(
            f"Triangles: {stats.triangle_count:,}\n"
            f"Vertices: {stats.vertex_count:,}\n"
            f"Size: {size[0]:.2f} × {size[1]:.2f} × {size[2]:.2f}\n"
            f"Watertight: {'Yes' if stats.is_watertight else 'No'}"
        )


class TexturePanel(QGroupBox):
    """Texture selection and library management."""

    texture_selected = Signal(object)  # Image.Image

    def __init__(self, tex_manager: TextureManager, parent=None):
        super().__init__("Textures", parent)
        self.tex_manager = tex_manager
        layout = QVBoxLayout(self)

        # Import button
        btn_row = QHBoxLayout()
        self.btn_load = QPushButton("Load Image")
        self.btn_load.clicked.connect(self._on_load_image)
        btn_row.addWidget(self.btn_load)

        self.btn_add_lib = QPushButton("Add to Library")
        self.btn_add_lib.clicked.connect(self._on_add_to_library)
        btn_row.addWidget(self.btn_add_lib)
        layout.addLayout(btn_row)

        # Current texture preview
        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedSize(128, 128)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("border: 1px solid #555; background: #333;")
        self.lbl_preview.setText("No texture")
        layout.addWidget(self.lbl_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        # Library list
        layout.addWidget(QLabel("Library:"))
        self.list_library = QListWidget()
        self.list_library.setMaximumHeight(200)
        self.list_library.itemDoubleClicked.connect(self._on_library_select)
        layout.addWidget(self.list_library)

        # Delete from library
        self.btn_delete = QPushButton("Remove Selected")
        self.btn_delete.clicked.connect(self._on_delete)
        layout.addWidget(self.btn_delete)

        self._current_image: Image.Image | None = None
        self._refresh_library()

    def _refresh_library(self):
        self.list_library.clear()
        for entry in self.tex_manager.entries:
            item = QListWidgetItem(entry.name)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            # Try to add icon
            thumb = self.tex_manager.get_thumbnail(entry, 48)
            if thumb:
                item.setIcon(_pil_to_qpixmap(thumb, 48).__class__().fromImage(
                    QImage(thumb.convert('RGBA').tobytes('raw', 'RGBA'),
                           thumb.width, thumb.height, QImage.Format.Format_RGBA8888)
                ))
            self.list_library.addItem(item)

    def _on_load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Texture Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if path:
            try:
                img = self.tex_manager.load_image(path)
                self._set_preview(img)
                self._current_image = img
                self.texture_selected.emit(img)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load image:\n{e}")

    def _on_add_to_library(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Texture to Library", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if path:
            name, ok = QInputDialog.getText(self, "Texture Name", "Name:",
                                            text=Path(path).stem)
            if ok and name:
                try:
                    self.tex_manager.import_texture(path, name)
                    self._refresh_library()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to import:\n{e}")

    def _on_library_select(self, item: QListWidgetItem):
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry:
            try:
                img = self.tex_manager.load_entry(entry)
                self._set_preview(img)
                self._current_image = img
                self.texture_selected.emit(img)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load texture:\n{e}")

    def _on_delete(self):
        item = self.list_library.currentItem()
        if item:
            entry = item.data(Qt.ItemDataRole.UserRole)
            if entry:
                self.tex_manager.remove_texture(entry)
                self._refresh_library()

    def _set_preview(self, img: Image.Image):
        pixmap = _pil_to_qpixmap(img, 128)
        self.lbl_preview.setPixmap(pixmap)

    @property
    def current_image(self) -> Image.Image | None:
        return self._current_image


class ParametersPanel(QGroupBox):
    """Displacement parameter controls."""

    params_changed = Signal()

    def __init__(self, parent=None):
        super().__init__("Parameters", parent)
        layout = QVBoxLayout(self)

        # Depth
        layout.addWidget(QLabel("Depth (mm):"))
        self.spin_depth = QDoubleSpinBox()
        self.spin_depth.setRange(0.0, 50.0)
        self.spin_depth.setValue(0.5)
        self.spin_depth.setSingleStep(0.1)
        self.spin_depth.setDecimals(3)
        self.spin_depth.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_depth)

        # Tile X
        layout.addWidget(QLabel("Tile X:"))
        self.spin_tile_x = QDoubleSpinBox()
        self.spin_tile_x.setRange(0.1, 50.0)
        self.spin_tile_x.setValue(1.0)
        self.spin_tile_x.setSingleStep(0.1)
        self.spin_tile_x.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_tile_x)

        # Tile Y
        layout.addWidget(QLabel("Tile Y:"))
        self.spin_tile_y = QDoubleSpinBox()
        self.spin_tile_y.setRange(0.1, 50.0)
        self.spin_tile_y.setValue(1.0)
        self.spin_tile_y.setSingleStep(0.1)
        self.spin_tile_y.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_tile_y)

        # Offset X
        layout.addWidget(QLabel("Offset X:"))
        self.spin_offset_x = QDoubleSpinBox()
        self.spin_offset_x.setRange(-10.0, 10.0)
        self.spin_offset_x.setValue(0.0)
        self.spin_offset_x.setSingleStep(0.05)
        self.spin_offset_x.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_offset_x)

        # Offset Y
        layout.addWidget(QLabel("Offset Y:"))
        self.spin_offset_y = QDoubleSpinBox()
        self.spin_offset_y.setRange(-10.0, 10.0)
        self.spin_offset_y.setValue(0.0)
        self.spin_offset_y.setSingleStep(0.05)
        self.spin_offset_y.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_offset_y)

        # Invert
        self.chk_invert = QCheckBox("Invert Texture")
        self.chk_invert.stateChanged.connect(self.params_changed)
        layout.addWidget(self.chk_invert)

        # Smoothing
        layout.addWidget(QLabel("Smoothing:"))
        self.spin_smooth = QSpinBox()
        self.spin_smooth.setRange(0, 20)
        self.spin_smooth.setValue(0)
        self.spin_smooth.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_smooth)

        # Contrast
        layout.addWidget(QLabel("Contrast:"))
        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(0.1, 5.0)
        self.spin_contrast.setValue(1.0)
        self.spin_contrast.setSingleStep(0.1)
        self.spin_contrast.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_contrast)

        # Clamp min
        layout.addWidget(QLabel("Clamp Min:"))
        self.spin_clamp_min = QDoubleSpinBox()
        self.spin_clamp_min.setRange(0.0, 1.0)
        self.spin_clamp_min.setValue(0.0)
        self.spin_clamp_min.setSingleStep(0.05)
        self.spin_clamp_min.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_clamp_min)

        # Clamp max
        layout.addWidget(QLabel("Clamp Max:"))
        self.spin_clamp_max = QDoubleSpinBox()
        self.spin_clamp_max.setRange(0.0, 1.0)
        self.spin_clamp_max.setValue(1.0)
        self.spin_clamp_max.setSingleStep(0.05)
        self.spin_clamp_max.valueChanged.connect(self.params_changed)
        layout.addWidget(self.spin_clamp_max)

        # Mode
        layout.addWidget(QLabel("Displacement Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["positive", "centered"])
        self.combo_mode.currentTextChanged.connect(self.params_changed)
        layout.addWidget(self.combo_mode)

        # Subdivision
        layout.addWidget(QLabel("Subdivision:"))
        self.combo_subdiv = QComboBox()
        self.combo_subdiv.addItems(["None", "1x", "2x", "3x"])
        self.combo_subdiv.currentIndexChanged.connect(self.params_changed)
        layout.addWidget(self.combo_subdiv)

    def get_params(self) -> DisplacementParams:
        return DisplacementParams(
            depth=self.spin_depth.value(),
            tile_x=self.spin_tile_x.value(),
            tile_y=self.spin_tile_y.value(),
            offset_x=self.spin_offset_x.value(),
            offset_y=self.spin_offset_y.value(),
            invert=self.chk_invert.isChecked(),
            smooth_kernel=self.spin_smooth.value(),
            contrast=self.spin_contrast.value(),
            clamp_min=self.spin_clamp_min.value(),
            clamp_max=self.spin_clamp_max.value(),
            mode=self.combo_mode.currentText(),
            subdivision=self.combo_subdiv.currentIndex(),
        )


class SelectionPanel(QGroupBox):
    """Selection mode and controls."""

    selection_mode_changed = Signal(bool)
    selection_type_changed = Signal(str)
    clear_selection = Signal()
    select_all = Signal()
    invert_selection = Signal()
    angle_threshold_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__("Selection", parent)
        layout = QVBoxLayout(self)

        # Mode toggle
        self.btn_select_mode = QPushButton("Enable Selection Mode")
        self.btn_select_mode.setCheckable(True)
        self.btn_select_mode.toggled.connect(self._on_mode_toggle)
        layout.addWidget(self.btn_select_mode)

        # Selection type
        layout.addWidget(QLabel("Selection Type:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Single Face", "Connected Region", "By Normal"])
        self.combo_type.currentTextChanged.connect(
            lambda t: self.selection_type_changed.emit(t)
        )
        layout.addWidget(self.combo_type)

        # Angle threshold
        layout.addWidget(QLabel("Angle Threshold (°):"))
        self.spin_angle = QDoubleSpinBox()
        self.spin_angle.setRange(1.0, 180.0)
        self.spin_angle.setValue(30.0)
        self.spin_angle.setSingleStep(5.0)
        self.spin_angle.valueChanged.connect(
            lambda v: self.angle_threshold_changed.emit(v)
        )
        layout.addWidget(self.spin_angle)

        # Selection info
        self.lbl_selection = QLabel("Selected: 0 faces")
        self.lbl_selection.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.lbl_selection)

        # Action buttons
        btn_row = QHBoxLayout()
        self.btn_select_all = QPushButton("All")
        self.btn_select_all.clicked.connect(self.select_all)
        btn_row.addWidget(self.btn_select_all)

        self.btn_invert = QPushButton("Invert")
        self.btn_invert.clicked.connect(self.invert_selection)
        btn_row.addWidget(self.btn_invert)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_selection)
        btn_row.addWidget(self.btn_clear)
        layout.addLayout(btn_row)

    def _on_mode_toggle(self, checked: bool):
        self.btn_select_mode.setText(
            "Disable Selection Mode" if checked else "Enable Selection Mode"
        )
        self.selection_mode_changed.emit(checked)

    def update_count(self, count: int):
        self.lbl_selection.setText(f"Selected: {count:,} faces")


class ActionPanel(QGroupBox):
    """Preview, apply, and export controls."""

    preview_requested = Signal()
    apply_requested = Signal()
    export_requested = Signal()
    wireframe_toggled = Signal()
    fit_view_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Actions", parent)
        layout = QVBoxLayout(self)

        # View controls
        view_row = QHBoxLayout()
        self.btn_wireframe = QPushButton("Wireframe")
        self.btn_wireframe.setCheckable(True)
        self.btn_wireframe.clicked.connect(self.wireframe_toggled)
        view_row.addWidget(self.btn_wireframe)

        self.btn_fit = QPushButton("Fit View")
        self.btn_fit.clicked.connect(self.fit_view_requested)
        view_row.addWidget(self.btn_fit)
        layout.addLayout(view_row)

        # Preview / Apply
        self.btn_preview = QPushButton("Preview Displacement")
        self.btn_preview.setEnabled(False)
        self.btn_preview.clicked.connect(self.preview_requested)
        layout.addWidget(self.btn_preview)

        self.btn_apply = QPushButton("Apply (Commit Changes)")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("background-color: #2d5a27; color: white;")
        self.btn_apply.clicked.connect(self.apply_requested)
        layout.addWidget(self.btn_apply)

        # Export
        self.btn_export = QPushButton("Export STL")
        self.btn_export.setEnabled(False)
        self.btn_export.setStyleSheet("background-color: #1a4a7a; color: white;")
        self.btn_export.clicked.connect(self.export_requested)
        layout.addWidget(self.btn_export)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Status
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.lbl_status)

    def set_mesh_loaded(self, loaded: bool):
        self.btn_export.setEnabled(loaded)

    def set_ready_for_displacement(self, ready: bool):
        self.btn_preview.setEnabled(ready)
        self.btn_apply.setEnabled(ready)

    def show_progress(self, value: int):
        self.progress.setVisible(True)
        self.progress.setValue(value)

    def hide_progress(self):
        self.progress.setVisible(False)

    def set_status(self, text: str):
        self.lbl_status.setText(text)
