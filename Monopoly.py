# The entire code is written by the AI.

import tkinter as tk

# Diagonal wallpaper: (x+y) advances along 45°; tan spans 3 units, brown 1 (3:1).
LIGHT_TAN = "#e8dcc8"
LIGHT_BROWN = "#cbb896"
STRIPE_UNIT = 12  # pixels along (x+y) per stripe slice; brown = 1 unit, tan = 3.

# Outer grid ring: flat fill (not striped) so the board reads clearly.
BORDER_FILL = "#d4c8b2"

GRID_SIZE = 10
HOLE_SIZE = 8
# One-cell border; (10 - 8) / 2 == 1
RING = (GRID_SIZE - HOLE_SIZE) // 2

# Build stripes at 1/SCALE res then zoom — avoids ~w*h tiny canvas rectangles (very laggy).
STRIPE_RENDER_SCALE = 3
# Resize repaint debounce (ms) — Configure fires many times while dragging the window.
REPAINT_DEBOUNCE_MS = 64


def _stripe_color(s: int) -> str:
    U = STRIPE_UNIT
    return LIGHT_TAN if (s // U) % 4 < 3 else LIGHT_BROWN


def _draw_diagonal_stripes(canvas: tk.Canvas) -> None:
    """45° stripes as one PhotoImage (fast); pattern matches world (x+y) so the hole lines up."""
    w, h = canvas.winfo_width(), canvas.winfo_height()
    if w <= 1 or h <= 1:
        return
    sc = STRIPE_RENDER_SCALE
    sw = (w + sc - 1) // sc
    sh = (h + sc - 1) // sc
    small = tk.PhotoImage(width=sw, height=sh)
    for sy in range(sh):
        parts: list[str] = []
        sx = 0
        while sx < sw:
            s = sc * (sx + sy)
            col = _stripe_color(s)
            sx_next = sx + 1
            while sx_next < sw and _stripe_color(sc * (sx_next + sy)) == col:
                sx_next += 1
            n = sx_next - sx
            parts.append(" ".join([col] * n))
            sx = sx_next
        # Tk expects each *row* as a braced list of colors; a bare string only sets one pixel.
        row = " ".join(parts)
        small.put("{" + row + "}", to=(0, sy))
    big = small.zoom(sc, sc)
    canvas._stripe_photo = big  # prevent GC
    canvas.create_image(0, 0, anchor=tk.NW, image=big, tags="stripe")


def _paint_ring_fill(
    canvas: tk.Canvas, gx: int, gy: int, cell: int, fill: str
) -> None:
    """Solid fill for the outer 10×10 ring only (inner 8×8 stays striped)."""
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if i not in (0, GRID_SIZE - 1) and j not in (0, GRID_SIZE - 1):
                continue
            x0 = gx + i * cell
            y0 = gy + j * cell
            canvas.create_rectangle(
                x0,
                y0,
                x0 + cell,
                y0 + cell,
                fill=fill,
                outline="",
                tags="ring",
            )


def _paint_frame_grid(canvas: tk.Canvas, gx: int, gy: int, cell: int) -> None:
    """10×10 grid lines; inner 8×8 has no interior lines — stripes show through, aligned."""
    W = GRID_SIZE * cell
    line_fill = "#5c4a38"
    lw = 2

    def hline(y: int, x0: int, x1: int) -> None:
        if x1 > x0:
            canvas.create_line(
                x0, y, x1, y, fill=line_fill, width=lw, capstyle=tk.ROUND, tags="grid"
            )

    def vline(x: int, y0: int, y1: int) -> None:
        if y1 > y0:
            canvas.create_line(
                x, y0, x, y1, fill=line_fill, width=lw, capstyle=tk.ROUND, tags="grid"
            )

    for k in range(GRID_SIZE + 1):
        y = gy + k * cell
        if k <= RING or k >= GRID_SIZE - RING:
            hline(y, gx, gx + W)
        else:
            hline(y, gx, gx + RING * cell)
            hline(y, gx + (GRID_SIZE - RING) * cell, gx + W)

    for k in range(GRID_SIZE + 1):
        x = gx + k * cell
        if k <= RING or k >= GRID_SIZE - RING:
            vline(x, gy, gy + W)
        else:
            vline(x, gy, gy + RING * cell)
            vline(x, gy + (GRID_SIZE - RING) * cell, gy + W)


def _bind_click_fullscreen(widget: tk.Misc, handler) -> None:
    """Bind left-click on this widget and all descendants so clicks reach fullscreen."""
    widget.bind("<Button-1>", handler, add=True)
    for child in widget.winfo_children():
        _bind_click_fullscreen(child, handler)


def main() -> None:
    root = tk.Tk()
    root.title("Monopoly")
    root.minsize(320, 200)

    game = {"started": False}

    def enter_fullscreen(_event: tk.Event | None = None) -> None:
        root.attributes("-fullscreen", True)

    def exit_fullscreen(_event: tk.Event | None = None) -> None:
        root.attributes("-fullscreen", False)

    root.bind_all("<Escape>", exit_fullscreen)

    bg_canvas = tk.Canvas(
        root,
        highlightthickness=0,
        borderwidth=0,
        background=LIGHT_TAN,
    )
    bg_canvas.pack(fill=tk.BOTH, expand=True)

    content = tk.Frame(root, bg=LIGHT_TAN, padx=28, pady=28)
    title_lbl = tk.Label(
        content,
        text="Monopoly",
        font=("Helvetica", 18, "bold"),
        bg=LIGHT_TAN,
        fg="#3d3020",
    )
    title_lbl.pack(pady=(0, 16))
    start_btn = tk.Button(
        content,
        text="Start",
        font=("Helvetica", 12),
        bg=LIGHT_TAN,
        fg="#3d3020",
        activebackground=LIGHT_BROWN,
        activeforeground="#3d3020",
        highlightthickness=1,
        highlightbackground=LIGHT_BROWN,
        relief=tk.FLAT,
        padx=16,
        pady=6,
    )
    start_btn.pack()
    content.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    content.lift(bg_canvas)

    _paint_job: list[str | None] = [None]

    def _repaint_all() -> None:
        _paint_job[0] = None
        bg_canvas.delete("stripe", "grid", "ring")
        w, h = bg_canvas.winfo_width(), bg_canvas.winfo_height()
        if w <= 1 or h <= 1:
            return
        _draw_diagonal_stripes(bg_canvas)

        if game["started"]:
            cell = max(18, min(w, h) // 14)
            span = GRID_SIZE * cell
            gx = (w - span) // 2
            gy = (h - span) // 2
            _paint_ring_fill(bg_canvas, gx, gy, cell, BORDER_FILL)
            _paint_frame_grid(bg_canvas, gx, gy, cell)
            content.place(
                relx=0.5,
                y=max(8, gy - 12),
                anchor=tk.S,
            )
        else:
            content.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _schedule_repaint(_event: tk.Event | None = None) -> None:
        if _paint_job[0] is not None:
            root.after_cancel(_paint_job[0])
        _paint_job[0] = root.after(REPAINT_DEBOUNCE_MS, _repaint_all)

    def on_start() -> None:
        if game["started"]:
            return
        game["started"] = True
        start_btn.destroy()
        title_lbl.pack_configure(pady=(0, 0))
        _repaint_all()

    start_btn.configure(command=on_start)

    bg_canvas.bind("<Configure>", _schedule_repaint)

    _bind_click_fullscreen(root, enter_fullscreen)

    def _fullscreen_when_mapped(_event: tk.Event | None = None) -> None:
        enter_fullscreen()
        root.unbind("<Map>")

    root.bind("<Map>", _fullscreen_when_mapped)
    root.after_idle(enter_fullscreen)
    # First frame before Configure debounce (avoids a blank flash).
    root.after(0, _repaint_all)

    root.mainloop()


if __name__ == "__main__":
    main()
