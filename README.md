# DIMP - Minimalist Icon Design Tool

A professional desktop application for creating clean, stroke-based minimalist icons with rotation, theming, and SVG export capabilities.

## Features

### Core Drawing Tools
- **Line Tool**: Draw straight lines with customizable stroke width
- **Circle Tool**: Create circular shapes
- **Square Tool**: Draw rectangular/square shapes
- **Triangle Tool**: Create triangular shapes
- All shapes support rotation and stroke width customization

### Rotation System
- **Right-click + Drag**: Intuitive rotation of selected shapes
- **Mouse Wheel**: Fine-tuned rotation adjustment (1° increments)
- Real-time visual feedback during rotation

### Theming System
Built-in color themes with light/dark mode support:
- **Classic Black**: Traditional black and grayscale
- **Ocean Blue**: Cool blue tones
- **Sunset Pink**: Warm pink hues
- **Forest Green**: Natural green palette
- **Amber Glow**: Warm amber and gold
- **Purple Iris**: Purple and violet
- **Mint Fresh**: Mint and cyan tones

Each theme features:
- Primary and secondary colors
- Automatic light/dark mode variants
- Theme-aware background colors

### Export & Save
- **SVG Export**: Export your icon in SVG format with theme colors applied
- **Project Save/Load**: Save projects as `.iconproj` files to preserve work
- **Format Support**: Easy sharing and further editing in other tools

### UI Features
- **Grid Background**: Optional snap-to-grid visual guide
- **Dark Mode**: Toggle between light and dark interfaces
- **Real-time Preview**: See shapes as you draw
- **Shape Selection**: Click shapes to select and modify
- **Delete Function**: Press Delete or Backspace to remove selected shapes

## Installation

### Requirements
- Python 3.8 or higher
- pip (Python package installer)

### Setup Steps

1. **Clone or download the project**
   ```bash
   cd icon-creator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python dimp.py
   ```

Or make it executable on macOS/Linux:
   ```bash
   chmod +x dip.py
   ./dimp.py
   ```

## Usage Guide

### Drawing Shapes

1. **Select a tool** from the toolbar (Line, Circle, Square, or Triangle)
2. **Adjust stroke width** using the spinbox (1-20 pixels)
3. **Pick a color** using the color picker button
4. **Left-click and drag** on the canvas to create shapes
5. The preview shows in real-time as you draw

### Rotating Shapes

1. **Right-click on a shape** to select it for rotation
2. **Drag** to rotate the shape around its center
3. **Use mouse wheel** while rotating for fine 1° adjustments
4. **Release** to confirm rotation

### Working with Themes

1. **Select a theme** from the Theme dropdown in the toolbar
2. **Toggle Dark Mode** to switch between light and dark variants
3. SVG export automatically applies the selected theme colors

### Saving Your Work

**Save Project (Preserves Editability)**:
- Click "Save Project"
- Choose location and filename (`.iconproj` format)
- Reopen anytime with "Load Project"
- Preserves all shapes, rotation, and theme settings

**Export as SVG (Final Output)**:
- Click "Export SVG"
- Choose location and filename (`.svg` format)
- Use in web projects, icon libraries, or other tools
- Colors automatically applied from current theme and mode

### Tips & Tricks

- **Multi-layer Creation**: Create overlapping shapes to build complex icons
- **Consistency**: Use the same stroke width for a cohesive look
- **Theme Testing**: Export in different themes to find the best fit
- **Light/Dark Pairs**: Create separate exports for light and dark modes

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Delete selected shape | Delete or Backspace |
| Clear all shapes | Use "Clear All" button |

## Project File Format

Saved projects (`.iconproj`) use JSON format for transparency and portability:

```json
{
  "shapes": [
    {
      "type": "line",
      "start_x": 100,
      "start_y": 100,
      "end_x": 200,
      "end_y": 200,
      "rotation": 0.0,
      "stroke_width": 2.0,
      "stroke_color": "#000000",
      "id": "shape_001"
    }
  ],
  "theme": "Classic Black",
  "dark_mode": false
}
```

## SVG Export Features

- Exported SVG includes:
  - Full canvas dimensions
  - Theme-appropriate background color
  - Stroke colors from selected theme
  - Rotation transforms applied to shapes
  - Round line caps and joins for quality output
  
- Colors alternate between primary and secondary theme colors
- Output is compatible with all modern SVG viewers and editors

## Architecture

### Core Components

**Canvas Widget** (`Canvas` class):
- Custom Qt drawing surface
- Mouse tracking and event handling
- Shape rendering with rotation
- SVG export logic

**Shape Data** (`Shape` dataclass):
- Immutable shape definition
- Serialization support (to/from dict)
- Complete state preservation

**Color Themes** (`ColorScheme` dataclass):
- Light and dark mode color pairs
- Named theme system
- Easy to extend with new themes

**Main Window** (`MainWindow` class):
- UI orchestration
- Tool bar and properties panel
- File I/O operations
- Theme management

## Extending the Application

### Adding New Shapes

1. Add shape type to `ShapeType` enum
2. Implement drawing logic in `Canvas._draw_shape()`
3. Add SVG conversion in `Canvas._shape_to_svg()`
4. Add toolbar button in `MainWindow._setup_toolbar()`

### Adding Themes

```python
ColorScheme(
    name="Your Theme",
    primary_light="#xxxxx",
    secondary_light="#xxxxx",
    primary_dark="#xxxxx",
    secondary_dark="#xxxxx"
)
```

Add to the `self.themes` list in `MainWindow.__init__()`.

### Customization

- Modify `Canvas.grid_enabled` default
- Adjust stroke width limits in spinbox setup
- Change default canvas colors
- Modify canvas size or aspect ratio

## Known Limitations & Future Enhancements

### Current
- Shapes don't snap to grid (visual only)
- No undo/redo system
- No layer support
- Limited shape types

### Potential Enhancements
- Undo/redo history
- Layer system
- Shape grouping
- Bezier curve tool
- Text support
- Grid snapping
- Export to PNG/PDF
- Shape duplication and mirroring

## Troubleshooting

**Application won't start**:
- Ensure PyQt6 is installed: `pip install PyQt6`
- Check Python version is 3.8+

**Colors look wrong after export**:
- Verify theme is selected correctly
- Check dark mode matches your export intent
- SVG colors depend on viewer color profile

**Performance issues with many shapes**:
- Reduce number of shapes
- Disable grid if not needed
- Simplify stroke widths

## License

MIT License - Feel free to modify and distribute

## Contributing

Suggestions and improvements welcome! Consider:
- New shape types
- UI enhancements
- Performance optimizations
- Additional themes

---

**Happy Icon Creating!** 🎨
