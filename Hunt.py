import math
import tkinter as tk

def draw_stick_figure(canvas, cx, cy):
    """Draw a simple stick figure with a face, centered at (cx, cy)."""
    # Head (circle)
    head_radius = 25
    head_center_y = cy - 60
    canvas.create_oval(cx - head_radius, head_center_y - head_radius,
                       cx + head_radius, head_center_y + head_radius, width=2)

    # Face: eyes (2 dots)
    eye_y = head_center_y - 8
    dot_r = 2
    canvas.create_oval(cx - 10 - dot_r, eye_y - dot_r, cx - 10 + dot_r, eye_y + dot_r,
                       fill="black", outline="black")  # left eye
    canvas.create_oval(cx + 10 - dot_r, eye_y - dot_r, cx + 10 + dot_r, eye_y + dot_r,
                       fill="black", outline="black")  # right eye

    # Face: mouth (simple smile, a bit higher)
    mouth_y = head_center_y + 4
    canvas.create_arc(cx - 12, mouth_y - 8, cx + 12, mouth_y + 8,
                      start=200, extent=140, style=tk.ARC, width=2)

    # Body (line from neck to waist)
    neck_y = cy - 35
    waist_y = cy + 20
    canvas.create_line(cx, neck_y, cx, waist_y, width=2)

    # Arms (outstretched)
    arm_y = cy - 15
    canvas.create_line(cx - 45, arm_y, cx, arm_y, width=2)  # left arm
    canvas.create_line(cx, arm_y, cx + 45, arm_y, width=2)  # right arm

    # Legs
    canvas.create_line(cx, waist_y, cx - 25, cy + 70, width=2)  # left leg
    canvas.create_line(cx, waist_y, cx + 25, cy + 70, width=2)  # right leg

def draw_lobby(canvas, width, height, money):
    """Draw the main lobby: stick figure, speech bubble, Store and To the wild buttons."""
    center_x, center_y = width // 2, height // 2
    canvas.create_text(24, 24, text=f"Money: ${money}", anchor="nw", font=("Arial", 14), fill="black")
    draw_stick_figure(canvas, center_x, center_y)

    quote = "Did you come to hunt world to hunt?"
    bubble_w, bubble_h = 320, 72
    bx, by = center_x - bubble_w // 2, center_y - 175
    canvas.create_rectangle(bx, by, bx + bubble_w, by + bubble_h,
                            fill="white", outline="black", width=2)
    tail_w = 20
    canvas.create_polygon(
        center_x - tail_w, by + bubble_h,
        center_x + tail_w, by + bubble_h,
        center_x, by + bubble_h + 18,
        fill="white", outline="black", width=2
    )
    canvas.create_text(center_x, by + bubble_h // 2, text=quote, font=("Arial", 14),
                       fill="black", width=280, justify="center")

    btn_y = center_y + 100
    store_w, wild_w, btn_h = 100, 140, 40
    gap = 20
    store_cx = center_x - (store_w + gap + wild_w) // 2 + store_w // 2
    canvas.create_rectangle(
        store_cx - store_w // 2, btn_y - btn_h // 2,
        store_cx + store_w // 2, btn_y + btn_h // 2,
        fill="white", outline="black", width=2, tags=("store_btn",)
    )
    canvas.create_text(store_cx, btn_y, text="Store", font=("Arial", 14), fill="black", tags=("store_btn",))
    wild_cx = center_x + (store_w + gap + wild_w) // 2 - wild_w // 2
    canvas.create_rectangle(
        wild_cx - wild_w // 2, btn_y - btn_h // 2,
        wild_cx + wild_w // 2, btn_y + btn_h // 2,
        fill="white", outline="black", width=2, tags=("wild_btn",)
    )
    canvas.create_text(wild_cx, btn_y, text="To the wild", font=("Arial", 14), fill="black", tags=("wild_btn",))

def draw_store(canvas, width, height):
    """Draw the store screen: stick figure with speech bubble, then Sell for money, Buy, Back to lobby."""
    center_x, center_y = width // 2, height // 2

    # Stick figure on the right, above the buttons
    figure_cx = center_x + 200
    figure_cy = center_y - 180
    draw_stick_figure(canvas, figure_cx, figure_cy)

    # Speech bubble on the left of the stick figure: "Welcome to the store"
    bubble_text = "Welcome to the store"
    bubble_w, bubble_h = 200, 56
    bubble_right = figure_cx - 50  # gap between bubble and figure
    bubble_left = bubble_right - bubble_w
    bubble_top = figure_cy - 100
    canvas.create_rectangle(bubble_left, bubble_top, bubble_right, bubble_top + bubble_h,
                            fill="white", outline="black", width=2)
    # Tail pointing right toward the stick figure
    tail_w = 14
    canvas.create_polygon(
        bubble_right - tail_w, bubble_top + bubble_h,
        bubble_right - tail_w, bubble_top + bubble_h + 22,
        bubble_right, bubble_top + bubble_h // 2,
        fill="white", outline="black", width=2
    )
    canvas.create_text((bubble_left + bubble_right) // 2, bubble_top + bubble_h // 2,
                       text=bubble_text, font=("Arial", 13), fill="black", width=170, justify="center")

    btn_w, btn_h = 180, 44
    gap = 16
    start_y = center_y - 40
    # Sell for money
    canvas.create_rectangle(
        center_x - btn_w // 2, start_y - btn_h // 2,
        center_x + btn_w // 2, start_y + btn_h // 2,
        fill="white", outline="black", width=2, tags=("sell_btn",)
    )
    canvas.create_text(center_x, start_y, text="Sell for money", font=("Arial", 14), fill="black", tags=("sell_btn",))
    # Buy
    start_y += btn_h + gap
    canvas.create_rectangle(
        center_x - btn_w // 2, start_y - btn_h // 2,
        center_x + btn_w // 2, start_y + btn_h // 2,
        fill="white", outline="black", width=2, tags=("buy_btn",)
    )
    canvas.create_text(center_x, start_y, text="Buy", font=("Arial", 14), fill="black", tags=("buy_btn",))
    # Back to lobby
    start_y += btn_h + gap
    canvas.create_rectangle(
        center_x - btn_w // 2, start_y - btn_h // 2,
        center_x + btn_w // 2, start_y + btn_h // 2,
        fill="white", outline="black", width=2, tags=("back_btn",)
    )
    canvas.create_text(center_x, start_y, text="Back to lobby", font=("Arial", 14), fill="black", tags=("back_btn",))

def draw_sell_screen(canvas, width, height):
    """Draw the sell screen: question only (entry and buttons are separate widgets)."""
    center_x, center_y = width // 2, height // 2
    canvas.create_text(center_x, center_y - 140, text="How Much Meat Do You Want To Sell?",
                      font=("Arial", 18), fill="black")
    canvas.create_text(center_x, center_y - 100, text="($1 per meat)", font=("Arial", 12), fill="gray")

def main():
    root = tk.Tk()
    root.title("Hunt")
    root.configure(bg="white")

    # Fullscreen
    root.attributes("-fullscreen", True)
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()

    canvas = tk.Canvas(root, width=width, height=height, bg="white", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    player_money = 0
    sell_overlay_frame = None

    def clear_sell_overlay():
        nonlocal sell_overlay_frame
        if sell_overlay_frame is not None:
            sell_overlay_frame.destroy()
            sell_overlay_frame = None

    def show_lobby(event=None):
        clear_sell_overlay()
        canvas.delete("all")
        draw_lobby(canvas, width, height, player_money)
        canvas.tag_bind("store_btn", "<Button-1>", show_store)
        canvas.tag_bind("wild_btn", "<Button-1>", on_wild)

    def show_store(event=None):
        clear_sell_overlay()
        canvas.delete("all")
        draw_store(canvas, width, height)
        canvas.tag_bind("sell_btn", "<Button-1>", show_sell_screen)
        canvas.tag_bind("buy_btn", "<Button-1>", on_buy)
        canvas.tag_bind("back_btn", "<Button-1>", show_lobby)

    def show_sell_screen(event=None):
        nonlocal sell_overlay_frame, player_money
        clear_sell_overlay()
        canvas.delete("all")
        draw_sell_screen(canvas, width, height)

        sell_overlay_frame = tk.Frame(root, bg="white")
        sell_overlay_frame.place(relx=0.5, rely=0.45, anchor="n")

        meat_var = tk.StringVar()
        entry = tk.Entry(sell_overlay_frame, textvariable=meat_var, font=("Arial", 14), width=12, justify="center")
        entry.pack(pady=(0, 8))

        result_label = tk.Label(sell_overlay_frame, text="", font=("Arial", 13), bg="white", fg="black")
        result_label.pack(pady=(0, 8))

        def do_sell():
            nonlocal player_money
            raw = meat_var.get().strip()
            if not raw:
                result_label.config(text="Type how much meat to sell.")
                return
            try:
                amount = float(raw)
            except ValueError:
                result_label.config(text="Enter a number.")
                return
            if amount < 0:
                result_label.config(text="Use zero or more.")
                return
            if not math.isfinite(amount):
                result_label.config(text="Enter a normal number (not infinity).")
                return
            max_meat = 1_000_000
            if amount > max_meat:
                result_label.config(text=f"Enter at most {max_meat:,} meat.")
                return
            meat_units = int(amount)
            earned = meat_units * 1
            player_money += earned
            result_label.config(
                text=f"You sold {meat_units} meat for ${earned}.\nYou now have ${player_money}."
            )

        tk.Button(sell_overlay_frame, text="Sell", font=("Arial", 12), command=do_sell).pack(pady=(0, 8))
        tk.Button(sell_overlay_frame, text="Back", font=("Arial", 12), command=show_store).pack()

    def on_wild(event):
        pass  # placeholder
    def on_buy(event):
        pass  # placeholder

    show_lobby()

    # Escape key exits fullscreen
    def toggle_fullscreen(event=None):
        root.attributes("-fullscreen", not root.attributes("-fullscreen"))
    root.bind("<Escape>", toggle_fullscreen)

    root.lift()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    root.mainloop()

if __name__ == "__main__":
    main()
