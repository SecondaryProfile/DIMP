import copy
import math
from collections import deque
from typing import Optional, List

from PyQt6.QtWidgets import QWidget, QInputDialog
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QEvent
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QMouseEvent, QWheelEvent, QKeyEvent, QPolygonF,
    QPainterPath, QFont, QFontMetrics, QPixmap
)

from models import CLOSE_THRESHOLD, IconPalette, ShapeType, ToolMode, Shape


class Canvas(QWidget):
    shape_selected = pyqtSignal(Shape)
    selection_cleared = pyqtSignal()

    def __init__(self, canvas_w: int = 512, canvas_h: int = 512):
        super().__init__()
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.zoom = 1.0
        self.shapes: List[Shape] = []
        self.current_tool = ShapeType.LINE
        self.stroke_width = 10.0
        self.stroke_color = QColor("#1a1a1a")
        self.default_corner_radius = 0.0
        self.tool_mode = ToolMode.DRAW
        self.is_drawing = False
        self.start_pos = QPoint()
        self.current_pos = QPoint()
        self.selected_shapes: List[Shape] = []
        self.hover_shape: Optional[Shape] = None
        self.rotating_shape: Optional[Shape] = None
        self.rotation_start_angle = 0.0
        self.moving_shapes: List[Shape] = []
        self.move_start_pos = QPoint()
        self.move_start_pos_snapped = QPoint()
        self.move_origins: List[tuple] = []
        self.path_points: List[List[float]] = []
        self.snap_endpoint: Optional[QPoint] = None
        self.curve_dragging: Optional[tuple] = None
        self.background_color = QColor("#f8f8f8")
        self.show_background = True
        self.grid_enabled = True
        self.snap_enabled = True
        self.grid_snap_enabled = True
        self.text_font_family = "Arial Rounded MT Bold"
        self.text_font_size = 24
        self.text_resize_shape: Optional[Shape] = None
        self.text_resize_start = QPoint()
        self.text_resize_start_size = 24
        self.text_resize_origin_h = 1.0
        self.cursor_pos = QPoint()
        self.undo_stack = deque(maxlen=5)
        self.redo_stack = deque(maxlen=5)
        self.setFixedSize(canvas_w, canvas_h)
        self.setMouseTracking(True)
        self.setFocus()

    # --- zoom ---

    def _map_pos(self, pos: QPoint) -> QPoint:
        """Convert display (widget) coordinates to logical canvas coordinates."""
        if self.zoom == 1.0:
            return pos
        return QPoint(int(pos.x() / self.zoom), int(pos.y() / self.zoom))

    def _apply_zoom(self, new_zoom: float):
        self.zoom = max(0.25, min(4.0, new_zoom))
        self.setFixedSize(int(self.zoom * self.canvas_w), int(self.zoom * self.canvas_h))
        self.update()

    def event(self, event):
        if event.type() == QEvent.Type.NativeGesture:
            try:
                if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                    delta = event.value() - 1.0
                    self._apply_zoom(self.zoom * (1.0 + delta * 0.5))
                    return True
            except AttributeError:
                pass
        return super().event(event)

    # --- canvas operations ---

    def resize_canvas(self, w: int, h: int):
        self.canvas_w = w
        self.canvas_h = h
        self.setFixedSize(int(self.zoom * w), int(self.zoom * h))
        self.update()

    def set_background(self, color: QColor):
        self.background_color = color
        self.update()

    def set_show_background(self, show: bool):
        self.show_background = show
        self.update()

    def _save_state(self):
        self.undo_stack.append(copy.deepcopy(self.shapes))
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.shapes))
            self.shapes = self.undo_stack.pop()
            self.selected_shapes.clear()
            self.update()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.shapes))
            self.shapes = self.redo_stack.pop()
            self.selected_shapes.clear()
            self.update()

    def set_mode(self, mode: ToolMode):
        self.tool_mode = mode
        self.is_drawing = False
        self.path_points.clear()
        self.moving_shapes.clear()
        self.rotating_shape = None
        self.curve_dragging = None
        cursor = Qt.CursorShape.ArrowCursor if mode == ToolMode.SELECT else Qt.CursorShape.CrossCursor
        self.setCursor(cursor)
        self.update()

    def set_tool(self, tool: ShapeType):
        self.current_tool = tool
        self.set_mode(ToolMode.DRAW)

    def set_stroke_width(self, width: float):
        self.stroke_width = width

    def set_stroke_color(self, color: QColor):
        self.stroke_color = color

    def set_snap_enabled(self, enabled: bool):
        self.snap_enabled = enabled

    def set_grid_snap_enabled(self, enabled: bool):
        self.grid_snap_enabled = enabled
        self.update()

    def set_text_font_family(self, family: str):
        self.text_font_family = family

    def set_text_font_size(self, size: int):
        self.text_font_size = size

    def set_default_corner_radius(self, r: float):
        self.default_corner_radius = r
        for s in self.selected_shapes:
            s.corner_radius = r
        self.update()

    # --- snapping helpers ---

    def _snap_to_grid(self, pos: QPoint) -> QPoint:
        g = 20
        return QPoint(round(pos.x() / g) * g, round(pos.y() / g) * g)

    def _snap_draw_pos(self, raw: QPoint) -> QPoint:
        dx = raw.x() - self.start_pos.x()
        dy = raw.y() - self.start_pos.y()
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return raw
        angle_deg = math.degrees(math.atan2(dy, dx))
        snapped_deg = round(angle_deg / 22.5) * 22.5
        snapped_rad = math.radians(snapped_deg)
        return QPoint(
            int(self.start_pos.x() + dist * math.cos(snapped_rad)),
            int(self.start_pos.y() + dist * math.sin(snapped_rad)),
        )

    def _snap_rotation(self, angle: float) -> float:
        return round(angle / 22.5) * 22.5

    def _get_all_endpoints(self) -> List[QPoint]:
        pts = []
        for shape in self.shapes:
            if shape.shape_type == ShapeType.PATH:
                if shape.points:
                    pts.append(QPoint(int(shape.points[0][0]), int(shape.points[0][1])))
                    if len(shape.points) > 1:
                        pts.append(QPoint(int(shape.points[-1][0]), int(shape.points[-1][1])))
            else:
                pts.append(QPoint(int(shape.start_x), int(shape.start_y)))
                pts.append(QPoint(int(shape.end_x), int(shape.end_y)))
        return pts

    def _find_snap_endpoint(self, pos: QPoint) -> Optional[QPoint]:
        for ep in self._get_all_endpoints():
            if math.sqrt((pos.x() - ep.x()) ** 2 + (pos.y() - ep.y()) ** 2) < CLOSE_THRESHOLD * 2:
                return ep
        return None

    def _get_path_handle_at(self, pos: QPoint, shape: Shape) -> Optional[int]:
        pts = shape.points
        n = len(pts)
        if n < 2:
            return None
        segs = n if shape.closed else n - 1
        for i in range(segs):
            end_idx = 0 if (shape.closed and i == n - 1) else i + 1
            x1, y1 = pts[i]
            x2, y2 = pts[end_idx]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            c = shape.curves[i] if i < len(shape.curves) else 0.0
            dx, dy_seg = x2 - x1, y2 - y1
            length = math.sqrt(dx * dx + dy_seg * dy_seg)
            if length > 0:
                nx, ny = -dy_seg / length, dx / length
                hx, hy = mx + nx * c, my + ny * c
            else:
                hx, hy = mx, my
            if math.sqrt((pos.x() - hx) ** 2 + (pos.y() - hy) ** 2) < 12:
                return i
        return None

    def _get_text_resize_handle(self, pos: QPoint, shape: Shape) -> bool:
        hx, hy = int(shape.end_x), int(shape.end_y)
        return math.sqrt((pos.x() - hx) ** 2 + (pos.y() - hy) ** 2) < 8

    def _recompute_text_bounds(self, shape: Shape):
        fm = QFontMetrics(QFont(shape.font_family, shape.font_size))
        br = fm.boundingRect(shape.text)
        shape.end_x = shape.start_x + br.width()
        shape.end_y = shape.start_y + br.height()

    # --- mouse events ---

    def mousePressEvent(self, event: QMouseEvent):
        pos = self._map_pos(event.pos())
        self.setFocus()
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if self.tool_mode == ToolMode.SELECT:
            if event.button() == Qt.MouseButton.LeftButton:
                for shape in self.selected_shapes:
                    if shape.shape_type == ShapeType.TEXT and self._get_text_resize_handle(pos, shape):
                        self._save_state()
                        self.text_resize_shape = shape
                        self.text_resize_start = pos
                        self.text_resize_start_size = shape.font_size
                        self.text_resize_origin_h = max(1.0, shape.end_y - shape.start_y)
                        return
                for shape in self.selected_shapes:
                    if shape.shape_type == ShapeType.PATH:
                        handle_idx = self._get_path_handle_at(pos, shape)
                        if handle_idx is not None:
                            self._save_state()
                            self.curve_dragging = (shape, handle_idx)
                            return
                hit = self._hit_test(pos)
                if hit:
                    if shift:
                        if hit in self.selected_shapes:
                            self.selected_shapes.remove(hit)
                        else:
                            self.selected_shapes.append(hit)
                    else:
                        if hit not in self.selected_shapes:
                            self.selected_shapes = [hit]
                    if self.selected_shapes:
                        self._save_state()
                        self.moving_shapes = list(self.selected_shapes)
                        self.move_start_pos = pos
                        self.move_start_pos_snapped = self._snap_to_grid(pos)
                        self.move_origins = [
                            (s.start_x, s.start_y, s.end_x, s.end_y, copy.deepcopy(s.points))
                            for s in self.moving_shapes
                        ]
                        self.shape_selected.emit(self.selected_shapes[-1])
                else:
                    if not shift:
                        self.selected_shapes.clear()
                        self.selection_cleared.emit()
                    self.update()
            elif event.button() == Qt.MouseButton.RightButton:
                self.rotating_shape = self._hit_test(pos)
                if self.rotating_shape:
                    self._save_state()
                    self.rotation_start_angle = self._calculate_angle(pos)
        else:
            if event.button() == Qt.MouseButton.LeftButton:
                if self.current_tool == ShapeType.PATH:
                    snapped_ep = self._find_snap_endpoint(pos)
                    if snapped_ep:
                        pos = snapped_ep
                    elif self.grid_snap_enabled:
                        pos = self._snap_to_grid(pos)
                    fx, fy = float(pos.x()), float(pos.y())
                    if self.path_points and len(self.path_points) >= 3:
                        x0, y0 = self.path_points[0]
                        if math.sqrt((fx - x0) ** 2 + (fy - y0) ** 2) < CLOSE_THRESHOLD:
                            self._finalize_path(closed=True)
                            return
                    self.path_points.append([fx, fy])
                    self.update()
                elif self.current_tool == ShapeType.TEXT:
                    if self.grid_snap_enabled:
                        pos = self._snap_to_grid(pos)
                    text, ok = QInputDialog.getText(self, "Add Text", "Enter text:")
                    if ok and text.strip():
                        self._save_state()
                        font = QFont(self.text_font_family, self.text_font_size)
                        fm = QFontMetrics(font)
                        br = fm.boundingRect(text)
                        self.shapes.append(Shape(
                            shape_type=ShapeType.TEXT,
                            start_x=float(pos.x()),
                            start_y=float(pos.y()),
                            end_x=float(pos.x() + br.width()),
                            end_y=float(pos.y() + br.height()),
                            stroke_width=self.stroke_width,
                            stroke_color=self.stroke_color.name(),
                            text=text,
                            font_family=self.text_font_family,
                            font_size=self.text_font_size,
                        ))
                        self.update()
                else:
                    start = pos
                    snapped_ep = self._find_snap_endpoint(start)
                    if snapped_ep:
                        start = snapped_ep
                    elif self.grid_snap_enabled:
                        start = self._snap_to_grid(start)
                    self.start_pos = start
                    self.current_pos = start
                    self.is_drawing = True
            elif event.button() == Qt.MouseButton.RightButton:
                if self.current_tool == ShapeType.PATH and self.path_points:
                    ep = self._find_snap_endpoint(pos)
                    final = ep if ep else (self._snap_to_grid(pos) if self.grid_snap_enabled else pos)
                    self.path_points.append([float(final.x()), float(final.y())])
                    if len(self.path_points) >= 2:
                        self._finalize_path(closed=False)
                    else:
                        self.path_points.clear()
                        self.update()
                else:
                    self.rotating_shape = self._hit_test(pos)
                    if self.rotating_shape:
                        self._save_state()
                        self.rotation_start_angle = self._calculate_angle(pos)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.tool_mode == ToolMode.SELECT:
                pos = self._map_pos(event.pos())
                hit = self._hit_test(pos)
                if hit and hit.shape_type == ShapeType.TEXT:
                    text, ok = QInputDialog.getText(
                        self, "Edit Text", "Edit text:", text=hit.text)
                    if ok:
                        self._save_state()
                        hit.text = text.strip() or hit.text
                        self._recompute_text_bounds(hit)
                        self.shape_selected.emit(hit)
                        self.update()
                    return
            if (self.tool_mode == ToolMode.DRAW
                    and self.current_tool == ShapeType.PATH
                    and len(self.path_points) >= 2):
                self._finalize_path(closed=False)

    def _finalize_path(self, closed: bool):
        if len(self.path_points) < 2:
            self.path_points.clear()
            self.update()
            return
        self._save_state()
        pts = self.path_points[:]
        self.shapes.append(Shape(
            shape_type=ShapeType.PATH,
            start_x=pts[0][0], start_y=pts[0][1],
            end_x=pts[-1][0], end_y=pts[-1][1],
            stroke_width=self.stroke_width,
            stroke_color=self.stroke_color.name(),
            corner_radius=self.default_corner_radius,
            points=pts,
            curves=[],
            closed=closed,
        ))
        self.path_points.clear()
        self.snap_endpoint = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = self._map_pos(event.pos())
        self.cursor_pos = pos
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        self.current_pos = pos

        if self.tool_mode == ToolMode.SELECT and not self.moving_shapes and not self.rotating_shape and not self.curve_dragging and not self.text_resize_shape:
            prev = self.hover_shape
            self.hover_shape = self._hit_test(pos)
            if self.hover_shape != prev:
                self.update()

        if self.text_resize_shape:
            dy = pos.y() - self.text_resize_start.y()
            new_size = max(6, int(self.text_resize_start_size * (1.0 + dy / self.text_resize_origin_h)))
            if new_size != self.text_resize_shape.font_size:
                self.text_resize_shape.font_size = new_size
                self._recompute_text_bounds(self.text_resize_shape)
            self.update()
        elif self.curve_dragging:
            shape, seg_idx = self.curve_dragging
            pts = shape.points
            n = len(pts)
            end_idx = 0 if (shape.closed and seg_idx == n - 1) else seg_idx + 1
            x1, y1 = pts[seg_idx]
            x2, y2 = pts[end_idx]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy_seg = x2 - x1, y2 - y1
            length = math.sqrt(dx * dx + dy_seg * dy_seg)
            if length > 0:
                nx, ny = -dy_seg / length, dx / length
                cx_v = pos.x() - mx
                cy_v = pos.y() - my
                offset = cx_v * nx + cy_v * ny
                while len(shape.curves) <= seg_idx:
                    shape.curves.append(0.0)
                shape.curves[seg_idx] = offset
            self.update()
        elif self.moving_shapes:
            if self.grid_enabled:
                snapped_pos = self._snap_to_grid(pos)
                dx = snapped_pos.x() - self.move_start_pos_snapped.x()
                dy = snapped_pos.y() - self.move_start_pos_snapped.y()
            else:
                dx = pos.x() - self.move_start_pos.x()
                dy = pos.y() - self.move_start_pos.y()
            for shape, (ox1, oy1, ox2, oy2, opoints) in zip(self.moving_shapes, self.move_origins):
                shape.start_x = ox1 + dx
                shape.start_y = oy1 + dy
                shape.end_x = ox2 + dx
                shape.end_y = oy2 + dy
                shape.points = [[p[0] + dx, p[1] + dy] for p in opoints]
            self.update()
        elif self.current_tool == ShapeType.PATH and self.tool_mode == ToolMode.DRAW:
            ep = self._find_snap_endpoint(pos)
            self.snap_endpoint = ep
            if ep:
                self.current_pos = ep
            elif self.grid_snap_enabled:
                self.current_pos = self._snap_to_grid(pos)
            self.update()
        elif self.is_drawing:
            if self.snap_enabled and shift:
                self.current_pos = self._snap_draw_pos(pos)
            elif self.grid_snap_enabled:
                self.current_pos = self._snap_to_grid(pos)
            ep = self._find_snap_endpoint(pos)
            if ep:
                self.current_pos = ep
                self.snap_endpoint = ep
            else:
                self.snap_endpoint = None
            self.update()
        elif self.rotating_shape:
            angle = self._calculate_angle(pos)
            delta = angle - self.rotation_start_angle
            self.rotation_start_angle = angle
            new_rot = self.rotating_shape.rotation + delta
            self.rotating_shape.rotation = self._snap_rotation(new_rot) if (self.snap_enabled and shift) else new_rot
            self.update()
        elif self.grid_snap_enabled and self.tool_mode == ToolMode.DRAW:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.text_resize_shape:
                self.shape_selected.emit(self.text_resize_shape)
                self.text_resize_shape = None
                return
            if self.curve_dragging:
                self.curve_dragging = None
            elif self.moving_shapes:
                self.moving_shapes.clear()
                self.move_origins.clear()
            elif self.is_drawing:
                self.is_drawing = False
                self._save_state()
                self.shapes.append(Shape(
                    shape_type=self.current_tool,
                    start_x=self.start_pos.x(),
                    start_y=self.start_pos.y(),
                    end_x=self.current_pos.x(),
                    end_y=self.current_pos.y(),
                    stroke_width=self.stroke_width,
                    stroke_color=self.stroke_color.name(),
                    corner_radius=self.default_corner_radius,
                ))
                self.snap_endpoint = None
                self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.rotating_shape = None

    def keyPressEvent(self, event: QKeyEvent):
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        if ctrl and event.key() == Qt.Key.Key_Z:
            self.redo() if shift else self.undo()
        elif ctrl and event.key() == Qt.Key.Key_Y:
            self.redo()
        elif event.key() == Qt.Key.Key_Escape:
            if self.path_points:
                self.path_points.clear()
                self.update()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.path_points:
                self.path_points.pop()
                self.update()
            else:
                to_delete = [s for s in self.selected_shapes if s in self.shapes]
                if to_delete:
                    self._save_state()
                    for s in to_delete:
                        self.shapes.remove(s)
                    self.selected_shapes.clear()
                    self.update()

    def wheelEvent(self, event: QWheelEvent):
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        delta = event.angleDelta().y() / 120.0
        targets = ([self.rotating_shape] if self.rotating_shape
                   else (self.selected_shapes if self.tool_mode == ToolMode.SELECT else []))
        if targets:
            for target in targets:
                if self.snap_enabled and shift:
                    snapped = self._snap_rotation(target.rotation)
                    target.rotation = snapped + math.copysign(22.5, delta)
                else:
                    target.rotation += delta
            self.update()
        else:
            self._apply_zoom(self.zoom * (1.0 + delta * 0.1))

    def _calculate_angle(self, pos: QPoint) -> float:
        return math.atan2(pos.y() - self.canvas_h / 2,
                          pos.x() - self.canvas_w / 2) * 180 / math.pi

    def _hit_test(self, pos: QPoint) -> Optional[Shape]:
        for shape in reversed(self.shapes):
            if self._point_in_shape(pos, shape):
                return shape
        return None

    def _point_near_segment(self, pos: QPoint, x1, y1, x2, y2, tol) -> bool:
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.sqrt((pos.x() - x1) ** 2 + (pos.y() - y1) ** 2) < tol
        t = ((pos.x() - x1) * dx + (pos.y() - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        px, py = x1 + t * dx, y1 + t * dy
        return math.sqrt((pos.x() - px) ** 2 + (pos.y() - py) ** 2) < tol

    def _point_in_shape(self, pos: QPoint, shape: Shape) -> bool:
        if shape.shape_type == ShapeType.PATH:
            tol = shape.stroke_width + 5
            pts = shape.points
            n = len(pts)
            for i in range(n - 1):
                if self._point_near_segment(pos, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], tol):
                    return True
            if shape.closed and n >= 3:
                if self._point_near_segment(pos, pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], tol):
                    return True
            return False
        if shape.shape_type == ShapeType.TEXT:
            t = 4
            return (shape.start_x - t <= pos.x() <= shape.end_x + t and
                    shape.start_y - t <= pos.y() <= shape.end_y + t)
        t = shape.stroke_width + 5
        return (min(shape.start_x, shape.end_x) - t <= pos.x() <= max(shape.start_x, shape.end_x) + t and
                min(shape.start_y, shape.end_y) - t <= pos.y() <= max(shape.start_y, shape.end_y) + t)

    # --- painting ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.zoom, self.zoom)

        if self.show_background:
            painter.fillRect(0, 0, self.canvas_w, self.canvas_h, self.background_color)
        else:
            self._draw_checkerboard(painter)
        if self.grid_enabled:
            self._draw_grid(painter)
        for shape in self.shapes:
            self._draw_shape(painter, shape,
                             selected=(shape in self.selected_shapes),
                             hover=(shape is self.hover_shape and shape not in self.selected_shapes))
            if shape in self.selected_shapes and shape.shape_type == ShapeType.PATH:
                self._draw_path_curve_handles(painter, shape)
        if self.is_drawing:
            self._draw_shape(painter, Shape(
                shape_type=self.current_tool,
                start_x=self.start_pos.x(), start_y=self.start_pos.y(),
                end_x=self.current_pos.x(), end_y=self.current_pos.y(),
                stroke_width=self.stroke_width,
                stroke_color=self.stroke_color.name(),
            ), preview=True)
        if self.path_points and self.tool_mode == ToolMode.DRAW:
            self._draw_path_preview(painter)
        if self.grid_snap_enabled and self.tool_mode == ToolMode.DRAW and self.current_tool not in (ShapeType.PATH, ShapeType.TEXT):
            snapped = self._snap_to_grid(self.cursor_pos)
            painter.save()
            painter.setPen(QPen(QColor("#0099ff"), 1))
            painter.setBrush(QColor(0, 153, 255, 160))
            r = 4
            painter.drawEllipse(snapped.x() - r, snapped.y() - r, r * 2, r * 2)
            if self.is_drawing:
                painter.setBrush(QColor(0, 200, 100, 200))
                painter.drawEllipse(self.start_pos.x() - r, self.start_pos.y() - r, r * 2, r * 2)
            painter.restore()
        if self.snap_endpoint and self.tool_mode == ToolMode.DRAW:
            painter.save()
            painter.setPen(QPen(QColor("#ff9900"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = 8
            painter.drawEllipse(self.snap_endpoint.x() - r, self.snap_endpoint.y() - r, r * 2, r * 2)
            painter.restore()

    def _draw_path_preview(self, painter: QPainter):
        pen = QPen(self.stroke_color)
        pen.setWidth(max(1, int(self.stroke_width)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        pts = self.path_points
        for i in range(len(pts) - 1):
            painter.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[i + 1][0]), int(pts[i + 1][1]))
        painter.drawLine(int(pts[-1][0]), int(pts[-1][1]), self.current_pos.x(), self.current_pos.y())
        if len(pts) >= 3:
            painter.save()
            painter.setPen(QPen(QColor("#00cc44"), 2))
            painter.setBrush(QColor(0, 204, 68, 100))
            r = CLOSE_THRESHOLD
            painter.drawEllipse(int(pts[0][0]) - r, int(pts[0][1]) - r, r * 2, r * 2)
            painter.restore()
        painter.save()
        painter.setPen(QPen(QColor("#0099ff"), 1))
        painter.setBrush(QColor(0, 153, 255, 200))
        for pt in pts:
            painter.drawEllipse(int(pt[0]) - 4, int(pt[1]) - 4, 8, 8)
        painter.restore()

    def _draw_path_curve_handles(self, painter: QPainter, shape: Shape):
        pts = shape.points
        n = len(pts)
        if n < 2:
            return
        segs = n if shape.closed else n - 1
        painter.save()
        for i in range(segs):
            end_idx = 0 if (shape.closed and i == n - 1) else i + 1
            x1, y1 = pts[i]
            x2, y2 = pts[end_idx]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            c = shape.curves[i] if i < len(shape.curves) else 0.0
            dx, dy_seg = x2 - x1, y2 - y1
            length = math.sqrt(dx * dx + dy_seg * dy_seg)
            if length > 0:
                nx, ny = -dy_seg / length, dx / length
                hx, hy = mx + nx * c, my + ny * c
            else:
                hx, hy = mx, my
            painter.setPen(QPen(QColor(255, 153, 0, 120), 1))
            painter.drawLine(int(mx), int(my), int(hx), int(hy))
            painter.setPen(QPen(QColor("#ff9900"), 1))
            painter.setBrush(QColor("#ff9900"))
            r = 5
            diamond = QPolygonF([
                QPointF(hx, hy - r), QPointF(hx + r, hy),
                QPointF(hx, hy + r), QPointF(hx - r, hy),
            ])
            painter.drawPolygon(diamond)
        painter.restore()

    def _draw_checkerboard(self, painter: QPainter):
        size = 16
        for row in range(0, self.canvas_h, size):
            for col in range(0, self.canvas_w, size):
                c = QColor("#cccccc") if (row // size + col // size) % 2 == 0 else QColor("#ffffff")
                painter.fillRect(col, row, size, size, c)

    def _draw_grid(self, painter: QPainter):
        bg = self.background_color
        luma = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
        painter.setPen(QPen(QColor(0, 0, 0, 30) if luma > 128 else QColor(255, 255, 255, 30), 0.5))
        for x in range(0, self.canvas_w, 20):
            painter.drawLine(x, 0, x, self.canvas_h)
        for y in range(0, self.canvas_h, 20):
            painter.drawLine(0, y, self.canvas_w, y)

    def _draw_shape(self, painter: QPainter, shape: Shape,
                    preview: bool = False, selected: bool = False, hover: bool = False):
        pen = QPen(QColor(shape.stroke_color))
        pen.setWidth(max(1, int(shape.stroke_width)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if preview:
            pen.setColor(self.stroke_color)
        if hover:
            pen.setColor(QColor("#88bbff"))
            pen.setWidth(max(1, int(shape.stroke_width) + 1))
        if selected:
            pen.setColor(QColor("#ff6b6b"))
        painter.setPen(pen)

        if shape.shape_type == ShapeType.PATH:
            self._draw_path(painter, shape)
            return

        cx = (shape.start_x + shape.end_x) / 2
        cy = (shape.start_y + shape.end_y) / 2
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(shape.rotation)
        painter.translate(-cx, -cy)

        if shape.shape_type == ShapeType.TEXT:
            self._draw_text_shape(painter, shape, pen, selected, hover)
        elif shape.shape_type == ShapeType.LINE:
            painter.drawLine(int(shape.start_x), int(shape.start_y),
                             int(shape.end_x), int(shape.end_y))
        elif shape.shape_type == ShapeType.CIRCLE:
            r = math.sqrt((shape.end_x - shape.start_x) ** 2 +
                          (shape.end_y - shape.start_y) ** 2) / 2
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        elif shape.shape_type == ShapeType.SQUARE:
            x = int(min(shape.start_x, shape.end_x))
            y = int(min(shape.start_y, shape.end_y))
            w = int(abs(shape.end_x - shape.start_x))
            h = int(abs(shape.end_y - shape.start_y))
            if shape.corner_radius > 0:
                painter.drawRoundedRect(x, y, w, h, shape.corner_radius, shape.corner_radius)
            else:
                painter.drawRect(x, y, w, h)
        elif shape.shape_type == ShapeType.TRIANGLE:
            self._draw_triangle(painter, shape)

        painter.restore()

    def _draw_path(self, painter: QPainter, shape: Shape):
        pts = shape.points
        n = len(pts)
        if n < 2:
            return
        curves = shape.curves
        path = QPainterPath()
        path.moveTo(pts[0][0], pts[0][1])
        segs = n if shape.closed else n - 1
        for i in range(segs):
            end_idx = 0 if (shape.closed and i == n - 1) else i + 1
            x1, y1 = pts[i]
            x2, y2 = pts[end_idx]
            c = curves[i] if i < len(curves) else 0.0
            if c != 0.0:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy_seg = x2 - x1, y2 - y1
                length = math.sqrt(dx * dx + dy_seg * dy_seg)
                if length > 0:
                    nx, ny = -dy_seg / length, dx / length
                    path.quadTo(mx + nx * c, my + ny * c, x2, y2)
                else:
                    path.lineTo(x2, y2)
            else:
                path.lineTo(x2, y2)
        if shape.closed:
            path.closeSubpath()
        painter.drawPath(path)

    def _draw_triangle(self, painter: QPainter, shape: Shape):
        x1, y1, x2, y2 = shape.start_x, shape.start_y, shape.end_x, shape.end_y
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        painter.drawPolyline(QPolygonF([
            QPointF(x1, y1),
            QPointF(x2, y2),
            QPointF(mx + (-dy / 2), my + (dx / 2)),
            QPointF(x1, y1),
        ]))

    def _draw_text_shape(self, painter: QPainter, shape: Shape, pen: QPen,
                         selected: bool, hover: bool):
        font = QFont(shape.font_family, shape.font_size)
        painter.setFont(font)
        fm = painter.fontMetrics()
        w = int(shape.end_x - shape.start_x)
        h = int(shape.end_y - shape.start_y)
        if selected:
            painter.setPen(QPen(QColor("#ff6b6b"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(int(shape.start_x) - 2, int(shape.start_y) - 2, w + 4, h + 4)
            # Resize handle at bottom-right
            hx, hy = int(shape.end_x), int(shape.end_y)
            painter.setPen(QPen(QColor("#ff6b6b"), 1))
            painter.setBrush(QColor("#ffffff"))
            painter.drawRect(hx - 5, hy - 5, 10, 10)
        elif hover:
            painter.setPen(QPen(QColor("#88bbff"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(int(shape.start_x) - 2, int(shape.start_y) - 2, w + 4, h + 4)
        painter.setPen(pen)
        painter.drawText(int(shape.start_x), int(shape.start_y + fm.ascent()), shape.text)

    def clear_all(self):
        self._save_state()
        self.shapes.clear()
        self.selected_shapes.clear()
        self.path_points.clear()
        self.update()

    # --- export ---

    def get_svg_export(self, palette: IconPalette, include_background: bool) -> str:
        w, h = self.canvas_w, self.canvas_h
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">',
        ]
        if include_background:
            lines.append(f'<rect width="{w}" height="{h}" fill="{palette.background}"/>')
        for shape in self.shapes:
            lines.append(self._shape_to_svg(shape))
        lines.append('</svg>')
        return '\n'.join(lines)

    def _shape_to_svg(self, shape: Shape) -> str:
        sw = max(1, int(shape.stroke_width))
        color = shape.stroke_color
        if shape.shape_type == ShapeType.PATH:
            return self._path_to_svg(shape, sw, color)
        if shape.shape_type == ShapeType.TEXT:
            return self._text_to_svg(shape, color)
        cx = (shape.start_x + shape.end_x) / 2
        cy = (shape.start_y + shape.end_y) / 2
        tr = f'transform="translate({cx} {cy}) rotate({shape.rotation}) translate({-cx} {-cy})"'
        if shape.shape_type == ShapeType.LINE:
            return (f'<line x1="{int(shape.start_x)}" y1="{int(shape.start_y)}" '
                    f'x2="{int(shape.end_x)}" y2="{int(shape.end_y)}" '
                    f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" {tr}/>')
        elif shape.shape_type == ShapeType.CIRCLE:
            r = math.sqrt((shape.end_x - shape.start_x) ** 2 +
                          (shape.end_y - shape.start_y) ** 2) / 2
            return (f'<circle cx="{int(cx)}" cy="{int(cy)}" r="{r:.2f}" '
                    f'fill="none" stroke="{color}" stroke-width="{sw}" {tr}/>')
        elif shape.shape_type == ShapeType.SQUARE:
            x, y = min(shape.start_x, shape.end_x), min(shape.start_y, shape.end_y)
            rw, rh = abs(shape.end_x - shape.start_x), abs(shape.end_y - shape.start_y)
            cr = shape.corner_radius
            if cr > 0:
                return (f'<rect x="{int(x)}" y="{int(y)}" width="{int(rw)}" height="{int(rh)}" '
                        f'rx="{cr:.1f}" ry="{cr:.1f}" fill="none" stroke="{color}" stroke-width="{sw}" {tr}/>')
            return (f'<rect x="{int(x)}" y="{int(y)}" width="{int(rw)}" height="{int(rh)}" '
                    f'fill="none" stroke="{color}" stroke-width="{sw}" {tr}/>')
        elif shape.shape_type == ShapeType.TRIANGLE:
            x1, y1, x2, y2 = shape.start_x, shape.start_y, shape.end_x, shape.end_y
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            pts = (f"{int(x1)},{int(y1)} {int(x2)},{int(y2)} "
                   f"{int(mx + (-dy / 2))},{int(my + (dx / 2))}")
            return (f'<polygon points="{pts}" fill="none" stroke="{color}" '
                    f'stroke-width="{sw}" {tr}/>')
        return ""

    def _path_to_svg(self, shape: Shape, sw: int, color: str) -> str:
        pts = shape.points
        n = len(pts)
        if n < 2:
            return ""
        curves = shape.curves
        d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
        segs = n if shape.closed else n - 1
        for i in range(segs):
            end_idx = 0 if (shape.closed and i == n - 1) else i + 1
            x1, y1 = pts[i]
            x2, y2 = pts[end_idx]
            c = curves[i] if i < len(curves) else 0.0
            if c != 0.0:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy_seg = x2 - x1, y2 - y1
                length = math.sqrt(dx * dx + dy_seg * dy_seg)
                if length > 0:
                    nx, ny = -dy_seg / length, dx / length
                    cpx, cpy = mx + nx * c, my + ny * c
                    d += f" Q {cpx:.1f} {cpy:.1f} {x2:.1f} {y2:.1f}"
                else:
                    d += f" L {x2:.1f} {y2:.1f}"
            else:
                d += f" L {x2:.1f} {y2:.1f}"
        if shape.closed:
            d += " Z"
        return (f'<path d="{d}" fill="none" stroke="{color}" '
                f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')

    def _text_to_svg(self, shape: Shape, color: str) -> str:
        cx = (shape.start_x + shape.end_x) / 2
        cy = (shape.start_y + shape.end_y) / 2
        tr = (f'transform="translate({cx:.1f},{cy:.1f}) '
              f'rotate({shape.rotation:.2f}) '
              f'translate({-cx:.1f},{-cy:.1f})"')
        fm = QFontMetrics(QFont(shape.font_family, shape.font_size))
        text_y = int(shape.start_y + fm.ascent())
        safe_text = (shape.text.replace('&', '&amp;')
                     .replace('<', '&lt;').replace('>', '&gt;'))
        return (f'<text x="{int(shape.start_x)}" y="{text_y}" '
                f'font-family="{shape.font_family}" font-size="{shape.font_size}pt" '
                f'fill="{color}" {tr}>{safe_text}</text>')

    def render_to_pixmap(self, pixel_size: int) -> QPixmap:
        """Render the canvas to a square QPixmap at the given pixel size."""
        pm = QPixmap(self.canvas_w, self.canvas_h)
        if self.show_background:
            pm.fill(self.background_color)
        else:
            pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for shape in self.shapes:
            self._draw_shape(painter, shape)
        painter.end()
        return pm.scaled(
            pixel_size, pixel_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
