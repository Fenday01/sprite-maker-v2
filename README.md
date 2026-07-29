# Sprite Maker V2

A compact, canvas-first pixel editor for creating monochrome sprites and
exporting them as packed C bitmap data.

## Features

- Responsive resizable pixel grid
- Square, circular, checkerboard, fill, and selection tools
- Adjustable brush sizes with live cursor previews
- Left-click drawing and right-click erasing
- Eight-way flood fill, including diagonal connections
- Mouse-wheel zoom centred on the pointer
- Undo and redo history
- Copy a rectangular selection and paste it as a reusable brush
- Live C output with one-click clipboard copying
- Correct row-padded byte sizing for sprite widths not divisible by eight

## Running

On Windows, double-click `run_sprite_maker.bat`.

Alternatively, run:

```powershell
python main.py
```

Sprite Maker uses Python's standard Tkinter library and has no third-party
package dependencies.

## Controls

| Action | Control |
| --- | --- |
| Draw | Left-click or left-drag |
| Erase | Right-click or right-drag |
| Zoom | Mouse wheel |
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Y` |
| Copy selection | `Ctrl+C` |
| Cut selection | `Ctrl+X` |
| Delete selected pixels | `Delete` |
| Use copied selection as a brush | `Ctrl+V` |
| Reset the active selection | `Escape` |
| Increase brush size | `Ctrl+Shift+>` |
| Decrease brush size | `Ctrl+Shift+<` |
| Copy generated C output | `Ctrl+Shift+C` |
