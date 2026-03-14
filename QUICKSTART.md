# DIMP - Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run the App
```bash
python dimp.py
```

That's it! The application window should open.

---

## First Icon (2 Minutes)

1. **Canvas appears** - you'll see a white canvas with a grid
2. **Click "Line"** tool in the toolbar
3. **Left-click and drag** on canvas diagonally to draw a line
4. **Click "Circle"** tool
5. **Draw a circle** by dragging on the canvas
6. **Right-click on your line**, drag to rotate it
7. **Adjust stroke width** - try 3, 4, 5
8. **Change the color** - click the color button and pick a new color

---

## Save Your Work

**To save editable project**:
- Click "Save Project"
- Name it `my-icon.iconproj`
- Load it later with "Load Project"

**To export as SVG** (for web/design tools):
- Click "Export SVG"
- Choose a theme and click export
- SVG file is ready for web use

---

## Key Controls

| Action | How |
|--------|-----|
| Draw shape | Left-click + drag |
| Rotate shape | Right-click on shape + drag |
| Fine-tune rotation | Use mouse wheel while rotating |
| Delete shape | Select it, press Delete |
| Change theme | Select from dropdown |
| Toggle dark mode | Click "Dark Mode" button |

---

## Understanding Themes

Each theme has a **primary** and **secondary color** that adapt:

- **Light Mode**: Colors designed for white backgrounds
- **Dark Mode**: Same colors adapted for dark backgrounds

When you export SVG:
1. Select your theme
2. Toggle light/dark mode
3. Click "Export SVG"
4. Colors automatically apply

**Example**: Ocean Blue theme
- Light mode: Deep blue icon on white
- Dark mode: Bright cyan icon on dark grey

---

## Common Tasks

### Create a minimalist icon set
1. Design one icon in light mode
2. Export as `icon-light.svg`
3. Toggle dark mode
4. Export as `icon-dark.svg`
5. Use both in your web app

### Test different color schemes
1. Draw your icon
2. Try each theme and dark mode combination
3. Export SVGs to compare
4. Pick your favorite look

### Make consistent icons
- Always use same stroke width (e.g., 2 or 3)
- Stick with one or two themes
- Use same shapes (circles, lines, etc.)
- Rotate shapes 45° or 90° for variety

---

## What's Included

- **dimp.py** - Main application
- **requirements.txt** - Dependencies
- **README.md** - Full documentation

---

## Next Steps

Explore these features:
- ✅ All 4 shape types (Line, Circle, Square, Triangle)
- ✅ Rotation with drag and wheel
- ✅ 7 built-in color themes
- ✅ Light/dark mode variants
- ✅ SVG export with theme colors
- ✅ Save/load projects

**Start creating!** 🎨

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'PyQt6'"**
```bash
pip install PyQt6
```

**App won't start**
- Check Python version: `python --version` (need 3.8+)
- Reinstall: `pip install --upgrade PyQt6`

**Colors not exporting right**
- Make sure to select a theme before exporting
- Toggle dark mode to see both variants
- SVG preview in your browser might show different colors (check viewer settings)

---

Enjoy creating beautiful minimalist icons! 🖌️
