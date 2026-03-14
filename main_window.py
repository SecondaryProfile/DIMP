import json
import os
from typing import List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QPushButton, QSpinBox, QLabel, QComboBox, QFileDialog,
    QDockWidget, QFrame, QColorDialog, QMessageBox, QScrollArea, QCheckBox, QButtonGroup,
    QFontComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut, QAction

from models import IconPalette, ICON_PALETTES, ShapeType, ToolMode, Shape
from canvas import Canvas


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIMP")
        self.setGeometry(100, 100, 1100, 780)
        self.current_palette = ICON_PALETTES[0]
        self.canvas = Canvas(512, 512)
        self.canvas.set_background(QColor(self.current_palette.background))
        self._setup_ui()
        self._setup_toolbar()
        self._setup_sidebar()   # creates checkboxes first
        self._setup_menubar()   # connects menu actions to those checkboxes
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.canvas.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self.canvas.redo)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet("QScrollArea { background: #404040; }")
        outer.addWidget(scroll)
        central.setLayout(outer)

    def _setup_menubar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)

        load_action = QAction("Load", self)
        load_action.setShortcut(QKeySequence("Ctrl+O"))
        load_action.triggered.connect(self._load_project)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        export_action = QAction("Export SVG", self)
        export_action.triggered.connect(self._export_svg)
        file_menu.addAction(export_action)

        export_ios_action = QAction("Export for iOS (Xcode)…", self)
        export_ios_action.triggered.connect(self._export_ios)
        file_menu.addAction(export_ios_action)

        export_android_action = QAction("Export for Android Studio…", self)
        export_android_action.triggered.connect(self._export_android)
        file_menu.addAction(export_android_action)

        # View menu
        view_menu = menubar.addMenu("View")

        show_bg_action = QAction("Show Background", self)
        show_bg_action.setCheckable(True)
        show_bg_action.setChecked(self._show_bg_check.isChecked())
        show_bg_action.setShortcut(QKeySequence("Alt+B"))
        show_bg_action.triggered.connect(self._show_bg_check.setChecked)
        self._show_bg_check.toggled.connect(show_bg_action.setChecked)
        view_menu.addAction(show_bg_action)

        snap_action = QAction("Snap on Rotate", self)
        snap_action.setCheckable(True)
        snap_action.setChecked(self._snap_check.isChecked())
        snap_action.setShortcut(QKeySequence("Alt+S"))
        snap_action.triggered.connect(self._snap_check.setChecked)
        self._snap_check.toggled.connect(snap_action.setChecked)
        view_menu.addAction(snap_action)

        grid_snap_action = QAction("Snap to Grid", self)
        grid_snap_action.setCheckable(True)
        grid_snap_action.setChecked(self._grid_snap_check.isChecked())
        grid_snap_action.setShortcut(QKeySequence("Alt+G"))
        grid_snap_action.triggered.connect(self._grid_snap_check.setChecked)
        self._grid_snap_check.toggled.connect(grid_snap_action.setChecked)
        view_menu.addAction(grid_snap_action)

    def _toolbar_group(self, label: str, widgets: list) -> QWidget:
        group = QWidget()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(2, 1, 2, 1)
        vbox.setSpacing(0)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        for w in widgets:
            row.addWidget(w)
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 9px; color: #111;")
        vbox.addLayout(row)
        vbox.addWidget(lbl)
        group.setLayout(vbox)
        return group

    def _toolbar_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    def _setup_toolbar(self):
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # --- Tools ---
        self._tool_btn_group = QButtonGroup(self)
        self._tool_btn_group.setExclusive(True)

        select_btn = QPushButton("Select")
        select_btn.setCheckable(True)
        select_btn.clicked.connect(lambda: self.canvas.set_mode(ToolMode.SELECT))
        self._tool_btn_group.addButton(select_btn)
        tool_btns = [select_btn]

        for label, tool in [("Line", ShapeType.LINE), ("Circle", ShapeType.CIRCLE),
                             ("Square", ShapeType.SQUARE), ("Triangle", ShapeType.TRIANGLE),
                             ("Path", ShapeType.PATH), ("Text", ShapeType.TEXT)]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, t=tool: self.canvas.set_tool(t))
            self._tool_btn_group.addButton(btn)
            tool_btns.append(btn)

        self._tool_btn_group.buttons()[1].setChecked(True)
        toolbar.addWidget(self._toolbar_group("Tools", tool_btns))
        toolbar.addWidget(self._toolbar_sep())

        # --- Canvas (width) ---
        width_lbl = QLabel("Width:")
        width_spin = QSpinBox()
        width_spin.setRange(1, 20)
        width_spin.setValue(10)
        width_spin.setMaximumWidth(55)
        width_spin.valueChanged.connect(lambda v: self.canvas.set_stroke_width(v))
        toolbar.addWidget(self._toolbar_group("Canvas", [width_lbl, width_spin]))
        toolbar.addWidget(self._toolbar_sep())

        # --- Color ---
        self._palette_combo = QComboBox()
        self._palette_combo.addItems([p.name for p in ICON_PALETTES])
        self._palette_combo.setMaximumWidth(110)
        self._palette_combo.currentIndexChanged.connect(
            lambda i: self._apply_palette(ICON_PALETTES[i])
        )

        self._swatch_btns: List[QPushButton] = []
        swatch_widgets = []
        for sw_label in ("BG", "Icon", "Accent"):
            w = QWidget()
            col = QVBoxLayout()
            col.setContentsMargins(2, 0, 2, 0)
            col.setSpacing(1)
            swatch = QPushButton()
            swatch.setFixedSize(26, 22)
            lbl = QLabel(sw_label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 9px; color: #aaa;")
            col.addWidget(swatch)
            col.addWidget(lbl)
            w.setLayout(col)
            swatch_widgets.append(w)
            self._swatch_btns.append(swatch)

        custom_btn = QPushButton("...")
        custom_btn.setFixedWidth(28)
        custom_btn.setToolTip("Custom color")
        custom_btn.clicked.connect(self._pick_custom_color)

        self._active_color_btn = QPushButton()
        self._active_color_btn.setFixedSize(22, 22)
        self._active_color_btn.setFlat(True)
        self._active_color_btn.setEnabled(False)

        color_widgets = [self._palette_combo] + swatch_widgets + [custom_btn, self._active_color_btn]
        toolbar.addWidget(self._toolbar_group("Color", color_widgets))
        toolbar.addWidget(self._toolbar_sep())

        # --- Text ---
        self._font_combo = QFontComboBox()
        self._font_combo.setMaximumWidth(160)
        self._font_combo.setCurrentFont(QFont("Arial Rounded MT Bold"))
        self._font_combo.currentFontChanged.connect(
            lambda f: self.canvas.set_text_font_family(f.family())
        )

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(6, 200)
        self._font_size_spin.setValue(24)
        self._font_size_spin.setSuffix("pt")
        self._font_size_spin.setMaximumWidth(60)
        self._font_size_spin.valueChanged.connect(
            lambda v: self.canvas.set_text_font_size(v)
        )

        toolbar.addWidget(self._toolbar_group("Text", [self._font_combo, self._font_size_spin]))
        toolbar.addWidget(self._toolbar_sep())

        # --- Utility ---
        grid_btn = QPushButton("Grid")
        grid_btn.setCheckable(True)
        grid_btn.setChecked(True)
        grid_btn.toggled.connect(
            lambda c: (setattr(self.canvas, 'grid_enabled', c), self.canvas.update())
        )

        undo_btn = QPushButton("Undo")
        undo_btn.clicked.connect(self.canvas.undo)

        redo_btn = QPushButton("Redo")
        redo_btn.clicked.connect(self.canvas.redo)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: white; font-weight: bold; border-radius: 3px; padding: 2px 6px; }"
            "QPushButton:hover { background-color: #e74c3c; }"
            "QPushButton:pressed { background-color: #922b21; }"
        )
        clear_btn.clicked.connect(self._confirm_clear)

        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet(
            "QPushButton { background-color: #7f1a1a; color: white; font-weight: bold; border-radius: 3px; padding: 2px 6px; }"
            "QPushButton:hover { background-color: #a02020; }"
            "QPushButton:pressed { background-color: #5a1010; }"
        )
        quit_btn.clicked.connect(self._confirm_quit)

        toolbar.addWidget(self._toolbar_group("Utility", [grid_btn, undo_btn, redo_btn, clear_btn, quit_btn]))

        self._refresh_swatches()

    def _setup_sidebar(self):
        dock = QDockWidget("Properties", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setMinimumWidth(160)

        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)

        lbl = QLabel("Canvas Size")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)

        for attr, label in [("_canvas_w_spin", "W:"), ("_canvas_h_spin", "H:")]:
            row = QHBoxLayout()
            spin = QSpinBox()
            spin.setRange(64, 2048)
            spin.setValue(512)
            spin.setSingleStep(64)
            setattr(self, attr, spin)
            row.addWidget(QLabel(label))
            row.addWidget(spin)
            layout.addLayout(row)

        square_btn = QPushButton("Make Square")
        square_btn.clicked.connect(self._make_square)
        layout.addWidget(square_btn)

        apply_btn = QPushButton("Apply Size")
        apply_btn.clicked.connect(self._apply_canvas_size)
        layout.addWidget(apply_btn)

        layout.addWidget(self._separator())

        cr_lbl = QLabel("Corner Radius")
        cr_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(cr_lbl)

        cr_row = QHBoxLayout()
        self._corner_radius_spin = QSpinBox()
        self._corner_radius_spin.setRange(0, 200)
        self._corner_radius_spin.setValue(0)
        self._corner_radius_spin.setSuffix(" px")
        self._corner_radius_spin.setToolTip("Rounded corners for squares (also updates selected shapes)")
        self._corner_radius_spin.valueChanged.connect(lambda v: self.canvas.set_default_corner_radius(float(v)))
        cr_row.addWidget(QLabel("R:"))
        cr_row.addWidget(self._corner_radius_spin)
        layout.addLayout(cr_row)

        layout.addWidget(self._separator())

        view_lbl = QLabel("View")
        view_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(view_lbl)

        self._show_bg_check = QCheckBox("Show Background")
        self._show_bg_check.setChecked(True)
        self._show_bg_check.toggled.connect(self.canvas.set_show_background)
        layout.addWidget(self._show_bg_check)

        self._snap_check = QCheckBox("Snap on Rotate")
        self._snap_check.setChecked(True)
        self._snap_check.setToolTip("Hold Shift while rotating to step in 22.5° increments")
        self._snap_check.toggled.connect(self.canvas.set_snap_enabled)
        layout.addWidget(self._snap_check)

        self._grid_snap_check = QCheckBox()
        self._grid_snap_check.setChecked(True)
        self._grid_snap_check.toggled.connect(self.canvas.set_grid_snap_enabled)
        self._grid_snap_check.hide()

        layout.addWidget(self._separator())

        sel_lbl = QLabel("Selected Shape")
        sel_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(sel_lbl)

        self._sel_color_widget = QWidget()
        sel_color_row = QHBoxLayout()
        sel_color_row.setContentsMargins(0, 0, 0, 0)
        sel_color_row.addWidget(QLabel("Color:"))
        self._sel_color_btn = QPushButton()
        self._sel_color_btn.setFixedSize(40, 22)
        self._sel_color_btn.setToolTip("Click to change selected shape color")
        self._sel_color_btn.clicked.connect(self._pick_selected_shape_color)
        sel_color_row.addWidget(self._sel_color_btn)
        sel_color_row.addStretch()
        self._sel_color_widget.setLayout(sel_color_row)
        self._sel_color_widget.setEnabled(False)
        layout.addWidget(self._sel_color_widget)

        layout.addWidget(self._separator())

        instructions = QLabel(
            "Left drag: Draw\n"
            "Right drag: Rotate\n"
            "Wheel: Fine rotate\n"
            "Delete: Remove shape\n"
            "Ctrl+Z / Ctrl+Y: Undo/Redo\n"
            "\nText tool:\n"
            "Click: Place text\n"
            "Double-click: Edit text\n"
            "Drag corner handle: Resize\n"
            "\nPath tool:\n"
            "Click: Add point\n"
            "Click start: Close path\n"
            "Right-click: Finish open\n"
            "Double-click: Finish open\n"
            "Delete: Remove last point\n"
            "Escape: Cancel path\n"
            "\nPath curves:\n"
            "Select path, drag\n"
            "orange handles to curve"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(instructions)

        layout.addWidget(self._separator())

        self.info_label = QLabel("Ready")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addStretch()
        widget.setLayout(layout)
        dock.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.canvas.shape_selected.connect(self._on_shape_selected)
        self.canvas.selection_cleared.connect(lambda: self._sel_color_widget.setEnabled(False))

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _confirm_clear(self):
        reply = QMessageBox.question(
            self, "Clear Canvas",
            "Delete all shapes? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas.clear_all()

    def _confirm_quit(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Quit")
        msg.setText("Do you want to save your changes before quitting?")
        save_btn = msg.addButton("Save and Quit", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton("Quit Without Saving", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(save_btn)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == save_btn:
            if self._save_project():
                QApplication.quit()
        elif clicked == discard_btn:
            QApplication.quit()

    def _apply_palette(self, palette: IconPalette):
        old = self.current_palette
        self.current_palette = palette
        self.canvas.set_background(QColor(palette.background))
        for shape in self.canvas.shapes:
            if shape.stroke_color.lower() == old.icon.lower():
                shape.stroke_color = palette.icon
            elif shape.stroke_color.lower() == old.accent.lower():
                shape.stroke_color = palette.accent
        self.canvas.update()
        self._refresh_swatches()
        self._set_stroke_color(palette.icon)

    def _refresh_swatches(self):
        p = self.current_palette
        for i, (color, role) in enumerate([(p.background, "BG"),
                                            (p.icon, "Icon"),
                                            (p.accent, "Accent")]):
            btn = self._swatch_btns[i]
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {color}; border: 1px solid #888; border-radius: 2px; }}"
                f"QPushButton:hover {{ background-color: {color}; border: 1px solid #ccc; border-radius: 2px; }}"
            )
            btn.setToolTip(f"{role}: {color}")
            try:
                btn.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            btn.clicked.connect(lambda _, c=color: self._set_stroke_color(c))

    def _set_stroke_color(self, hex_color: str):
        self.canvas.set_stroke_color(QColor(hex_color))
        self._active_color_btn.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid #888; border-radius: 2px;"
        )

    def _pick_custom_color(self):
        color = QColorDialog.getColor(self.canvas.stroke_color, self)
        if color.isValid():
            self._set_stroke_color(color.name())

    def _make_square(self):
        self._canvas_h_spin.setValue(self._canvas_w_spin.value())

    def _apply_canvas_size(self):
        self.canvas.resize_canvas(self._canvas_w_spin.value(), self._canvas_h_spin.value())

    def _on_shape_selected(self, shape: Shape):
        self._corner_radius_spin.blockSignals(True)
        self._corner_radius_spin.setValue(int(shape.corner_radius))
        self._corner_radius_spin.blockSignals(False)
        self._sel_color_widget.setEnabled(True)
        self._sel_color_btn.setStyleSheet(
            f"QPushButton {{ background-color: {shape.stroke_color}; border: 1px solid #888; border-radius: 2px; }}"
        )
        info = (f"Type: {shape.shape_type.value}\n"
                f"Rotation: {shape.rotation:.1f}\n"
                f"Stroke: {shape.stroke_width}\n"
                f"Color: {shape.stroke_color}")
        if shape.shape_type == ShapeType.TEXT:
            info += f"\nText: {shape.text}\nFont: {shape.font_family} {shape.font_size}pt"
        self.info_label.setText(info)

    def _pick_selected_shape_color(self):
        if not self.canvas.selected_shapes:
            return
        current = QColor(self.canvas.selected_shapes[-1].stroke_color)
        color = QColorDialog.getColor(current, self)
        if color.isValid():
            self.canvas._save_state()
            for shape in self.canvas.selected_shapes:
                shape.stroke_color = color.name()
            self.canvas.selected_shapes.clear()
            self._sel_color_widget.setEnabled(False)
            self.canvas.update()

    def _export_svg(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export SVG", "", "SVG Files (*.svg);;All Files (*)"
        )
        if filename:
            svg = self.canvas.get_svg_export(
                self.current_palette, self._show_bg_check.isChecked()
            )
            with open(filename, 'w') as f:
                f.write(svg)
            QMessageBox.information(self, "Success", f"Exported to {filename}")

    def _export_ios(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder for iOS export")
        if not folder:
            return
        appiconset = os.path.join(folder, "AppIcon.appiconset")
        os.makedirs(appiconset, exist_ok=True)

        # (logical_size, scale, idiom)
        specs = [
            (20, 1, "iphone"), (20, 2, "iphone"), (20, 3, "iphone"),
            (29, 1, "iphone"), (29, 2, "iphone"), (29, 3, "iphone"),
            (40, 1, "iphone"), (40, 2, "iphone"), (40, 3, "iphone"),
            (60, 2, "iphone"), (60, 3, "iphone"),
            (20, 1, "ipad"),   (20, 2, "ipad"),
            (29, 1, "ipad"),   (29, 2, "ipad"),
            (40, 1, "ipad"),   (40, 2, "ipad"),
            (76, 1, "ipad"),   (76, 2, "ipad"),
            (1024, 1, "ios-marketing"),
        ]

        images_json = []
        seen = set()
        for logical, scale, idiom in specs:
            pixel = int(logical * scale)
            filename = f"icon-{logical}@{scale}x-{idiom}.png"
            if pixel not in seen:
                pm = self.canvas.render_to_pixmap(pixel)
                pm.save(os.path.join(appiconset, filename), "PNG")
                seen.add(pixel)
            images_json.append({
                "filename": filename,
                "idiom": idiom,
                "scale": f"{scale}x",
                "size": f"{logical}x{logical}",
            })

        contents = {"images": images_json, "info": {"author": "xcode", "version": 1}}
        with open(os.path.join(appiconset, "Contents.json"), "w") as f:
            json.dump(contents, f, indent=2)

        QMessageBox.information(
            self, "iOS Export Done",
            f"AppIcon.appiconset written to:\n{appiconset}\n\n"
            "Drag the AppIcon.appiconset folder into your Xcode Assets.xcassets."
        )

    def _export_android(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder for Android export")
        if not folder:
            return
        res_dir = os.path.join(folder, "res")
        densities = [
            ("mipmap-mdpi",    48),
            ("mipmap-hdpi",    72),
            ("mipmap-xhdpi",   96),
            ("mipmap-xxhdpi",  144),
            ("mipmap-xxxhdpi", 192),
        ]
        for density, size in densities:
            dest = os.path.join(res_dir, density)
            os.makedirs(dest, exist_ok=True)
            pm = self.canvas.render_to_pixmap(size)
            pm.save(os.path.join(dest, "ic_launcher.png"), "PNG")

        QMessageBox.information(
            self, "Android Export Done",
            f"res/ folder written to:\n{res_dir}\n\n"
            "Copy the res/ folder into your Android Studio project's app/src/main/ directory."
        )

    def _save_project(self) -> bool:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Icon Project Files (*.iconproj);;All Files (*)"
        )
        if not filename:
            return False
        data = {
            "shapes": [s.to_dict() for s in self.canvas.shapes],
            "palette": self.current_palette.name,
            "show_background": self._show_bg_check.isChecked(),
            "canvas_w": self.canvas.canvas_w,
            "canvas_h": self.canvas.canvas_h,
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        QMessageBox.information(self, "Success", f"Saved to {filename}")
        return True

    def _load_project(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Icon Project Files (*.iconproj);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.canvas.shapes = [Shape.from_dict(s) for s in data["shapes"]]
                palette_name = data.get("palette")
                for p in ICON_PALETTES:
                    if p.name == palette_name:
                        self._palette_combo.setCurrentIndex(ICON_PALETTES.index(p))
                        self._apply_palette(p)
                        break
                self._show_bg_check.setChecked(data.get("show_background", True))
                cw, ch = data.get("canvas_w", 512), data.get("canvas_h", 512)
                self.canvas.resize_canvas(cw, ch)
                self._canvas_w_spin.setValue(cw)
                self._canvas_h_spin.setValue(ch)
                self.canvas.update()
                QMessageBox.information(self, "Success", f"Loaded from {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")
