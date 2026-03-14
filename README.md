# DIMP

A small desktop app for drawing minimalist, stroke-based icons. Pick a shape, set a stroke width, pick a color — export as SVG.

Built with Python + PyQt6.

---

## Why

I kept reaching for Figma or Illustrator just to make a simple icon. DIMP strips that down to the essentials: shape primitives, a rotation system, a handful of themes, and clean SVG output.

## Getting Started

```bash
pip install -r requirements.txt
python dimp.py
```

Requires Python 3.8+.

## How it works

Select a tool from the toolbar (line, circle, square, or triangle), then click and drag on the canvas. Right-click and drag a shape to rotate it. Mouse wheel adjusts rotation in 1° increments.

When you're done, export as SVG or save as `.iconproj` to come back to it later.

## Themes

There are a few built-in color themes, each with light and dark variants. Swap themes at any time — the SVG export picks up whatever you've got selected.

## Shortcuts

| Action | Key |
|--------|-----|
| Delete selected shape | `Delete` / `Backspace` |
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Y` / `Ctrl+Shift+Z` |
| Save project | `Ctrl+S` |
| Load project | `Ctrl+O` |
| Show/hide background | `Alt+B` |
| Toggle snap on rotate | `Alt+S` |
| Toggle snap to grid | `Alt+G` |
| Constrain line angle (22.5° steps) | Hold `Shift` while drawing |
| Snap rotation (22.5° steps) | Hold `Shift` while rotating |
| Cancel path in progress | `Escape` |
| Remove last path point | `Delete` / `Backspace` (while drawing path) |
| Close path | Click the first point |
| Finish open path | Right-click or double-click |
| Zoom in/out | Scroll wheel (on canvas) |

## Saving

- **Save Project** → keeps everything editable (shapes, rotation, theme)
- **Export SVG** → flat export ready for use

## Known issues / rough edges

- No layers

## License

MIT
