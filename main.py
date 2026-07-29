import math
import re
import tkinter as tk
from tkinter import ttk


class PixelArtApp:
    MIN_GRID_SIZE = 1
    MAX_GRID_SIZE = 128
    MAX_BRUSH_SIZE = 16

    BG = "#11151c"
    SURFACE = "#1a2029"
    SURFACE_RAISED = "#232b36"
    BORDER = "#34404f"
    TEXT = "#eef3f8"
    MUTED = "#9aa8b7"
    ACCENT = "#42c9a5"
    ACCENT_ACTIVE = "#63d9ba"
    CANVAS_BG = "#0b0e13"
    EMPTY_PIXEL = "#f3f6f8"
    FILLED_PIXEL = "#14181e"
    GRID_LINE = "#9ba7b2"
    PREVIEW_DRAW = "#20b98f"
    PREVIEW_ERASE = "#ef6c75"

    def __init__(self, root):
        self.root = root
        self.root.title("Sprite Maker")
        self.root.geometry("1180x720")
        self.root.minsize(820, 520)
        self.root.configure(bg=self.BG)

        self.grid_width = 16
        self.grid_height = 8
        self.pixels = self._blank_pixels(self.grid_width, self.grid_height)

        self.width_var = tk.StringVar(value=str(self.grid_width))
        self.height_var = tk.StringVar(value=str(self.grid_height))
        self.brush_size_var = tk.IntVar(value=1)
        self.brush_shape_var = tk.StringVar(value="Square")
        self.sprite_name_var = tk.StringVar(value="sprite")
        self.grid_summary_var = tk.StringVar()
        self.status_var = tk.StringVar(
            value="Left-drag to draw  |  Right-drag to erase"
        )

        self.cell_size = 20
        self.base_cell_size = 20
        self.zoom_level = 1.0
        self.view_center_x = self.grid_width / 2
        self.view_center_y = self.grid_height / 2
        self.grid_left = 0
        self.grid_top = 0
        self.pixel_items = {}
        self.tool_buttons = {}
        self.undo_stack = []
        self.redo_stack = []
        self.pending_history_state = None
        self.stroke_changed = False
        self.selection_start = None
        self.selection_bounds = None
        self.clipboard_pixels = None
        self.render_job = None
        self.output_job = None
        self.stroke_value = None
        self.last_stroke_cell = None
        self.hover_cell = None

        self._configure_styles()
        self._build_interface()
        self._bind_events()
        self._update_grid_summary()

        self.sprite_name_var.trace_add("write", self._schedule_output_update)
        self.brush_size_var.trace_add("write", self._on_brush_changed)
        self.brush_shape_var.trace_add("write", self._on_brush_changed)

        self.root.after_idle(self._initial_layout)

    @staticmethod
    def _blank_pixels(width, height):
        return [[0 for _ in range(width)] for _ in range(height)]

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            ".",
            background=self.SURFACE,
            foreground=self.TEXT,
            fieldbackground=self.SURFACE_RAISED,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            font=("Segoe UI", 10),
        )
        style.configure("TFrame", background=self.SURFACE)
        style.configure(
            "TLabel",
            background=self.SURFACE,
            foreground=self.TEXT,
        )
        style.configure(
            "Muted.TLabel",
            background=self.SURFACE,
            foreground=self.MUTED,
            font=("Segoe UI Semibold", 8),
        )
        style.configure(
            "Status.TLabel",
            background=self.BG,
            foreground=self.MUTED,
            padding=(12, 7),
        )
        style.configure(
            "TButton",
            background=self.SURFACE_RAISED,
            foreground=self.TEXT,
            borderwidth=1,
            padding=(11, 7),
        )
        style.map(
            "TButton",
            background=[
                ("active", self.BORDER),
                ("pressed", self.BG),
            ],
        )
        style.configure(
            "Accent.TButton",
            background=self.ACCENT,
            foreground="#07130f",
            borderwidth=0,
            padding=(13, 7),
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Accent.TButton",
            background=[
                ("active", self.ACCENT_ACTIVE),
                ("pressed", "#30ac8b"),
            ],
        )
        style.configure(
            "Icon.TButton",
            background=self.SURFACE_RAISED,
            foreground=self.TEXT,
            borderwidth=1,
            padding=(7, 7),
            font=("Segoe UI Symbol", 12),
        )
        style.configure(
            "TEntry",
            fieldbackground=self.SURFACE_RAISED,
            foreground=self.TEXT,
            insertcolor=self.TEXT,
            padding=6,
        )
        style.configure(
            "TSpinbox",
            fieldbackground=self.SURFACE_RAISED,
            foreground=self.TEXT,
            arrowcolor=self.MUTED,
            padding=4,
        )
        style.configure(
            "TCombobox",
            fieldbackground=self.SURFACE_RAISED,
            background=self.SURFACE_RAISED,
            foreground=self.TEXT,
            arrowcolor=self.MUTED,
            padding=4,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.SURFACE_RAISED)],
            foreground=[("readonly", self.TEXT)],
            selectbackground=[("readonly", self.SURFACE_RAISED)],
            selectforeground=[("readonly", self.TEXT)],
        )

    def _build_interface(self):
        self._build_toolbar()

        self.main_pane = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            bg=self.BG,
            bd=0,
            sashwidth=6,
            sashpad=0,
            sashrelief=tk.FLAT,
            showhandle=False,
        )
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))

        self._build_canvas_panel()
        self._build_output_panel()

        self.main_pane.add(
            self.canvas_panel,
            minsize=420,
            stretch="always",
        )
        self.main_pane.add(
            self.output_panel,
            minsize=290,
            width=360,
            stretch="never",
        )

        self.status_label = ttk.Label(
            self.root,
            textvariable=self.status_var,
            style="Status.TLabel",
            anchor=tk.W,
        )
        self.status_label.pack(fill=tk.X)

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=(12, 10))
        self.toolbar = toolbar
        toolbar.pack(fill=tk.X)

        title_block = ttk.Frame(toolbar)
        self.title_block = title_block
        title_block.pack(side=tk.LEFT, padx=(0, 18))
        ttk.Label(
            title_block,
            text="SPRITE MAKER",
            font=("Segoe UI Semibold", 12),
            foreground=self.ACCENT,
        ).pack(anchor=tk.W)
        ttk.Label(
            title_block,
            textvariable=self.grid_summary_var,
            style="Muted.TLabel",
        ).pack(anchor=tk.W)

        self.first_toolbar_divider = self._toolbar_divider(toolbar)

        grid_controls = ttk.Frame(toolbar)
        grid_controls.pack(side=tk.LEFT, padx=12)
        ttk.Label(
            grid_controls,
            text="GRID",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=4, sticky=tk.W)

        self.width_spinbox = ttk.Spinbox(
            grid_controls,
            from_=self.MIN_GRID_SIZE,
            to=self.MAX_GRID_SIZE,
            textvariable=self.width_var,
            width=5,
            justify=tk.CENTER,
        )
        self.width_spinbox.grid(row=1, column=0)
        ttk.Label(grid_controls, text="×").grid(row=1, column=1, padx=5)
        self.height_spinbox = ttk.Spinbox(
            grid_controls,
            from_=self.MIN_GRID_SIZE,
            to=self.MAX_GRID_SIZE,
            textvariable=self.height_var,
            width=5,
            justify=tk.CENTER,
        )
        self.height_spinbox.grid(row=1, column=2)
        ttk.Button(
            grid_controls,
            text="Apply",
            command=self.apply_grid_size,
        ).grid(row=1, column=3, padx=(7, 0))

        self._toolbar_divider(toolbar)

        brush_controls = ttk.Frame(toolbar)
        brush_controls.pack(side=tk.LEFT, padx=12)
        ttk.Label(
            brush_controls,
            text="BRUSH",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=5, sticky=tk.W)
        self.brush_size_spinbox = ttk.Spinbox(
            brush_controls,
            from_=1,
            to=self.MAX_BRUSH_SIZE,
            textvariable=self.brush_size_var,
            width=4,
            justify=tk.CENTER,
            command=self._refresh_brush_preview,
        )
        self.brush_size_spinbox.grid(row=1, column=0)

        tool_strip = tk.Frame(brush_controls, bg=self.SURFACE)
        tool_strip.grid(row=1, column=1, padx=(6, 0))
        for column, tool_name in enumerate(
            ("Square", "Circle", "Checker", "Fill", "Select")
        ):
            button = self._create_tool_button(tool_strip, tool_name)
            button.grid(row=0, column=column, padx=(0 if column == 0 else 3, 0))
            self.tool_buttons[tool_name] = button
        self._refresh_tool_buttons()

        self._toolbar_divider(toolbar)

        name_controls = ttk.Frame(toolbar)
        name_controls.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)
        ttk.Label(
            name_controls,
            text="SPRITE NAME",
            style="Muted.TLabel",
        ).pack(anchor=tk.W)
        self.sprite_name_entry = ttk.Entry(
            name_controls,
            textvariable=self.sprite_name_var,
            width=18,
        )
        self.sprite_name_entry.pack(fill=tk.X)

        self.clear_button = ttk.Button(
            toolbar,
            text="Clear",
            command=self.clear_canvas,
        )
        self.clear_button.pack(side=tk.RIGHT, padx=(7, 0))
        self.copy_output_button = ttk.Button(
            toolbar,
            text="Copy Output",
            style="Accent.TButton",
            command=self.copy_output,
        )
        self.copy_output_button.pack(side=tk.RIGHT)
        self.redo_button = ttk.Button(
            toolbar,
            text="↷",
            style="Icon.TButton",
            width=2,
            command=self.redo,
        )
        self.redo_button.pack(side=tk.RIGHT, padx=(4, 0))
        self.undo_button = ttk.Button(
            toolbar,
            text="↶",
            style="Icon.TButton",
            width=2,
            command=self.undo,
        )
        self.undo_button.pack(side=tk.RIGHT, padx=(7, 0))
        self.toolbar.bind("<Configure>", self._on_toolbar_configure)
        self.toolbar_compact = False

    def _toolbar_divider(self, parent):
        divider = tk.Frame(
            parent,
            width=1,
            height=40,
            bg=self.BORDER,
        )
        divider.pack(side=tk.LEFT, fill=tk.Y, pady=2)
        return divider

    def _on_toolbar_configure(self, event):
        compact = event.width < 1000
        if compact == self.toolbar_compact:
            return
        self.toolbar_compact = compact

        if compact:
            self.title_block.pack_forget()
            self.copy_output_button.configure(text="⧉", width=2)
            self.clear_button.configure(text="×", width=2)
        else:
            self.title_block.pack(
                side=tk.LEFT,
                padx=(0, 18),
                before=self.first_toolbar_divider,
            )
            self.copy_output_button.configure(
                text="Copy Output",
                width=0,
            )
            self.clear_button.configure(text="Clear", width=0)

    def _create_tool_button(self, parent, tool_name):
        button = tk.Canvas(
            parent,
            width=27,
            height=27,
            bg=self.SURFACE,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            cursor="hand2",
            takefocus=True,
        )
        button.bind(
            "<Button-1>",
            lambda _event, name=tool_name: self._select_tool(name),
        )
        button.bind(
            "<Return>",
            lambda _event, name=tool_name: self._select_tool(name),
        )
        button.bind(
            "<space>",
            lambda _event, name=tool_name: self._select_tool(name),
        )
        button.bind(
            "<Enter>",
            lambda _event, name=tool_name: self.status_var.set(
                self._tool_help(name)
            ),
        )
        button.bind(
            "<Leave>",
            lambda _event: self.status_var.set(
                "Left-drag to draw  |  Right-drag to erase"
            ),
        )
        return button

    @staticmethod
    def _tool_help(tool_name):
        help_text = {
            "Square": "Square brush",
            "Circle": "Circular brush",
            "Checker": "Checkerboard brush",
            "Fill": "Eight-way connected flood fill",
            "Select": "Rectangular pixel selection",
        }
        return help_text[tool_name]

    def _select_tool(self, tool_name):
        self.brush_shape_var.set(tool_name)
        self.canvas.focus_set()
        return "break"

    def _refresh_tool_buttons(self):
        selected = self.brush_shape_var.get()
        for tool_name, button in self.tool_buttons.items():
            active = (
                tool_name == selected
                or (tool_name == "Select" and selected == "Paste")
            )
            button.configure(
                bg=self.SURFACE_RAISED if active else self.SURFACE,
                highlightbackground=self.ACCENT if active else self.BORDER,
            )
            self._draw_tool_icon(button, tool_name, active)

    def _draw_tool_icon(self, button, tool_name, active):
        button.delete("all")
        color = self.ACCENT if active else self.MUTED

        if tool_name == "Square":
            button.create_rectangle(
                8, 8, 20, 20,
                fill=color,
                outline="",
            )
        elif tool_name == "Circle":
            button.create_oval(
                7, 7, 21, 21,
                fill=color,
                outline="",
            )
        elif tool_name == "Checker":
            for row in range(3):
                for column in range(3):
                    if (row + column) % 2 == 0:
                        x1 = 7 + (column * 5)
                        y1 = 7 + (row * 5)
                        button.create_rectangle(
                            x1, y1, x1 + 5, y1 + 5,
                            fill=color,
                            outline="",
                        )
            button.create_rectangle(7, 7, 22, 22, outline=color)
        elif tool_name == "Fill":
            button.create_polygon(
                7, 9, 17, 6, 21, 15, 11, 19,
                outline=color,
                fill="",
                width=2,
            )
            button.create_line(
                9, 21, 22, 21,
                fill=color,
                width=2,
            )
        else:
            button.create_rectangle(
                6, 7, 21, 20,
                outline=color,
                dash=(2, 2),
                width=2,
            )
            button.create_rectangle(
                18, 17, 23, 22,
                fill=self.SURFACE_RAISED if active else self.SURFACE,
                outline=color,
            )

    def _build_canvas_panel(self):
        self.canvas_panel = tk.Frame(
            self.main_pane,
            bg=self.CANVAS_BG,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        self.canvas = tk.Canvas(
            self.canvas_panel,
            bg=self.CANVAS_BG,
            bd=0,
            highlightthickness=0,
            cursor="crosshair",
            takefocus=True,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def _build_output_panel(self):
        self.output_panel = tk.Frame(
            self.main_pane,
            bg=self.SURFACE,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )

        output_header = ttk.Frame(self.output_panel, padding=(11, 8))
        output_header.pack(fill=tk.X)
        ttk.Label(
            output_header,
            text="LIVE C OUTPUT",
            font=("Segoe UI Semibold", 10),
        ).pack(side=tk.LEFT)
        ttk.Label(
            output_header,
            text="updates automatically",
            style="Muted.TLabel",
        ).pack(side=tk.RIGHT)

        text_frame = tk.Frame(self.output_panel, bg=self.SURFACE)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.code_text = tk.Text(
            text_frame,
            bg="#0e1218",
            fg="#d9e2eb",
            insertbackground=self.TEXT,
            selectbackground="#285b53",
            selectforeground=self.TEXT,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=10,
            wrap=tk.NONE,
            font=("Cascadia Mono", 9),
            state=tk.DISABLED,
        )
        y_scroll = ttk.Scrollbar(
            text_frame,
            orient=tk.VERTICAL,
            command=self.code_text.yview,
        )
        x_scroll = ttk.Scrollbar(
            text_frame,
            orient=tk.HORIZONTAL,
            command=self.code_text.xview,
        )
        self.code_text.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set,
        )

        self.code_text.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

    def _bind_events(self):
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<ButtonPress-1>", self._start_draw)
        self.canvas.bind("<B1-Motion>", self._continue_draw)
        self.canvas.bind("<ButtonRelease-1>", self._end_draw)
        self.canvas.bind("<ButtonPress-3>", self._start_erase)
        self.canvas.bind("<B3-Motion>", self._continue_erase)
        self.canvas.bind("<ButtonRelease-3>", self._end_draw)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Leave>", self._hide_brush_preview)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)

        self.width_spinbox.bind("<Return>", self.apply_grid_size)
        self.height_spinbox.bind("<Return>", self.apply_grid_size)
        self.width_spinbox.bind("<FocusOut>", self._restore_grid_values)
        self.height_spinbox.bind("<FocusOut>", self._restore_grid_values)

        self.root.bind("<Control-Shift-C>", self.copy_output)
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-y>", self.redo)
        self.root.bind("<Control-c>", self.copy_selection)
        self.root.bind("<Control-x>", self.cut_selection)
        self.root.bind("<Control-v>", self.activate_selection_brush)
        self.root.bind("<Delete>", self.delete_selection)
        self.root.bind("<Control-Shift-greater>", self._increase_brush_size)
        self.root.bind("<Control-Shift-less>", self._decrease_brush_size)
        self.root.bind("<Control-Shift-period>", self._increase_brush_size)
        self.root.bind("<Control-Shift-comma>", self._decrease_brush_size)
        self.root.bind("<Escape>", lambda _event: self.canvas.focus_set())

    def _initial_layout(self):
        try:
            pane_width = self.main_pane.winfo_width()
            self.main_pane.sash_place(0, max(420, pane_width - 370), 1)
        except tk.TclError:
            pass
        self._update_history_buttons()
        self.render_canvas()
        self.update_output()
        self.canvas.focus_set()

    def _on_canvas_configure(self, _event=None):
        if self.render_job is not None:
            self.root.after_cancel(self.render_job)
        self.render_job = self.root.after(35, self.render_canvas)

    def render_canvas(self):
        self.render_job = None
        self.canvas.delete("all")
        self.pixel_items.clear()

        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        padding = 30
        usable_width = max(1, canvas_width - (padding * 2))
        usable_height = max(1, canvas_height - (padding * 2))

        self.base_cell_size = max(
            0.25,
            min(
                usable_width / self.grid_width,
                usable_height / self.grid_height,
            ),
        )
        self.zoom_level = max(
            1.0,
            min(self.zoom_level, self._max_zoom_level()),
        )
        self.cell_size = self.base_cell_size * self.zoom_level

        if self.zoom_level <= 1.0001:
            self.zoom_level = 1.0
            self.view_center_x = self.grid_width / 2
            self.view_center_y = self.grid_height / 2
        else:
            self._clamp_view_center()

        drawn_width = self.cell_size * self.grid_width
        drawn_height = self.cell_size * self.grid_height
        self.grid_left = (
            (canvas_width / 2)
            - (self.view_center_x * self.cell_size)
        )
        self.grid_top = (
            (canvas_height / 2)
            - (self.view_center_y * self.cell_size)
        )

        right = self.grid_left + drawn_width
        bottom = self.grid_top + drawn_height
        self.canvas.create_rectangle(
            self.grid_left,
            self.grid_top,
            right,
            bottom,
            fill=self.EMPTY_PIXEL,
            outline=self.BORDER,
            width=2,
            tags="grid_background",
        )

        for y, row in enumerate(self.pixels):
            for x, value in enumerate(row):
                if value:
                    self._create_pixel_item(x, y)

        if self.cell_size >= 5:
            line_width = 1
            for x in range(1, self.grid_width):
                line_x = self.grid_left + (x * self.cell_size)
                self.canvas.create_line(
                    line_x,
                    self.grid_top,
                    line_x,
                    bottom,
                    fill=self.GRID_LINE,
                    width=line_width,
                    tags="grid_lines",
                )
            for y in range(1, self.grid_height):
                line_y = self.grid_top + (y * self.cell_size)
                self.canvas.create_line(
                    self.grid_left,
                    line_y,
                    right,
                    line_y,
                    fill=self.GRID_LINE,
                    width=line_width,
                    tags="grid_lines",
                )

        self.canvas.create_text(
            14,
            12,
            anchor=tk.NW,
            fill=self.MUTED,
            font=("Segoe UI Semibold", 9),
            text=(
                f"{self.grid_width} × {self.grid_height}   "
                f"•   {self._tool_summary()}   "
                f"•   {self.zoom_level:.1f}× zoom"
            ),
            tags="overlay",
        )
        self._draw_selection_outline()
        self._refresh_brush_preview()

    def _max_zoom_level(self):
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        usable_width = max(1, canvas_width - 60)
        usable_height = max(1, canvas_height - 60)
        ten_cell_size = min(usable_width / 10, usable_height / 10)
        return max(1.0, ten_cell_size / self.base_cell_size)

    def _clamp_view_center(self):
        visible_width = self.canvas.winfo_width() / self.cell_size
        visible_height = self.canvas.winfo_height() / self.cell_size

        if visible_width >= self.grid_width:
            self.view_center_x = self.grid_width / 2
        else:
            half_visible_width = visible_width / 2
            self.view_center_x = max(
                half_visible_width,
                min(
                    self.grid_width - half_visible_width,
                    self.view_center_x,
                ),
            )

        if visible_height >= self.grid_height:
            self.view_center_y = self.grid_height / 2
        else:
            half_visible_height = visible_height / 2
            self.view_center_y = max(
                half_visible_height,
                min(
                    self.grid_height - half_visible_height,
                    self.view_center_y,
                ),
            )

    def _on_mouse_wheel(self, event):
        if getattr(event, "num", None) == 4:
            direction = 1
        elif getattr(event, "num", None) == 5:
            direction = -1
        else:
            direction = 1 if event.delta > 0 else -1

        old_zoom = self.zoom_level
        old_cell_size = self.cell_size
        world_x = (event.x - self.grid_left) / old_cell_size
        world_y = (event.y - self.grid_top) / old_cell_size

        factor = 1.25
        if direction > 0:
            new_zoom = old_zoom * factor
        else:
            new_zoom = old_zoom / factor
        new_zoom = max(1.0, min(self._max_zoom_level(), new_zoom))

        if abs(new_zoom - old_zoom) < 0.0001:
            return "break"

        self.zoom_level = new_zoom
        new_cell_size = self.base_cell_size * new_zoom
        canvas_center_x = self.canvas.winfo_width() / 2
        canvas_center_y = self.canvas.winfo_height() / 2
        self.view_center_x = (
            world_x - ((event.x - canvas_center_x) / new_cell_size)
        )
        self.view_center_y = (
            world_y - ((event.y - canvas_center_y) / new_cell_size)
        )

        if new_zoom <= 1.0001:
            self.view_center_x = self.grid_width / 2
            self.view_center_y = self.grid_height / 2

        self.render_canvas()
        self.status_var.set(
            f"Zoom {self.zoom_level:.1f}×  •  "
            "Mouse wheel zooms around the pointer"
        )
        return "break"

    def _pixel_bounds(self, x, y, inset=0):
        x1 = self.grid_left + (x * self.cell_size) + inset
        y1 = self.grid_top + (y * self.cell_size) + inset
        x2 = self.grid_left + ((x + 1) * self.cell_size) - inset
        y2 = self.grid_top + ((y + 1) * self.cell_size) - inset
        return x1, y1, x2, y2

    def _create_pixel_item(self, x, y):
        if (x, y) in self.pixel_items:
            return
        item = self.canvas.create_rectangle(
            *self._pixel_bounds(x, y),
            fill=self.FILLED_PIXEL,
            outline="",
            tags=("pixel",),
        )
        self.pixel_items[(x, y)] = item

    def _set_pixel(self, x, y, value):
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height):
            return False
        if self.pixels[y][x] == value:
            return False

        self.pixels[y][x] = value
        item = self.pixel_items.pop((x, y), None)
        if item is not None:
            self.canvas.delete(item)
        if value:
            self._create_pixel_item(x, y)
        return True

    def _event_to_cell(self, event):
        x = (event.x - self.grid_left) // self.cell_size
        y = (event.y - self.grid_top) // self.cell_size
        if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
            return int(x), int(y)
        return None

    def _start_draw(self, event):
        return self._start_stroke(event, 1)

    def _start_erase(self, event):
        return self._start_stroke(event, 0)

    def _start_stroke(self, event, value):
        self.canvas.focus_set()
        cell = self._event_to_cell(event)
        if cell is None:
            return "break"

        tool_name = self.brush_shape_var.get()
        if tool_name == "Select":
            if value == 0:
                self.selection_start = None
                self.selection_bounds = None
                self.canvas.delete("selection")
                self.status_var.set("Selection cleared.")
                return "break"
            self.selection_start = cell
            self.selection_bounds = (*cell, *cell)
            self._draw_selection_outline()
            self.status_var.set(
                "Drag to select pixels  •  Ctrl+C copies the selection"
            )
            return "break"

        if tool_name == "Fill":
            self.stroke_value = None
            self.last_stroke_cell = None
            self._begin_history_action()
            changed_count = self._flood_fill(*cell, value)
            self.hover_cell = cell
            self._draw_brush_preview(cell, value)
            if changed_count:
                self._commit_history_action()
                self.render_canvas()
                self._schedule_output_update()
                action = "Filled" if value else "Erased"
                self.status_var.set(
                    f"{action} {changed_count:,} diagonally connected pixels."
                )
            else:
                self._discard_history_action()
            return "break"

        self._begin_history_action()
        self.stroke_value = value
        self.last_stroke_cell = None
        self.stroke_changed = False
        self._paint_to_event(event)
        return "break"

    def _continue_draw(self, event):
        if (
            self.brush_shape_var.get() == "Select"
            and self.selection_start is not None
        ):
            self._update_selection(event)
            return "break"
        if self.stroke_value == 1:
            self._paint_to_event(event)
        return "break"

    def _continue_erase(self, event):
        if self.stroke_value == 0:
            self._paint_to_event(event)
        return "break"

    def _end_draw(self, _event=None):
        if self.selection_start is not None:
            self.selection_start = None
            if self.selection_bounds is not None:
                x1, y1, x2, y2 = self.selection_bounds
                self.status_var.set(
                    f"Selected {x2 - x1 + 1} × {y2 - y1 + 1} pixels  "
                    "•  Ctrl+C to copy"
                )
            return "break"

        if self.pending_history_state is not None:
            if self.stroke_changed:
                self._commit_history_action()
            else:
                self._discard_history_action()
        self.stroke_value = None
        self.last_stroke_cell = None
        self.stroke_changed = False
        return "break"

    def _paint_to_event(self, event):
        cell = self._event_to_cell(event)
        if cell is None:
            return

        changed = False
        if self.last_stroke_cell is None:
            cells = [cell]
        else:
            cells = self._line_cells(self.last_stroke_cell, cell)

        for x, y in cells:
            changed = self._stamp_brush(x, y, self.stroke_value) or changed

        self.last_stroke_cell = cell
        self.hover_cell = cell
        self._draw_brush_preview(cell, self.stroke_value)
        if changed:
            self.stroke_changed = True
            self._schedule_output_update()

    @staticmethod
    def _line_cells(start, end):
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        step_x = 1 if x0 < x1 else -1
        step_y = 1 if y0 < y1 else -1
        error = dx + dy
        cells = []

        while True:
            cells.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            doubled_error = 2 * error
            if doubled_error >= dy:
                error += dy
                x0 += step_x
            if doubled_error <= dx:
                error += dx
                y0 += step_y
        return cells

    def _stamp_brush(self, center_x, center_y, value):
        changed = False
        for x, y in self._brush_cells(center_x, center_y):
            changed = self._set_pixel(x, y, value) or changed
        return changed

    def _flood_fill(self, start_x, start_y, value):
        target_value = self.pixels[start_y][start_x]
        if target_value == value:
            return 0

        pending = [(start_x, start_y)]
        self.pixels[start_y][start_x] = value
        changed_count = 0

        while pending:
            x, y = pending.pop()
            changed_count += 1
            for offset_y in (-1, 0, 1):
                for offset_x in (-1, 0, 1):
                    if offset_x == 0 and offset_y == 0:
                        continue
                    neighbour_x = x + offset_x
                    neighbour_y = y + offset_y
                    if not (
                        0 <= neighbour_x < self.grid_width
                        and 0 <= neighbour_y < self.grid_height
                    ):
                        continue
                    if (
                        self.pixels[neighbour_y][neighbour_x]
                        == target_value
                    ):
                        self.pixels[neighbour_y][neighbour_x] = value
                        pending.append((neighbour_x, neighbour_y))
        return changed_count

    def _brush_cells(self, center_x, center_y):
        size = self._brush_size()
        start = -((size - 1) // 2)
        end = size // 2
        shape = self.brush_shape_var.get()
        if shape == "Paste":
            if not self.clipboard_pixels:
                return []
            pattern_height = len(self.clipboard_pixels)
            pattern_width = len(self.clipboard_pixels[0])
            start_x = -((pattern_width - 1) // 2)
            start_y = -((pattern_height - 1) // 2)
            cells = []
            for pattern_y, row in enumerate(self.clipboard_pixels):
                for pattern_x, pixel in enumerate(row):
                    if not pixel:
                        continue
                    x = center_x + start_x + pattern_x
                    y = center_y + start_y + pattern_y
                    if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                        cells.append((x, y))
            return cells
        if shape == "Select":
            return [(center_x, center_y)]
        if shape == "Fill":
            return [(center_x, center_y)]

        center = (size - 1) / 2
        radius = size / 2
        cells = []

        for offset_y in range(start, end + 1):
            for offset_x in range(start, end + 1):
                if shape == "Circle":
                    local_x = offset_x - start
                    local_y = offset_y - start
                    distance_squared = (
                        (local_x - center) ** 2
                        + (local_y - center) ** 2
                    )
                    if distance_squared > radius ** 2:
                        continue
                if shape == "Checker":
                    local_x = offset_x - start
                    local_y = offset_y - start
                    if (local_x + local_y) % 2:
                        continue
                x = center_x + offset_x
                y = center_y + offset_y
                if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
                    cells.append((x, y))
        return cells

    def _brush_size(self):
        try:
            value = int(self.brush_size_var.get())
        except (tk.TclError, ValueError):
            value = 1
        return max(1, min(self.MAX_BRUSH_SIZE, value))

    def _increase_brush_size(self, _event=None):
        return self._change_brush_size(1)

    def _decrease_brush_size(self, _event=None):
        return self._change_brush_size(-1)

    def _change_brush_size(self, amount):
        new_size = max(
            1,
            min(self.MAX_BRUSH_SIZE, self._brush_size() + amount),
        )
        self.brush_size_var.set(new_size)
        self.status_var.set(
            f"Brush size {new_size} px  •  "
            "Ctrl+Shift+< / Ctrl+Shift+> adjusts size"
        )
        return "break"

    def _on_canvas_motion(self, event):
        cell = self._event_to_cell(event)
        self.hover_cell = cell
        if cell is None:
            self._hide_brush_preview()
        else:
            preview_value = self.stroke_value
            if preview_value is None:
                preview_value = 1
            self._draw_brush_preview(cell, preview_value)

    def _update_selection(self, event):
        cell = self._event_to_cell(event)
        if cell is None or self.selection_start is None:
            return
        start_x, start_y = self.selection_start
        end_x, end_y = cell
        self.selection_bounds = (
            min(start_x, end_x),
            min(start_y, end_y),
            max(start_x, end_x),
            max(start_y, end_y),
        )
        self._draw_selection_outline()

    def _draw_selection_outline(self):
        self.canvas.delete("selection")
        if self.selection_bounds is None:
            return
        x1, y1, x2, y2 = self.selection_bounds
        left, top, _, _ = self._pixel_bounds(x1, y1)
        _, _, right, bottom = self._pixel_bounds(x2, y2)
        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=self.ACCENT,
            width=2,
            dash=(5, 3),
            tags="selection",
        )
        self.canvas.tag_raise("selection")

    def _draw_brush_preview(self, cell, value=1):
        self.canvas.delete("brush_preview")
        color = self.PREVIEW_DRAW if value else self.PREVIEW_ERASE
        inset = 1 if self.cell_size >= 5 else 0
        for x, y in self._brush_cells(*cell):
            self.canvas.create_rectangle(
                *self._pixel_bounds(x, y, inset=inset),
                outline=color,
                width=2 if self.cell_size >= 8 else 1,
                tags="brush_preview",
            )
        self.canvas.tag_raise("brush_preview")

    def _hide_brush_preview(self, _event=None):
        self.hover_cell = None
        self.canvas.delete("brush_preview")

    def _refresh_brush_preview(self):
        self._update_grid_summary()
        if self.hover_cell is not None:
            preview_value = self.stroke_value
            if preview_value is None:
                preview_value = 1
            self._draw_brush_preview(self.hover_cell, preview_value)

    def _on_brush_changed(self, *_args):
        self.root.after_idle(self._finish_brush_change)

    def _finish_brush_change(self):
        self._refresh_tool_buttons()
        if self.brush_shape_var.get() in ("Fill", "Select", "Paste"):
            self.brush_size_spinbox.configure(state=tk.DISABLED)
        else:
            self.brush_size_spinbox.configure(state=tk.NORMAL)
        self._refresh_brush_preview()

    def copy_selection(self, _event=None):
        if self._focus_is_text_input():
            return None
        if self.selection_bounds is None:
            self.status_var.set(
                "Select a rectangular area before using Ctrl+C."
            )
            return "break"

        width, height, active_pixels = self._copy_selected_pixels()
        self.status_var.set(
            f"Copied {width} × {height} selection "
            f"({active_pixels} set pixels)  •  Ctrl+V makes it a brush"
        )
        return "break"

    def cut_selection(self, _event=None):
        if self._focus_is_text_input():
            return None
        if self.selection_bounds is None:
            self.status_var.set(
                "Select a rectangular area before using Ctrl+X."
            )
            return "break"

        width, height, _active_pixels = self._copy_selected_pixels()
        removed_pixels = self._clear_selected_pixels()
        self.status_var.set(
            f"Cut {width} × {height} selection "
            f"({removed_pixels} set pixels removed)  •  "
            "Ctrl+V makes it a brush"
        )
        return "break"

    def delete_selection(self, _event=None):
        if self._focus_is_text_input():
            return None
        if self.selection_bounds is None:
            self.status_var.set(
                "Select a rectangular area before pressing Delete."
            )
            return "break"

        removed_pixels = self._clear_selected_pixels()
        if removed_pixels:
            self.status_var.set(
                f"Deleted {removed_pixels} set pixels from the selection."
            )
        else:
            self.status_var.set("The selected area is already clear.")
        return "break"

    def _focus_is_text_input(self):
        focused_widget = self.root.focus_get()
        return isinstance(
            focused_widget,
            (tk.Entry, tk.Text, ttk.Entry, ttk.Spinbox),
        )

    def _copy_selected_pixels(self):
        x1, y1, x2, y2 = self.selection_bounds
        self.clipboard_pixels = [
            self.pixels[y][x1:x2 + 1]
            for y in range(y1, y2 + 1)
        ]
        width = x2 - x1 + 1
        height = y2 - y1 + 1
        active_pixels = sum(
            sum(row) for row in self.clipboard_pixels
        )
        return width, height, active_pixels

    def _clear_selected_pixels(self):
        x1, y1, x2, y2 = self.selection_bounds
        removed_pixels = sum(
            self.pixels[y][x]
            for y in range(y1, y2 + 1)
            for x in range(x1, x2 + 1)
        )
        if not removed_pixels:
            return 0

        self._begin_history_action()
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.pixels[y][x] = 0
        self._commit_history_action()
        self.render_canvas()
        self._schedule_output_update()
        return removed_pixels

    def activate_selection_brush(self, _event=None):
        if self._focus_is_text_input():
            return None
        if not self.clipboard_pixels:
            self.status_var.set(
                "Copy a selection with Ctrl+C before using Ctrl+V."
            )
            return "break"

        self.brush_shape_var.set("Paste")
        width = len(self.clipboard_pixels[0])
        height = len(self.clipboard_pixels)
        self.status_var.set(
            f"Selection brush active: {width} × {height}  •  "
            "Left-click stamps; right-click erases"
        )
        self.canvas.focus_set()
        return "break"

    def _snapshot(self):
        return (
            self.grid_width,
            self.grid_height,
            tuple(tuple(row) for row in self.pixels),
        )

    def _begin_history_action(self):
        if self.pending_history_state is None:
            self.pending_history_state = self._snapshot()

    def _commit_history_action(self):
        if self.pending_history_state is None:
            return
        self.undo_stack.append(self.pending_history_state)
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        self.pending_history_state = None
        self.redo_stack.clear()
        self._update_history_buttons()

    def _discard_history_action(self):
        self.pending_history_state = None

    def _restore_snapshot(self, snapshot):
        width, height, rows = snapshot
        self.grid_width = width
        self.grid_height = height
        self.pixels = [list(row) for row in rows]
        self.width_var.set(str(width))
        self.height_var.set(str(height))
        self.zoom_level = 1.0
        self.view_center_x = width / 2
        self.view_center_y = height / 2
        self.selection_start = None
        self.selection_bounds = None
        self.pending_history_state = None
        self.stroke_value = None
        self.last_stroke_cell = None
        self._update_grid_summary()
        self.render_canvas()
        self._schedule_output_update()

    def undo(self, _event=None):
        if not self.undo_stack:
            self.status_var.set("Nothing to undo.")
            return "break"
        self.redo_stack.append(self._snapshot())
        self._restore_snapshot(self.undo_stack.pop())
        self._update_history_buttons()
        self.status_var.set("Undo")
        self.canvas.focus_set()
        return "break"

    def redo(self, _event=None):
        if not self.redo_stack:
            self.status_var.set("Nothing to redo.")
            return "break"
        self.undo_stack.append(self._snapshot())
        self._restore_snapshot(self.redo_stack.pop())
        self._update_history_buttons()
        self.status_var.set("Redo")
        self.canvas.focus_set()
        return "break"

    def _update_history_buttons(self):
        if self.undo_stack:
            self.undo_button.state(["!disabled"])
        else:
            self.undo_button.state(["disabled"])
        if self.redo_stack:
            self.redo_button.state(["!disabled"])
        else:
            self.redo_button.state(["disabled"])

    def apply_grid_size(self, _event=None):
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
        except (tk.TclError, ValueError):
            self.status_var.set("Grid dimensions must be whole numbers.")
            self._restore_grid_values()
            return "break"

        if not (
            self.MIN_GRID_SIZE <= width <= self.MAX_GRID_SIZE
            and self.MIN_GRID_SIZE <= height <= self.MAX_GRID_SIZE
        ):
            self.status_var.set(
                f"Grid dimensions must be between "
                f"{self.MIN_GRID_SIZE} and {self.MAX_GRID_SIZE}."
            )
            self._restore_grid_values()
            return "break"

        if width == self.grid_width and height == self.grid_height:
            self.canvas.focus_set()
            return "break"

        self._begin_history_action()
        resized_pixels = self._blank_pixels(width, height)
        copy_width = min(width, self.grid_width)
        copy_height = min(height, self.grid_height)
        for y in range(copy_height):
            resized_pixels[y][:copy_width] = self.pixels[y][:copy_width]

        self.grid_width = width
        self.grid_height = height
        self.pixels = resized_pixels
        self.zoom_level = 1.0
        self.view_center_x = width / 2
        self.view_center_y = height / 2
        self.selection_start = None
        self.selection_bounds = None
        self.width_var.set(str(width))
        self.height_var.set(str(height))
        self._commit_history_action()
        self._update_grid_summary()
        self.render_canvas()
        self._schedule_output_update()
        self.status_var.set(
            f"Grid resized to {width} × {height}; overlapping pixels preserved."
        )
        self.canvas.focus_set()
        return "break"

    def _restore_grid_values(self, _event=None):
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
        except (tk.TclError, ValueError):
            self.width_var.set(str(self.grid_width))
            self.height_var.set(str(self.grid_height))
            return
        if not (
            self.MIN_GRID_SIZE <= width <= self.MAX_GRID_SIZE
            and self.MIN_GRID_SIZE <= height <= self.MAX_GRID_SIZE
        ):
            self.width_var.set(str(self.grid_width))
            self.height_var.set(str(self.grid_height))

    def _update_grid_summary(self):
        self.grid_summary_var.set(
            f"{self.grid_width} × {self.grid_height}  •  "
            f"{self._tool_summary()}"
        )

    def _tool_summary(self):
        tool_name = self.brush_shape_var.get()
        if tool_name == "Fill":
            return "eight-way fill"
        if tool_name == "Select":
            return "selection"
        if tool_name == "Paste" and self.clipboard_pixels:
            return (
                f"{len(self.clipboard_pixels[0])} × "
                f"{len(self.clipboard_pixels)} selection brush"
            )
        return f"{self._brush_size()} px {tool_name.lower()}"

    def clear_canvas(self):
        if not any(any(row) for row in self.pixels):
            self.status_var.set("Canvas is already clear.")
            self.canvas.focus_set()
            return
        self._begin_history_action()
        self.pixels = self._blank_pixels(self.grid_width, self.grid_height)
        self._commit_history_action()
        self.render_canvas()
        self._schedule_output_update()
        self.status_var.set("Canvas cleared.")
        self.canvas.focus_set()

    @staticmethod
    def _c_identifier(value):
        identifier = re.sub(r"\W+", "_", value.strip())
        identifier = identifier.strip("_") or "sprite"
        if identifier[0].isdigit():
            identifier = f"_{identifier}"
        return identifier

    def generate_code(self):
        base_name = self._c_identifier(self.sprite_name_var.get())
        data_name = base_name.lower()
        sprite_name = base_name.upper()
        bytes_per_row = math.ceil(self.grid_width / 8)
        total_bytes = bytes_per_row * self.grid_height

        code_lines = [
            f"static const uint8_t {data_name}[{total_bytes}] = {{"
        ]

        for row_index, row in enumerate(self.pixels):
            byte_values = []
            for start in range(0, self.grid_width, 8):
                byte_value = 0
                for bit in range(8):
                    x = start + bit
                    if x < self.grid_width and row[x]:
                        byte_value |= 1 << (7 - bit)
                byte_values.append(f"0b{byte_value:08b}")

            row_comment = "".join("*" if value else " " for value in row)
            comma = "," if row_index < self.grid_height - 1 else ""
            code_lines.append(
                f"    {', '.join(byte_values)}{comma}  // {row_comment}"
            )

        code_lines.extend(
            [
                "};",
                "",
                f"const Sprite {sprite_name} = {{",
                f"    .width  = {self.grid_width},",
                f"    .height = {self.grid_height},",
                f"    .data   = {data_name}",
                "};",
                "",
                f"extern const Sprite {sprite_name};",
            ]
        )
        return "\n".join(code_lines)

    def _schedule_output_update(self, *_args):
        if self.output_job is not None:
            self.root.after_cancel(self.output_job)
        self.output_job = self.root.after(45, self.update_output)

    def update_output(self):
        self.output_job = None
        code = self.generate_code()
        y_position = self.code_text.yview()[0]
        self.code_text.configure(state=tk.NORMAL)
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", code)
        self.code_text.configure(state=tk.DISABLED)
        self.code_text.yview_moveto(y_position)

    def copy_output(self, _event=None):
        code = self.generate_code()
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.root.update_idletasks()
        self.status_var.set(
            f"Copied {len(code):,} characters of C output to the clipboard."
        )
        return "break"


def main():
    root = tk.Tk()
    PixelArtApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
