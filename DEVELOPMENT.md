# DIMP - Development Guide

This guide covers extending the application with new features and customizations.

---

## Code Architecture Overview

### Main Classes

```
MainWindow (QMainWindow)
├── Canvas (QWidget) - Drawing surface and shape rendering
├── Shape (dataclass) - Individual shape representation
├── ColorScheme (dataclass) - Theme definition
└── ShapeType (Enum) - Shape type constants
```

### Key Design Patterns

1. **Shape-based architecture**: All drawings are stored as `Shape` objects
2. **Theme-aware rendering**: Colors chosen at export time, not draw time
3. **State preservation**: Projects saved as JSON for portability
4. **Event-driven UI**: PyQt6 signals/slots for user interactions

---

## Adding New Shape Types

### Step 1: Add to ShapeType Enum

```python
class ShapeType(Enum):
    LINE = "line"
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"
    POLYGON = "polygon"  # NEW
    STAR = "star"        # NEW
```

### Step 2: Add Drawing Logic

In `Canvas._draw_shape()`:

```python
elif shape.shape_type == ShapeType.POLYGON:
    self._draw_polygon(painter, shape)
elif shape.shape_type == ShapeType.STAR:
    self._draw_star(painter, shape)
```

Then implement the drawing methods:

```python
def _draw_polygon(self, painter: QPainter, shape: Shape):
    """Draw an N-sided polygon"""
    # Calculate vertices based on start/end points
    from PyQt6.QtGui import QPolygonF, QPointF
    
    cx = (shape.start_x + shape.end_x) / 2
    cy = (shape.start_y + shape.end_y) / 2
    radius = math.sqrt((shape.end_x - shape.start_x) ** 2 +
                      (shape.end_y - shape.start_y) ** 2) / 2
    
    sides = 6  # Hexagon, customize as needed
    points = []
    for i in range(sides):
        angle = 2 * math.pi * i / sides
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append(QPointF(x, y))
    
    polygon = QPolygonF(points)
    painter.drawPolygon(polygon)
```

### Step 3: Add SVG Export

In `Canvas._shape_to_svg()`:

```python
elif shape.shape_type == ShapeType.POLYGON:
    # Generate polygon SVG points
    cx = (shape.start_x + shape.end_x) / 2
    cy = (shape.start_y + shape.end_y) / 2
    radius = math.sqrt((shape.end_x - shape.start_x) ** 2 +
                      (shape.end_y - shape.start_y) ** 2) / 2
    
    sides = 6
    points = []
    for i in range(sides):
        angle = 2 * math.pi * i / sides
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append(f"{int(x)},{int(y)}")
    
    points_str = " ".join(points)
    return (f'<polygon points="{points_str}" fill="none" '
           f'stroke="{color}" stroke-width="{stroke_width}" {transform}/>')
```

### Step 4: Add UI Button

In `MainWindow._setup_toolbar()`:

```python
polygon_btn = QPushButton("Polygon")
polygon_btn.clicked.connect(lambda: self.canvas.set_tool(ShapeType.POLYGON))
toolbar.addWidget(polygon_btn)
```

---

## Adding New Color Themes

### Method 1: Hard-coded Theme

Add to the `self.themes` list in `MainWindow.__init__()`:

```python
ColorScheme(
    name="Sunset Orange",
    primary_light="#ff6600",      # Orange for light backgrounds
    secondary_light="#ffaa33",     # Lighter orange
    primary_dark="#ffdd99",        # Light orange for dark backgrounds
    secondary_dark="#ffeecc",      # Very light orange
    background_light="#ffffff",    # White background
    background_dark="#1a1a1a"      # Dark background
)
```

**Color Selection Tips:**
- Light mode: Use darker, saturated colors on white
- Dark mode: Use lighter, less saturated versions
- Secondary: Usually lighter or more saturated variant
- Test both light and dark modes before adding

### Method 2: Load from File

Create `themes.json`:

```json
{
  "themes": [
    {
      "name": "Custom Theme",
      "primary_light": "#1a1a1a",
      "secondary_light": "#4d4d4d",
      "primary_dark": "#e6e6e6",
      "secondary_dark": "#b3b3b3"
    }
  ]
}
```

Add to `MainWindow.__init__()`:

```python
import json

with open('themes.json') as f:
    themes_data = json.load(f)
    for theme_data in themes_data['themes']:
        self.themes.append(ColorScheme(**theme_data))
```

---

## Modifying Canvas Behavior

### Change Grid Size

In `Canvas._draw_grid()`:

```python
grid_size = 10  # Was 20, now finer grid
```

### Change Default Stroke Width

In `MainWindow._setup_toolbar()`:

```python
width_spin.setValue(3)  # Was 2
width_spin.setMaximum(50)  # Increase max
```

### Add Stroke Width Presets

```python
class StrokePreset(Enum):
    THIN = 1
    NORMAL = 2
    MEDIUM = 3
    THICK = 5
    EXTRA_THICK = 8
```

---

## Adding Undo/Redo Support

### 1. Create UndoStack

```python
class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.shapes = []
        self.undo_stack = []
        self.redo_stack = []
```

### 2. Capture State Before Changes

```python
def _push_undo(self):
    """Push current state to undo stack"""
    import copy
    self.undo_stack.append(copy.deepcopy(self.shapes))
    self.redo_stack.clear()  # Clear redo when new action taken

def mouseReleaseEvent(self, event: QMouseEvent):
    if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
        self._push_undo()  # Save state BEFORE creating shape
        self.is_drawing = False
        # ... rest of code
```

### 3. Implement Undo/Redo Methods

```python
def undo(self):
    if self.undo_stack:
        self.redo_stack.append(self.shapes)
        self.shapes = self.undo_stack.pop()
        self.update()

def redo(self):
    if self.redo_stack:
        self.undo_stack.append(self.shapes)
        self.shapes = self.redo_stack.pop()
        self.update()
```

### 4. Add Keyboard Shortcuts

```python
def keyPressEvent(self, event: QKeyEvent):
    if event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
        self.undo()
    elif event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
        self.redo()
```

---

## Adding Layer Support

### 1. Create Layer Class

```python
@dataclass
class Layer:
    name: str
    shapes: List[Shape] = field(default_factory=list)
    visible: bool = True
    opacity: float = 1.0
    id: str = field(default_factory=lambda: str(hash(id(__import__('time').time()))))
```

### 2. Modify Canvas

```python
class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.layers: List[Layer] = [Layer(name="Default")]
        self.active_layer = self.layers[0]
```

### 3. Update Shape Creation

```python
def mouseReleaseEvent(self, event: QMouseEvent):
    if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
        self.is_drawing = False
        shape = Shape(...)
        self.active_layer.shapes.append(shape)  # Add to active layer
        self.update()
```

### 4. Update Rendering

```python
def paintEvent(self, event):
    painter = QPainter(self)
    # ... background and grid ...
    
    # Draw all visible layers
    for layer in self.layers:
        if not layer.visible:
            continue
        for shape in layer.shapes:
            self._draw_shape(painter, shape)
```

---

## Improving Shape Rotation

### Current Implementation Issues
- Rotation center always at shape midpoint
- No visual rotation indicator

### Enhanced Version with Rotation Handle

```python
def _draw_shape(self, painter: QPainter, shape: Shape, 
                selected: bool = False):
    """Enhanced with rotation handle"""
    # ... existing drawing code ...
    
    if selected:
        # Draw rotation handle
        cx = (shape.start_x + shape.end_x) / 2
        cy = (shape.start_y + shape.end_y) / 2
        
        handle_distance = 80
        handle_x = cx + handle_distance * math.cos(math.radians(shape.rotation))
        handle_y = cy + handle_distance * math.sin(math.radians(shape.rotation))
        
        # Draw line from center to handle
        painter.drawLine(int(cx), int(cy), int(handle_x), int(handle_y))
        
        # Draw handle circle
        painter.drawEllipse(int(handle_x) - 4, int(handle_y) - 4, 8, 8)
```

---

## Performance Optimization

### For Large Numbers of Shapes

```python
class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.use_cache = True
        self.cache_pixmap = None
        self.cache_valid = False
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        if self.use_cache and self.cache_valid:
            painter.drawPixmap(0, 0, self.cache_pixmap)
            self._draw_preview(painter)
        else:
            self._render_full(painter)
            if self.use_cache:
                self.cache_pixmap = QPixmap(self.size())
                cache_painter = QPainter(self.cache_pixmap)
                self._render_full(cache_painter)
                self.cache_valid = True
    
    def invalidate_cache(self):
        self.cache_valid = False
```

---

## Testing New Features

### Unit Test Example

```python
def test_shape_rotation():
    shape = Shape(
        shape_type=ShapeType.LINE,
        start_x=0, start_y=0,
        end_x=100, end_y=0
    )
    
    shape.rotation = 90
    assert shape.rotation == 90
    
    shape.rotation = 360 + 45
    # Normalize if needed
    assert shape.rotation == 405

def test_svg_export():
    canvas = Canvas()
    canvas.shapes.append(Shape(
        shape_type=ShapeType.CIRCLE,
        start_x=50, start_y=50,
        end_x=100, end_y=100
    ))
    
    theme = ColorScheme(
        name="Test",
        primary_light="#000000",
        secondary_light="#333333",
        primary_dark="#ffffff",
        secondary_dark="#cccccc"
    )
    
    svg = canvas.get_svg_export(theme, False)
    assert '<circle' in svg
    assert '#000000' in svg
```

---

## Debugging Tips

### Print Shape State

```python
def _debug_shapes(self):
    for i, shape in enumerate(self.shapes):
        print(f"Shape {i}: {shape.shape_type.value} "
              f"@ ({shape.start_x}, {shape.start_y}) "
              f"-> ({shape.end_x}, {shape.end_y}) "
              f"rot={shape.rotation}°")
```

### Visualize Bounding Boxes

```python
def _draw_debug_bounds(self, painter: QPainter):
    """Visualize shape bounding boxes"""
    for shape in self.shapes:
        x1 = min(shape.start_x, shape.end_x)
        y1 = min(shape.start_y, shape.end_y)
        x2 = max(shape.start_x, shape.end_x)
        y2 = max(shape.start_y, shape.end_y)
        painter.drawRect(int(x1), int(y1), int(x2-x1), int(y2-y1))
```

---

## Common Gotchas

1. **Qt Coordinate System**: Origin (0,0) is top-left, Y increases downward
2. **Painter State**: Always `painter.save()` before transforms, `painter.restore()` after
3. **Integer Conversion**: Qt drawing functions need integers, use `int()` for coordinates
4. **SVG vs Qt Angles**: Both use same convention (0° = right, increases clockwise)
5. **Color Spaces**: Ensure hex colors are valid format (#RRGGBB)

---

## Resources

- **PyQt6 Documentation**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **SVG Spec**: https://www.w3.org/TR/SVG2/
- **Python Dataclasses**: https://docs.python.org/3/library/dataclasses.html
- **Qt Painter**: https://doc.qt.io/qt-6/qpainter.html

---

Happy coding! 🚀
