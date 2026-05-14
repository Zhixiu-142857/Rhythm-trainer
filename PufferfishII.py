# This entire code is written by the AI.

import tkinter as tk
import random
import time

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    _PIL_IMPORTED = True
except ImportError:
    _PIL_IMPORTED = False

# Use Pillow for injury overlay etc. only while True; set False when user dismisses missing-Pillow screen
_PIL_AVAILABLE = _PIL_IMPORTED

window = tk.Tk()
window.title("Pufferfish II")
window.configure(bg="aliceblue")
window.attributes("-fullscreen", True)

def _exit_fullscreen(event=None):
    window.attributes("-fullscreen", False)
# bind_all so Escape/F work on Windows when a child widget (e.g. canvas) has focus
window.bind_all("<Escape>", _exit_fullscreen)
window.bind_all("<KeyPress-f>", _exit_fullscreen)

# State: which screen we're on, lobby message, and how many times they've opened announcements
current_screen = "lobby"
lobby_message = "please, go to the announcements."
announcements_visit_count = 0
announcements_phase = "get_out"  # "get_out" then after 0.5s "tip" when lake_visit_count >= 1
announcements_title_fill = "black"  # fades to background during fade-out
money = 0  # you get $5 when you first go to announcements
market_view = "main"  # "main" | "sell" | "buy"
sell_price_per_fish = None  # set when on sell screen with fish (random 1.00--2.00)
hammer_purchased = False
spiky_hammer_purchased = False
stove_purchased = False
show_spiky_hammer_no_money = False  # red "not enough money" message on spiky hammer box
spiky_hammer_no_money_timer_id = None
tried_to_steal_spiky_hammer = False  # if True and you buy stove, you die with steal message
fish_count = 0
space_pressed = False  # True while space is held (for spiky hammer trim on lake)
lake_hurt = False
injured = False  # True when hurt by spiky or no hammer; must buy bandage at market
injury_countdown_timer_id = None  # countdown 5->1 then blood loss death; cancel if they go to market
bypass_announcements_for_market = False  # True when sent to market for bandage; skip "we are not ready yet"
LAKE_CIRCLE_R = 28
lake_timer_id = None  # 20 sec forced return to lobby
lake_timer_end_time = None  # when the 20s return will fire (for unpausing)
lake_spawn_timer_id = None
lake_visit_count = 0  # times previously left the lake (used for spawn interval and spiky delay)
lake_trim_no_money_shown = False  # overlay "not enough money for trimming" on lake; timer paused
lake_trim_spikeless_shown = False  # overlay "don't trim spikeless fish" on lake; timer paused
lake_trim_spikeless_timer_id = None

# Death-related text constants (edit these to change death wording in one place)
STARVATION_LOBBY_TEXT = "Sorry, you have died of starvation. =("
BLOOD_LOSS_DEATH_TEXT = "You have died of blood loss. PLAY AGAIN?"
STEAL_DEATH_TEXT = "You died because you tried to steal. PLAY AGAIN?"
STARVATION_DEATH_TEXT_TEMPLATE = "OH NO! YOU DIED OF STARVATION! YOU SURVIVED UNTIL ROUND {round_num}. WANT TO PLAY AGAIN?"

# Lobby buttons at the bottom
button_frame = tk.Frame(window, bg="aliceblue")
button_frame.pack(side="bottom", pady=20)

def go_to_announcements():
    global current_screen, lobby_message, announcements_visit_count, announcements_phase, money, bypass_announcements_for_market
    current_screen = "announcements"
    announcements_visit_count += 1
    bypass_announcements_for_market = False  # they've been to announcements now
    if announcements_visit_count == 1:
        money = round(money + 5, 2)  # get $5 on first visit ("Here is $5 to get you started")
        update_money_display()
        announcements_phase = "get_out"
    else:
        announcements_phase = "get_out"
        if lake_visit_count >= 1:
            window.after(500, _announcements_show_tip)
    if lobby_message == "please, go to the announcements.":
        lobby_message = "please go to the market."  # next time they see lobby, show this
    button_frame.pack_forget()
    market_frame.pack_forget()
    back_frame.pack(pady=20)
    canvas.delete("all")
    draw_content()

def _announcements_show_tip():
    global announcements_phase, announcements_title_fill
    if current_screen != "announcements" or lake_visit_count < 1:
        return
    announcements_title_fill = "black"
    _announcements_fade_step(0)

def _announcements_fade_step(step):
    global announcements_phase, announcements_title_fill
    if current_screen != "announcements":
        return
    fills = ["black", "gray40", "gray60", "gray80", "aliceblue"]
    if step < len(fills):
        announcements_title_fill = fills[step]
        canvas.delete("all")
        draw_content()
        window.after(80, lambda: _announcements_fade_step(step + 1))
    else:
        announcements_phase = "tip"
        announcements_title_fill = "black"
        canvas.delete("all")
        draw_content()

def go_to_market():
    global current_screen, market_view
    current_screen = "market"
    market_view = "main"
    button_frame.pack_forget()
    back_frame.pack_forget()
    market_sub_buttons.pack_forget()
    market_sell_confirm_frame.pack_forget()
    market_healed_frame.pack_forget()
    market_frame.pack(side="bottom", pady=20)
    market_main_buttons.pack(pady=0)
    # Disable buy/sell if they haven't been to announcements yet (unless bypass for bandage)
    if announcements_visit_count == 0 and not bypass_announcements_for_market:
        market_buy_btn.config(state="disabled")
        market_sell_btn.config(state="disabled")
    else:
        market_buy_btn.config(state="normal")
        market_sell_btn.config(state="normal")
    canvas.delete("all")
    draw_content()

def go_to_lobby(from_lake=False, from_healed=False):
    global current_screen, lake_hurt, lake_timer_id, lake_timer_end_time, lake_spawn_timer_id, lake_visit_count, lobby_message, space_pressed, lake_trim_no_money_shown, lake_trim_spikeless_shown, lake_trim_spikeless_timer_id
    # Stale 20s timer: if we were called with from_lake=True but user already left the lake, ignore
    if from_lake and current_screen != "lake":
        return
    if from_healed:
        # From market "healed" view: go to lobby and show eat state (same rules as returning from lake)
        current_screen = "lobby"
        back_frame.pack_forget()
        market_frame.pack_forget()
        market_healed_frame.pack_forget()
        lake_frame.pack_forget()
        death_frame.pack_forget()
        eat_btn_frame.pack_forget()
        canvas.config(bg="aliceblue")
        canvas.delete("all")
        canvas.unbind("<Button-1>")
        canvas.unbind("<Motion>")
        required = 1 if stove_purchased else 2
        if fish_count < required:
            # No fish to eat after healing — same as lake return: starvation
            lobby_message = STARVATION_LOBBY_TEXT
            button_frame.pack_forget()
            draw_content()
            window.after(2000, show_death_screen)
            return
        lobby_message = "please, eat 1 of your fish" if stove_purchased else "please, eat 2 of your fish"
        eat_btn_frame.pack(pady=10)
        market_btn.config(state="disabled")
        announcements_btn.config(state="disabled")
        lake_btn.config(state="disabled")
        button_frame.pack(side="bottom", pady=20)
        draw_content()
        return
    if current_screen == "announcements" and lake_visit_count >= 1:
        lobby_message = "Now go catch some fish!"
    if current_screen == "lake":
        if lake_timer_id is not None:
            try:
                window.after_cancel(lake_timer_id)
            except tk.TclError:
                pass
            lake_timer_id = None
            lake_timer_end_time = None
        if lake_spawn_timer_id is not None:
            try:
                window.after_cancel(lake_spawn_timer_id)
            except tk.TclError:
                pass
            lake_spawn_timer_id = None
        lake_trim_no_money_shown = False
        lake_trim_spikeless_shown = False
        if lake_trim_spikeless_timer_id is not None:
            try:
                window.after_cancel(lake_trim_spikeless_timer_id)
            except tk.TclError:
                pass
            lake_trim_spikeless_timer_id = None
    current_screen = "lobby"
    lake_hurt = False
    back_frame.pack_forget()
    market_frame.pack_forget()
    lake_frame.pack_forget()
    death_frame.pack_forget()
    eat_btn_frame.pack_forget()
    canvas.config(bg="aliceblue")
    canvas.delete("all")
    canvas.unbind("<Button-1>")
    canvas.unbind("<Motion>")
    try:
        window.unbind("<KeyPress-space>")
        window.unbind("<KeyRelease-space>")
    except tk.TclError:
        pass
    space_pressed = False
    if from_lake:
        required = 1 if stove_purchased else 2
        if fish_count < required:
            lobby_message = STARVATION_LOBBY_TEXT
            button_frame.pack_forget()
            draw_content()
            window.after(2000, show_death_screen)
            return
        else:
            lobby_message = "please, eat 1 of your fish" if stove_purchased else "please, eat 2 of your fish"
            eat_btn_frame.pack(pady=10)
            market_btn.config(state="disabled")
            announcements_btn.config(state="disabled")
            lake_btn.config(state="disabled")
    else:
        market_btn.config(state="normal")
        announcements_btn.config(state="normal")
        lake_btn.config(state="normal")
    button_frame.pack(side="bottom", pady=20)
    draw_content()

def turn_circle_red(circle_id):
    """Turn an orange circle into red (spiky)."""
    try:
        canvas.itemconfig(circle_id, fill="red", tags=("lake_circle", "red"))
    except tk.TclError:
        pass


def spawn_lake_circles(n):
    """Spawn n circles: 3/4 orange (turn red after max(3/(prev_visits+1), 0.5)s), 1/4 red."""
    global lake_visit_count
    canvas.update()
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        return
    r = LAKE_CIRCLE_R
    prev = lake_visit_count  # times previously visited the lake (before this visit)
    spiky_delay_sec = max(3.0 / (prev + 1), 0.5)
    spiky_delay_ms = int(spiky_delay_sec * 1000)
    for _ in range(n):
        x = random.randint(r + 10, max(r + 11, w - r - 10))
        y = random.randint(r + 10, max(r + 11, h - r - 80))
        if random.random() < 0.75:
            color, fill = "orange", "orange"
        else:
            color, fill = "red", "red"
        oval_id = canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline="black", width=2, tags=("lake_circle", color))
        if color == "orange":
            window.after(spiky_delay_ms, lambda oid=oval_id: turn_circle_red(oid))


def lake_spawn_tick():
    """Spawn one fish every [1 - 1/(prev_visits+1)] seconds (min 0.2s)."""
    global lake_spawn_timer_id, lake_visit_count
    if current_screen != "lake":
        return
    prev = lake_visit_count
    interval_sec = 1 - 1.0 / (prev + 1)
    interval_sec = max(interval_sec, 0.2)
    interval_ms = int(interval_sec * 1000)
    spawn_lake_circles(1)
    lake_spawn_timer_id = window.after(interval_ms, lake_spawn_tick)

def on_lake_click(event):
    global fish_count, lake_hurt, money, injured
    if lake_hurt or lake_trim_no_money_shown or lake_trim_spikeless_shown:
        return
    items = canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
    for i in reversed(items):
        tags = canvas.gettags(i)
        if "lake_circle" not in tags:
            continue
        if "red" in tags:
            if space_pressed and spiky_hammer_purchased:
                if money < 0.25:
                    _show_trim_no_money_overlay()
                    return
                # Trim spikes: cost $0.25, turn red back to orange and restart spiky timer
                money = round(money - 0.25, 2)
                update_money_display()
                canvas.itemconfig(i, fill="orange", tags=("lake_circle", "orange"))
                spiky_delay_sec = max(3.0 / (lake_visit_count + 1), 0.5)
                spiky_delay_ms = int(spiky_delay_sec * 1000)
                window.after(spiky_delay_ms, lambda oid=i: turn_circle_red(oid))
                return
            _start_injury_screen("OW! DON'T CATCH SPIKY PUFFERFISH! THEY HURT!")
            return
        if "orange" in tags:
            if space_pressed:
                _show_trim_spikeless_overlay()
                return
            if not hammer_purchased:
                _start_injury_screen("DON'T CATCH FISH WITHOUT A HAMMER!!!")
                return
            fish_count += 1
            update_fish_display()
            canvas.move(i, 0, 80)
            def remove_circle(oid):
                try:
                    canvas.delete(oid)
                except tk.TclError:
                    pass
            window.after(250, lambda oid=i: remove_circle(oid))
            return

def _show_trim_spikeless_overlay():
    global lake_trim_spikeless_shown, lake_timer_id, lake_trim_spikeless_timer_id, money
    if current_screen != "lake":
        return
    if money >= 10:
        money = round(money - 10, 2)
        update_money_display()
    lake_trim_spikeless_shown = True
    if lake_timer_id is not None:
        try:
            window.after_cancel(lake_timer_id)
        except tk.TclError:
            pass
        lake_timer_id = None
    if lake_trim_spikeless_timer_id is not None:
        try:
            window.after_cancel(lake_trim_spikeless_timer_id)
        except tk.TclError:
            pass
    canvas.delete("all")
    canvas.config(bg="orange")
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w > 1 and h > 1:
        canvas.create_text(w // 2, h // 2, text="don't try to trim the spikes off spikeless fish.",
                          font=("Arial", 22, "bold"), fill="black", width=max(1, w - 80), justify="center")
    def _dismiss_trim_spikeless():
        global lake_trim_spikeless_shown, lake_timer_id, lake_trim_spikeless_timer_id
        if not lake_trim_spikeless_shown or current_screen != "lake":
            return
        lake_trim_spikeless_shown = False
        lake_trim_spikeless_timer_id = None
        canvas.delete("all")
        canvas.config(bg="dark blue")
        # Unpause: resume with remaining time, don't restart 20s
        if lake_timer_end_time is not None:
            remaining_sec = max(0.0, lake_timer_end_time - time.time())
            lake_timer_id = window.after(int(remaining_sec * 1000), lambda: go_to_lobby(from_lake=True))
        else:
            lake_timer_id = window.after(20000, lambda: go_to_lobby(from_lake=True))
    lake_trim_spikeless_timer_id = window.after(4000, _dismiss_trim_spikeless)

def _show_trim_no_money_overlay():
    global lake_trim_no_money_shown, lake_timer_id
    if current_screen != "lake":
        return
    lake_trim_no_money_shown = True
    if lake_timer_id is not None:
        try:
            window.after_cancel(lake_timer_id)
        except tk.TclError:
            pass
        lake_timer_id = None
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        return
    cx, cy = w // 2, h // 2
    box_w, box_h = 500, 140
    canvas.create_rectangle(cx - box_w // 2, cy - box_h // 2, cx + box_w // 2, cy + box_h // 2,
                            fill="light blue", outline="black", width=2, tags=("trim_no_money_overlay",))
    canvas.create_text(cx, cy - 25, text="YOU DON'T HAVE ENOUGH MONEY FOR TRIMMING! OH NO!",
                      font=("Arial", 16, "bold"), fill="black", width=box_w - 40, justify="center",
                      tags=("trim_no_money_overlay",))
    canvas.create_text(cx, cy + 25, text="press the space button to continue the game",
                      font=("Arial", 10), fill="black", tags=("trim_no_money_overlay",))

def _dismiss_trim_no_money():
    global lake_trim_no_money_shown, lake_timer_id, lake_timer_end_time
    if not lake_trim_no_money_shown or current_screen != "lake":
        return
    lake_trim_no_money_shown = False
    canvas.delete("trim_no_money_overlay")
    lake_timer_end_time = time.time() + 20
    lake_timer_id = window.after(20000, lambda: go_to_lobby(from_lake=True))

def _on_space_press(event):
    global space_pressed
    if lake_trim_no_money_shown:
        _dismiss_trim_no_money()
        return
    space_pressed = True

def _on_space_release(event):
    global space_pressed
    space_pressed = False

def go_to_lake():
    global current_screen, lake_hurt, lake_timer_id, lake_timer_end_time, lake_spawn_timer_id, space_pressed, fish_count
    # Fish carried from the previous day spoil on lake entry: only one-third remains.
    fish_count = fish_count // 3
    current_screen = "lake"
    lake_hurt = False
    space_pressed = False
    lake_back_btn.config(text="back to lobby", command=lambda: go_to_lobby(from_lake=True))
    button_frame.pack_forget()
    back_frame.pack_forget()
    market_frame.pack_forget()
    lake_frame.pack(side="bottom", pady=20)
    update_fish_display()
    canvas.config(bg="dark blue")
    canvas.delete("all")
    canvas.bind("<Button-1>", on_lake_click)
    window.bind("<KeyPress-space>", _on_space_press)
    window.bind("<KeyRelease-space>", _on_space_release)
    window.after(100, lake_spawn_tick)  # one fish every 0.5 sec
    lake_timer_end_time = time.time() + 20
    lake_timer_id = window.after(20000, lambda: go_to_lobby(from_lake=True))

market_btn = tk.Button(button_frame, text="market", font=("Arial", 14), width=12, command=go_to_market)
market_btn.pack(side="left", padx=10)
announcements_btn = tk.Button(button_frame, text="announcements", font=("Arial", 14), width=12, command=go_to_announcements)
announcements_btn.pack(side="left", padx=10)
lake_btn = tk.Button(button_frame, text="lake", font=("Arial", 14), width=12, command=go_to_lake)
lake_btn.pack(side="left", padx=10)

# Frame for "back to lobby" (hidden initially)
back_frame = tk.Frame(window, bg="aliceblue")
tk.Button(back_frame, text="back to lobby", font=("Arial", 14), width=14, command=go_to_lobby).pack()

# Lake screen: bottom frame and fish count label
lake_frame = tk.Frame(window, bg="aliceblue")
lake_back_btn = tk.Button(lake_frame, text="back to lobby", font=("Arial", 14), width=14, command=lambda: go_to_lobby(from_lake=True))
lake_back_btn.pack()

# Injury countdown: semi-transparent red overlay with transparent number cutout, updates every second
INJURY_RED_COLORS = ["#ffb3b3", "#ff8080", "#ff4d4d", "#cc0000", "#990000"]  # light to dark
INJURY_OVERLAY_ALPHA = 180  # 0-255, semi-transparent red
injury_overlay_photo = None  # keep ref so PhotoImage is not gc'd

def _hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def _make_injury_overlay_photo(w, h, hex_color, number_cutout=None):
    """Create a semi-transparent red rectangle. If number_cutout is set, cut that number out (transparent)."""
    global injury_overlay_photo
    if w <= 0 or h <= 0:
        w, h = 800, 600
    r, g, b = _hex_to_rgb(hex_color)
    img = Image.new("RGBA", (w, h), (r, g, b, INJURY_OVERLAY_ALPHA))
    if number_cutout is not None:
        mask = Image.new("L", (w, h), 255)
        draw_mask = ImageDraw.Draw(mask)
        font = None
        for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "arial.ttf", "Arial.ttf"]:
            try:
                font = ImageFont.truetype(path, 216)
                break
            except (OSError, IOError):
                continue
        if font is None:
            font = ImageFont.load_default()
        num_str = str(number_cutout)
        try:
            bbox = draw_mask.textbbox((0, 0), num_str, font=font)
        except AttributeError:
            try:
                bbox = (0, 0, *draw_mask.textsize(num_str, font=font))
            except AttributeError:
                bbox = (0, 0, 240, 216)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx, ty = (w - tw) // 2, (h - th) // 2
        draw_mask.text((tx, ty), num_str, fill=0, font=font)
        alpha = img.split()[3]
        zero_l = Image.new("L", (w, h), 0)
        new_alpha = Image.composite(zero_l, alpha, mask)
        img.putalpha(new_alpha)
    injury_overlay_photo = ImageTk.PhotoImage(img)
    return injury_overlay_photo

def _draw_injury_overlay(hex_color, number):
    """Draw overlay (red only) and number as separate item: number in front of overlay, behind bandage."""
    w, h = canvas.winfo_width(), canvas.winfo_height()
    if w <= 0 or h <= 0:
        w, h = 800, 600
    cx, cy = w // 2, h // 2
    if not _PIL_AVAILABLE:
        return
    # Overlay: semi-transparent red only (no number cutout)
    photo = _make_injury_overlay_photo(w, h, hex_color, number_cutout=None)
    canvas.delete("injury_overlay")
    canvas.delete("injury_number")
    canvas.create_image(0, 0, anchor="nw", image=photo, tags=("injury_overlay",))
    canvas.tag_lower("injury_overlay")
    # Number: in front of overlay and other buy items, behind bandage only
    canvas.create_text(cx, cy, text=str(number), font=("Arial", 216, "bold"), fill="white", tags=("injury_number",))
    all_ids = list(canvas.find_all())
    bandage_ids = set(canvas.find_withtag("bandage"))
    number_ids = set(canvas.find_withtag("injury_number"))
    bandage_indices = [i for i, id in enumerate(all_ids) if id in bandage_ids]
    number_indices = [i for i, id in enumerate(all_ids) if id in number_ids]
    if bandage_indices and number_indices:
        # Lower number until it sits just below the bandage (so overlay + hammer/spiky/stove are below number)
        min_bandage = min(bandage_indices)
        lowers_needed = min(number_indices) - min_bandage + 1
        for _ in range(max(0, lowers_needed)):
            canvas.tag_lower("injury_number")

def _draw_lake_hurt_message(title_text):
    """Show the injury message screen (title + paragraph). No overlay yet."""
    w, h = canvas.winfo_width(), canvas.winfo_height()
    cx, cy = w // 2, h // 2
    canvas.delete("all")
    canvas.config(bg=INJURY_RED_COLORS[0])
    canvas.create_text(cx, cy - 55, text=title_text, font=("Arial", 24, "bold"), fill="white")
    canvas.create_text(cx, cy, text="you have injured yourself. you will lose blood at an astonishingly fast rate if you don't go to the market to buy a bandage immediately.",
                      font=("Arial", 16, "bold"), fill="white", width=max(1, w - 80), justify="center")

def _draw_injury_no_pil_banner(seconds_left):
    """Without Pillow: only a top line counting down seconds until blood-loss death."""
    canvas.delete("injury_no_pil_banner")
    w = canvas.winfo_width()
    if w <= 0:
        w = 800
    fill = "white" if current_screen == "lake" else "dark red"
    if seconds_left == 1:
        line = "you have 1 second until you die of blood loss"
    else:
        line = f"you have {seconds_left} seconds until you die of blood loss"
    canvas.create_text(
        w // 2,
        55,
        text=line,
        font=("Arial", 16, "bold"),
        fill=fill,
        tags=("injury_no_pil_banner",),
        width=max(200, w - 40),
        justify="center",
    )

def _start_injury_overlay_phase(title_text):
    """Called after the lake_hurt message has been shown. Start the overlay countdown."""
    global injury_countdown_timer_id, injured
    if not injured:
        injury_countdown_timer_id = None
        return
    if _PIL_AVAILABLE:
        _draw_injury_overlay(INJURY_RED_COLORS[0], 5)
    else:
        _draw_injury_no_pil_banner(5)
    injury_countdown_timer_id = window.after(1000, lambda: _injury_countdown_step(1, title_text))

def _start_injury_screen(title_text):
    global lake_hurt, injured, injury_countdown_timer_id
    lake_hurt = True
    injured = True
    if injury_countdown_timer_id is not None:
        try:
            window.after_cancel(injury_countdown_timer_id)
        except tk.TclError:
            pass
    # First: full-screen lake hurt message (title + paragraph) for everyone; then overlay or banner after 1.5s
    _draw_lake_hurt_message(title_text)
    if not _PIL_AVAILABLE:
        canvas.delete("injury_no_pil_banner")
    lake_back_btn.config(text="go to the market to get a bandage", command=_go_to_market_for_bandage)
    injury_countdown_timer_id = window.after(1500, lambda: _start_injury_overlay_phase(title_text))

def _injury_countdown_step(step, title_text):
    global injury_countdown_timer_id, injured
    if not injured:
        injury_countdown_timer_id = None
        canvas.delete("injury_overlay")
        canvas.delete("injury_number")
        canvas.delete("injury_no_pil_banner")
        return
    w, h = canvas.winfo_width(), canvas.winfo_height()
    cx, cy = w // 2, h // 2
    if step >= 5:
        injury_countdown_timer_id = None
        canvas.delete("injury_overlay")
        canvas.delete("injury_number")
        canvas.delete("injury_no_pil_banner")
        show_death_screen(BLOOD_LOSS_DEATH_TEXT)
        return
    color = INJURY_RED_COLORS[min(step, len(INJURY_RED_COLORS) - 1)]
    num = 5 - step
    if _PIL_AVAILABLE:
        _draw_injury_overlay(color, num)
    else:
        _draw_injury_no_pil_banner(num)
    injury_countdown_timer_id = window.after(1000, lambda: _injury_countdown_step(step + 1, title_text))

def _go_to_market_for_bandage():
    """Leave lake (when injured) and go to market to buy a bandage. Timer keeps running at market."""
    global current_screen, lake_timer_id, lake_timer_end_time, lake_spawn_timer_id, lake_trim_spikeless_timer_id, bypass_announcements_for_market
    if current_screen != "lake":
        return
    bypass_announcements_for_market = True  # skip "we are not ready yet" when coming for bandage
    # Do not cancel injury_countdown_timer_id - timer continues at market
    if lake_timer_id is not None:
        try:
            window.after_cancel(lake_timer_id)
        except tk.TclError:
            pass
        lake_timer_id = None
        lake_timer_end_time = None
    if lake_spawn_timer_id is not None:
        try:
            window.after_cancel(lake_spawn_timer_id)
        except tk.TclError:
            pass
        lake_spawn_timer_id = None
    if lake_trim_spikeless_timer_id is not None:
        try:
            window.after_cancel(lake_trim_spikeless_timer_id)
        except tk.TclError:
            pass
        lake_trim_spikeless_timer_id = None
    lake_frame.pack_forget()
    go_to_market()
    show_market_buy()  # bring them directly to the buy screen (bandage)

fish_label = tk.Label(window, text="Fish: 0", font=("Arial", 18, "bold"), bg="white", fg="black", relief="solid", bd=2)
fish_label.place(relx=0, x=20, y=20, anchor="nw")
fish_label.lift()

# Lobby: eat button (when message is "please, eat 2 of your fish")
eat_btn_frame = tk.Frame(window, bg="aliceblue")

def on_eat():
    global fish_count, lobby_message, lake_visit_count
    required = 1 if stove_purchased else 2
    if fish_count >= required:
        fish_count -= required
        lake_visit_count += 1  # round = completed eat; display shows "Round N" after N eats
        lobby_message = "you are supposed to sell your fish at the market, but since you don't have fish to sell, you must go to the announcements." if fish_count == 0 else "go to the market to sell your remaining fish"
        eat_btn_frame.pack_forget()
        market_btn.config(state="normal")
        announcements_btn.config(state="normal")
        lake_btn.config(state="normal")
        canvas.delete("all")
        draw_content()

tk.Button(eat_btn_frame, text="eat", font=("Arial", 14), width=12, command=on_eat).pack()

# Death screen: black + message + play again
death_frame = tk.Frame(window, bg="black")
death_label = tk.Label(death_frame, text="", font=("Arial", 18, "bold"), fg="white", bg="black", wraplength=500, justify="center")
death_label.pack(pady=80, padx=40)

def show_death_screen(custom_message=None):
    global current_screen
    current_screen = "death"
    button_frame.pack_forget()
    market_frame.pack_forget()
    lake_frame.pack_forget()
    canvas.pack_forget()  # hide canvas so death frame gets the full area
    death_text = custom_message if custom_message is not None else STARVATION_DEATH_TEXT_TEMPLATE.format(round_num=lake_visit_count)
    death_label.config(text=death_text)
    death_frame.pack(fill="both", expand=True)
    death_frame.update_idletasks()
    window.update_idletasks()

def play_again():
    global current_screen, lobby_message, announcements_visit_count, money, market_view, hammer_purchased, spiky_hammer_purchased, stove_purchased, show_spiky_hammer_no_money, spiky_hammer_no_money_timer_id, tried_to_steal_spiky_hammer, fish_count, lake_visit_count, lake_trim_no_money_shown, lake_trim_spikeless_shown, lake_trim_spikeless_timer_id, injured, injury_countdown_timer_id, bypass_announcements_for_market
    current_screen = "lobby"
    lobby_message = "please, go to the announcements."
    announcements_visit_count = 0
    money = 0
    market_view = "main"
    hammer_purchased = False
    spiky_hammer_purchased = False
    stove_purchased = False
    show_spiky_hammer_no_money = False
    tried_to_steal_spiky_hammer = False
    injured = False
    bypass_announcements_for_market = False
    lake_trim_no_money_shown = False
    lake_trim_spikeless_shown = False
    if injury_countdown_timer_id is not None:
        try:
            window.after_cancel(injury_countdown_timer_id)
        except tk.TclError:
            pass
        injury_countdown_timer_id = None
    if lake_trim_spikeless_timer_id is not None:
        try:
            window.after_cancel(lake_trim_spikeless_timer_id)
        except tk.TclError:
            pass
        lake_trim_spikeless_timer_id = None
    if spiky_hammer_no_money_timer_id is not None:
        try:
            window.after_cancel(spiky_hammer_no_money_timer_id)
        except tk.TclError:
            pass
        spiky_hammer_no_money_timer_id = None
    fish_count = 0
    lake_visit_count = 0
    death_frame.pack_forget()
    eat_btn_frame.pack_forget()
    market_btn.config(state="normal")
    announcements_btn.config(state="normal")
    lake_btn.config(state="normal")
    button_frame.pack(side="bottom", pady=20)
    canvas.config(bg="aliceblue")
    canvas.delete("all")
    canvas.pack(fill="both", expand=True)  # restore canvas after death screen
    update_money_display()
    draw_content()

tk.Button(death_frame, text="play again", font=("Arial", 18, "bold"), command=play_again).pack(pady=30)

def show_market_sell():
    global market_view, sell_price_per_fish
    market_view = "sell"
    market_main_buttons.pack_forget()
    market_sub_buttons.pack(pady=0)
    if fish_count > 0:
        sell_price_per_fish = round(random.randint(100, 200) / 100.0, 2)
        sell_count_var.set(1)
        sell_count_spinbox.config(to=max(1, fish_count))
        market_sell_confirm_frame.pack(pady=5)
    else:
        sell_price_per_fish = None
        market_sell_confirm_frame.pack_forget()
    canvas.delete("all")
    draw_content()

def show_market_buy():
    global market_view
    market_view = "buy"
    market_main_buttons.pack_forget()
    if injured:
        market_sub_buttons.pack_forget()  # no back to market / back to lobby when injured
    else:
        market_sub_buttons.pack(pady=0)
    canvas.delete("all")
    draw_content()

def go_back_to_market():
    global market_view, show_spiky_hammer_no_money, spiky_hammer_no_money_timer_id
    market_view = "main"
    show_spiky_hammer_no_money = False
    if spiky_hammer_no_money_timer_id is not None:
        try:
            window.after_cancel(spiky_hammer_no_money_timer_id)
        except tk.TclError:
            pass
        spiky_hammer_no_money_timer_id = None
    market_sub_buttons.pack_forget()
    market_sell_confirm_frame.pack_forget()
    market_healed_frame.pack_forget()
    market_main_buttons.pack(side="left", padx=10)
    canvas.delete("all")
    draw_content()

def on_sell_fish():
    global money, fish_count, sell_price_per_fish, market_view, lobby_message
    if fish_count > 0 and sell_price_per_fish is not None:
        try:
            n = int(sell_count_var.get())
        except (ValueError, tk.TclError):
            n = 1
        n = max(1, min(n, fish_count))
        money = round(money + sell_price_per_fish * n, 2)
        fish_count -= n
        sell_price_per_fish = None
        lobby_message = "Now go catch some fish!" if lake_visit_count >= 2 else "go to the announcements now"
        market_sell_confirm_frame.pack_forget()
        update_money_display()
        update_fish_display()
        market_view = "sell_thanks"
        canvas.delete("all")
        draw_content()

def update_money_display():
    money_label.config(text=f"You have ${round(money, 2):.2f}")
    money_label.lift()

def update_fish_display():
    fish_label.config(text=f"Fish: {fish_count}")
    fish_label.lift()

def update_round_display():
    round_label.config(text=f"Round {lake_visit_count}")
    round_label.lift()

def on_hammer_click(event):
    global money, hammer_purchased
    if money >= 5 and not hammer_purchased:
        money = round(money - 5, 2)
        hammer_purchased = True
        update_money_display()
        canvas.delete("all")
        draw_content()

def _clear_spiky_hammer_no_money():
    global show_spiky_hammer_no_money, spiky_hammer_no_money_timer_id
    show_spiky_hammer_no_money = False
    spiky_hammer_no_money_timer_id = None
    if current_screen == "market" and market_view == "buy":
        canvas.delete("all")
        draw_content()

def on_spiky_hammer_click(event):
    global money, spiky_hammer_purchased, show_spiky_hammer_no_money, spiky_hammer_no_money_timer_id, tried_to_steal_spiky_hammer
    if money >= 30 and not spiky_hammer_purchased:
        money = round(money - 30, 2)
        spiky_hammer_purchased = True
        update_money_display()
        canvas.delete("all")
        draw_content()
        return
    if not spiky_hammer_purchased and money < 30:
        tried_to_steal_spiky_hammer = True
        if spiky_hammer_no_money_timer_id is not None:
            try:
                window.after_cancel(spiky_hammer_no_money_timer_id)
            except tk.TclError:
                pass
        show_spiky_hammer_no_money = True
        spiky_hammer_no_money_timer_id = window.after(4000, _clear_spiky_hammer_no_money)
        canvas.delete("all")
        draw_content()

def on_stove_click(event):
    global money, stove_purchased, tried_to_steal_spiky_hammer
    if money >= 30 and not stove_purchased and spiky_hammer_purchased:
        money = round(money - 30, 2)
        stove_purchased = True
        update_money_display()
        canvas.delete("all")
        draw_content()
        return
    if money < 30 and not stove_purchased and tried_to_steal_spiky_hammer:
        window.after(0, lambda: show_death_screen(STEAL_DEATH_TEXT))

def on_bandage_click(event):
    global money, injured, market_view
    if injured and money >= 10:
        money = round(money - 10, 2)
        injured = False
        update_money_display()
        market_view = "healed"
        market_main_buttons.pack_forget()
        market_sub_buttons.pack_forget()
        market_sell_confirm_frame.pack_forget()
        market_healed_frame.pack(pady=10)
        canvas.delete("all")
        draw_content()

# Frame for market bottom: two rows we swap (main = buy/sell/lobby; sub = back to market / back to lobby)
market_frame = tk.Frame(window, bg="aliceblue")
market_main_buttons = tk.Frame(market_frame, bg="aliceblue")
market_buy_btn = tk.Button(market_main_buttons, text="buy", font=("Arial", 14), width=12, command=show_market_buy)
market_buy_btn.pack(side="left", padx=10)
market_sell_btn = tk.Button(market_main_buttons, text="sell", font=("Arial", 14), width=12, command=show_market_sell)
market_sell_btn.pack(side="left", padx=10)
tk.Button(market_main_buttons, text="back to lobby", font=("Arial", 14), width=14, command=go_to_lobby).pack(side="left", padx=10)
market_sub_buttons = tk.Frame(market_frame, bg="aliceblue")
tk.Button(market_sub_buttons, text="back to market", font=("Arial", 14), width=14, command=go_back_to_market).pack(side="left", padx=10)
tk.Button(market_sub_buttons, text="back to lobby", font=("Arial", 14), width=14, command=go_to_lobby).pack(side="left", padx=10)
market_sell_confirm_frame = tk.Frame(market_frame, bg="aliceblue")
sell_count_var = tk.IntVar(value=1)
sell_count_spinbox = tk.Spinbox(market_sell_confirm_frame, from_=1, to=99, width=5, textvariable=sell_count_var, font=("Arial", 14))
sell_count_spinbox.pack(side="left", padx=5, pady=5)
tk.Label(market_sell_confirm_frame, text="fish to sell", font=("Arial", 14), bg="aliceblue").pack(side="left", padx=2)
tk.Button(market_sell_confirm_frame, text="Sell", font=("Arial", 14), width=12, command=on_sell_fish).pack(side="left", padx=5)
market_healed_frame = tk.Frame(market_frame, bg="aliceblue")
tk.Button(market_healed_frame, text="go to lobby", font=("Arial", 14), width=14, command=lambda: go_to_lobby(from_healed=True)).pack(pady=10)
# When market is first shown, main buttons are visible (pack in go_to_market)

# Money display in top-right corner (lifted above canvas so it's visible)
money_label = tk.Label(window, text=f"You have ${round(money, 2):.2f}", font=("Arial", 18, "bold"), bg="white", fg="black", relief="solid", bd=2)
money_label.place(relx=1, x=-20, y=20, anchor="ne")
money_label.lift()

# Round display at top center (always visible)
round_label = tk.Label(window, text="Round 0", font=("Arial", 18, "bold"), bg="white", fg="black", relief="solid", bd=2)
round_label.place(relx=0.5, y=20, anchor="n")
round_label.lift()

# Canvas for stick figure and speech bubble (fills remaining space)
canvas = tk.Canvas(window, bg="aliceblue", highlightthickness=0)
canvas.pack(fill="both", expand=True)


def draw_stick_figure(cx, head_top, head_r, scale, face_scale=1, frown=False):
    """Draw a stick figure. head_top, head_r in same units; scale multiplies body/arms/legs."""
    neck_y = head_top + 2 * head_r
    torso_len = 45 * scale
    arm_len = 28 * scale
    leg_len = 35 * scale
    foot_span = 22 * scale
    torso_bottom = neck_y + torso_len
    feet_y = torso_bottom + leg_len

    canvas.create_oval(cx - head_r, head_top, cx + head_r, neck_y, outline="black", width=max(2, int(2 * scale)))
    head_cy = (head_top + neck_y) // 2
    face_cy = head_cy - 6 * face_scale
    eye_y0, eye_y1 = face_cy - 5 * face_scale, face_cy + 5 * face_scale
    lw = max(2, int(2 * scale))
    canvas.create_line(cx - 7 * face_scale, eye_y0, cx - 7 * face_scale, eye_y1, fill="black", width=lw)
    canvas.create_line(cx + 7 * face_scale, eye_y0, cx + 7 * face_scale, eye_y1, fill="black", width=lw)
    mouth_y = face_cy + (12 if frown else 8) * face_scale  # frown drawn lower
    mouth_w, mouth_h = 10, 4  # slightly smaller mouth
    if scale > 1:
        mouth_w, mouth_h = mouth_w * face_scale, mouth_h * face_scale
    # smile: bottom arc (start=180, extent=180); frown: top arc (start=0, extent=180)
    mouth_start, mouth_extent = (0, 180) if frown else (180, 180)
    canvas.create_arc(cx - mouth_w, mouth_y - mouth_h, cx + mouth_w, mouth_y + mouth_h,
                     start=mouth_start, extent=mouth_extent, style=tk.ARC, outline="black", width=lw)

    canvas.create_line(cx, neck_y, cx, torso_bottom, fill="black", width=lw)
    canvas.create_line(cx, neck_y + 20 * scale, cx - arm_len, neck_y + 5 * scale, fill="black", width=lw)
    canvas.create_line(cx, neck_y + 20 * scale, cx + arm_len, neck_y + 5 * scale, fill="black", width=lw)
    canvas.create_line(cx, torso_bottom, cx - foot_span, feet_y, fill="black", width=lw)
    canvas.create_line(cx, torso_bottom, cx + foot_span, feet_y, fill="black", width=lw)
    return feet_y


def draw_content():
    if current_screen == "death":
        return
    update_money_display()
    update_fish_display()
    update_round_display()
    canvas.update()
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        window.after(10, draw_content)
        return
    cx = w // 2

    if current_screen == "announcements":
        ann_top = 40  # offset so content clears "Round #" at top
        first_visit = announcements_visit_count == 1
        if first_visit:
            title = "WELCOME TO ANNOUNCEMENTS! YOU ARE IN THE RIGHT PLACE!"
            speech = "Welcome to pufferfishtown. Here, we fish. Here is $5 to get you started. Now go to the market for more information."
        else:
            title = "SORRY, BUT YOU ARE NOT SUPPOSED TO BE HERE RIGHT NOW"
            if lake_visit_count >= 1 and announcements_phase == "tip":
                speech = "Well, now you know how the game works, right? (Catch pufferfish with a hammer by clicking them, trim spikes with a spiky hammer by presing fish, and eat fish every round or else you will die of starvation) Try to survive the most rounds without dying!"
            else:
                speech = "get out of here now!"

        if not (announcements_phase == "tip" and lake_visit_count >= 1):
            canvas.create_text(cx, 50 + ann_top, text=title,
                              font=("Arial", 22, "bold"), fill=announcements_title_fill)

        # Massive stick figure with speech bubble
        scale = 3.5
        head_r = 18 * scale
        if first_visit:
            bubble_w, bubble_h = 440, 130
        elif announcements_phase == "tip":
            bubble_w, bubble_h = 480, 100
        else:
            bubble_w, bubble_h = 320, 85
        rect_top = 180 + ann_top
        rect_bottom = rect_top + bubble_h
        tip_y = rect_bottom + 28

        canvas.create_rectangle(cx - bubble_w // 2, rect_top, cx + bubble_w // 2, rect_bottom,
                                fill="white", outline="black", width=3)
        canvas.create_polygon(cx - 25, rect_bottom, cx + 25, rect_bottom, cx, tip_y,
                             fill="white", outline="black", width=3)
        canvas.create_text(cx, (rect_top + rect_bottom) // 2, text=speech,
                          font=("Arial", 15), fill="black", width=bubble_w - 50)

        gap = 35
        head_top = tip_y + gap
        announcements_frown = not first_visit and announcements_phase != "tip"
        draw_stick_figure(cx, head_top, head_r, scale, face_scale=scale, frown=announcements_frown)
        return

    if current_screen == "market":
        market_top = 40  # offset so content clears "Round #" at top
        canvas.create_text(cx, 50 + market_top, text="WELCOME TO THE MARKET!",
                          font=("Arial", 22, "bold"), fill="black")

        if market_view == "healed":
            canvas.create_text(cx, 180 + market_top, text="you're healed! go to the lobby and eat your fish.",
                              font=("Arial", 20, "bold"), fill="black", width=400, justify="center")
            return

        if market_view == "sell_thanks":
            speech = "thank you for selling your fish!"
            scale = 3.5
            head_r = 18 * scale
            bubble_w, bubble_h = 420, 85
            rect_top = 180 + market_top
            rect_bottom = rect_top + bubble_h
            tip_y = rect_bottom + 28
            canvas.create_rectangle(cx - bubble_w // 2, rect_top, cx + bubble_w // 2, rect_bottom,
                                    fill="white", outline="black", width=3)
            canvas.create_polygon(cx - 25, rect_bottom, cx + 25, rect_bottom, cx, tip_y,
                                 fill="white", outline="black", width=3)
            canvas.create_text(cx, (rect_top + rect_bottom) // 2, text=speech,
                              font=("Arial", 16), fill="black", width=bubble_w - 40)
            gap = 35
            head_top = tip_y + gap
            draw_stick_figure(cx, head_top, head_r, scale, face_scale=scale, frown=False)
            return

        if market_view == "sell":
            if fish_count > 0 and sell_price_per_fish is not None:
                speech = f"sell fish for {sell_price_per_fish:.2f} dollars each?"
                frown = False
            else:
                speech = "sorry, you have no fish right now, so get out"
                frown = True
            scale = 3.5
            head_r = 18 * scale
            bubble_w, bubble_h = 420, 85
            rect_top = 180 + market_top
            rect_bottom = rect_top + bubble_h
            tip_y = rect_bottom + 28
            canvas.create_rectangle(cx - bubble_w // 2, rect_top, cx + bubble_w // 2, rect_bottom,
                                    fill="white", outline="black", width=3)
            canvas.create_polygon(cx - 25, rect_bottom, cx + 25, rect_bottom, cx, tip_y,
                                 fill="white", outline="black", width=3)
            canvas.create_text(cx, (rect_top + rect_bottom) // 2, text=speech,
                              font=("Arial", 15), fill="black", width=bubble_w - 50)
            gap = 35
            head_top = tip_y + gap
            draw_stick_figure(cx, head_top, head_r, scale, face_scale=scale, frown=frown)
            return

        if market_view == "buy":
            if hammer_purchased and spiky_hammer_purchased and stove_purchased:
                # Stick figure that "pops out" saying go to the lake (only when everything is bought)
                speech = "go to the lake now to catch some fish"
                scale = 3.5
                head_r = 18 * scale
                bubble_w, bubble_h = 420, 85
                rect_top = 180 + market_top
                rect_bottom = rect_top + bubble_h
                tip_y = rect_bottom + 28
                canvas.create_rectangle(cx - bubble_w // 2, rect_top, cx + bubble_w // 2, rect_bottom,
                                        fill="white", outline="black", width=3)
                canvas.create_polygon(cx - 25, rect_bottom, cx + 25, rect_bottom, cx, tip_y,
                                     fill="white", outline="black", width=3)
                canvas.create_text(cx, (rect_top + rect_bottom) // 2, text=speech,
                                  font=("Arial", 15), fill="black", width=bubble_w - 50)
                gap = 35
                head_top = tip_y + gap
                draw_stick_figure(cx, head_top, head_r, scale, face_scale=scale)
            else:
                sq_size = 120
                sq_y0 = 180 + market_top
                # Left item: hammer $5
                left_cx = cx - 180
                if not hammer_purchased:
                    sq_x0 = left_cx - sq_size // 2
                    canvas.create_rectangle(sq_x0, sq_y0, sq_x0 + sq_size, sq_y0 + sq_size,
                                            fill="aliceblue", outline="", tags=("hammer",))
                    canvas.create_rectangle(sq_x0, sq_y0, sq_x0 + sq_size, sq_y0 + sq_size,
                                            outline="black", width=2)
                    handle_w, handle_h = 18, 50
                    handle_x = left_cx - handle_w // 2
                    handle_y = sq_y0 + (sq_size - handle_h) // 2
                    canvas.create_rectangle(handle_x, handle_y, handle_x + handle_w, handle_y + handle_h,
                                           outline="black", width=2)
                    head_y = handle_y + 8
                    head_left = handle_x - 25
                    head_right = handle_x + handle_w + 25
                    canvas.create_line(head_left, head_y, head_right, head_y, fill="black", width=4)
                    canvas.create_text(left_cx, sq_y0 + sq_size + 30, text="hammer; $5 (click to buy)",
                                      font=("Arial", 14), fill="black")
                    canvas.tag_bind("hammer", "<Button-1>", on_hammer_click)
                # Center item: spiky hammer $30
                center_cx = cx
                if not spiky_hammer_purchased:
                    sq_x0 = center_cx - sq_size // 2
                    canvas.create_rectangle(sq_x0, sq_y0, sq_x0 + sq_size, sq_y0 + sq_size,
                                            fill="aliceblue", outline="", tags=("spiky_hammer",))
                    canvas.create_rectangle(sq_x0, sq_y0, sq_x0 + sq_size, sq_y0 + sq_size,
                                            outline="black", width=2)
                    handle_w, handle_h = 18, 50
                    handle_x = center_cx - handle_w // 2
                    handle_y = sq_y0 + (sq_size - handle_h) // 2
                    canvas.create_rectangle(handle_x, handle_y, handle_x + handle_w, handle_y + handle_h,
                                           outline="black", width=2)
                    head_y = handle_y + 8
                    head_left = handle_x - 25
                    head_right = handle_x + handle_w + 25
                    canvas.create_line(head_left, head_y, head_right, head_y, fill="black", width=4)
                    for dy in (-4, 0, 4):
                        canvas.create_line(head_left + 10, head_y + dy, head_left + 20, head_y + dy + 5, fill="black", width=2)
                        canvas.create_line(head_right - 20, head_y + dy + 5, head_right - 10, head_y + dy, fill="black", width=2)
                    canvas.create_text(center_cx, sq_y0 + sq_size + 30, text="spiky hammer; $30 (click to buy)",
                                      font=("Arial", 12), fill="black")
                    canvas.tag_bind("spiky_hammer", "<Button-1>", on_spiky_hammer_click)
                    if show_spiky_hammer_no_money:
                        msg = "You don't have enough money to buy this, and don't try to steal!"
                        canvas.create_rectangle(sq_x0, sq_y0, sq_x0 + sq_size, sq_y0 + sq_size,
                                                fill="red", outline="dark red", width=3)
                        canvas.create_text(center_cx, sq_y0 + sq_size // 2, text=msg,
                                          font=("Arial", 11, "bold"), fill="white", width=sq_size - 16, justify="center")
                # Right item: stove $30 (circle in triangle in circle, or X if spiky hammer not bought)
                stove_cx = cx + 180
                if not stove_purchased:
                    sq_x0 = stove_cx - sq_size // 2
                    canvas.create_rectangle(sq_x0, sq_y0, sq_x0 + sq_size, sq_y0 + sq_size,
                                            fill="aliceblue", outline="", tags=("stove",))
                    canvas.create_rectangle(sq_x0, sq_y0, sq_x0 + sq_size, sq_y0 + sq_size,
                                            outline="black", width=2)
                    if spiky_hammer_purchased:
                        scx, scy = stove_cx, sq_y0 + sq_size // 2
                        R = 45
                        canvas.create_oval(scx - R, scy - R, scx + R, scy + R, outline="black", width=2, tags=("stove",))
                        cos30 = 3 ** 0.5 / 2
                        tx1, ty1 = scx, scy - R
                        tx2, ty2 = scx - R * cos30, scy + R * 0.5
                        tx3, ty3 = scx + R * cos30, scy + R * 0.5
                        canvas.create_polygon(tx1, ty1, tx2, ty2, tx3, ty3, outline="black", width=2, fill="", tags=("stove",))
                        r_inner = R * 0.5
                        canvas.create_oval(scx - r_inner, scy - r_inner, scx + r_inner, scy + r_inner, outline="black", width=2, tags=("stove",))
                    else:
                        # X in the box when spiky hammer not purchased yet
                        margin = 25
                        canvas.create_line(sq_x0 + margin, sq_y0 + margin, sq_x0 + sq_size - margin, sq_y0 + sq_size - margin, fill="black", width=4, tags=("stove",))
                        canvas.create_line(sq_x0 + sq_size - margin, sq_y0 + margin, sq_x0 + margin, sq_y0 + sq_size - margin, fill="black", width=4, tags=("stove",))
                    canvas.create_text(stove_cx, sq_y0 + sq_size + 30, text="stove; $30 (click to buy)",
                                      font=("Arial", 14), fill="black")
                    canvas.tag_bind("stove", "<Button-1>", on_stove_click)
                # Bandage (only when injured): right side so it doesn't block the center countdown number
                if injured:
                    bandage_y0 = sq_y0 + sq_size + 60
                    bandage_cx = cx + 280
                    sq_x0_b = bandage_cx - sq_size // 2
                    canvas.create_rectangle(sq_x0_b, bandage_y0, sq_x0_b + sq_size, bandage_y0 + sq_size,
                                            fill="lightyellow", outline="", tags=("bandage",))
                    canvas.create_rectangle(sq_x0_b, bandage_y0, sq_x0_b + sq_size, bandage_y0 + sq_size,
                                            outline="black", width=2)
                    # Simple bandage shape: horizontal strip with X
                    by_cy = bandage_y0 + sq_size // 2
                    canvas.create_rectangle(sq_x0_b + 25, by_cy - 15, sq_x0_b + sq_size - 25, by_cy + 15,
                                            outline="brown", width=2, fill="white", tags=("bandage",))
                    canvas.create_line(sq_x0_b + 35, by_cy - 8, sq_x0_b + sq_size - 35, by_cy + 8, fill="red", width=2, tags=("bandage",))
                    canvas.create_line(sq_x0_b + 35, by_cy + 8, sq_x0_b + sq_size - 35, by_cy - 8, fill="red", width=2, tags=("bandage",))
                    canvas.create_text(bandage_cx, bandage_y0 + sq_size + 30, text="bandage; $10 (click to buy)",
                                      font=("Arial", 14), fill="black")
                    canvas.tag_bind("bandage", "<Button-1>", on_bandage_click)
            return

        # market_view == "main"
        if announcements_visit_count == 0 and not bypass_announcements_for_market:
            speech = "go over to the announcements! we are not ready yet!"
            bubble_w, bubble_h = 420, 85
        else:
            speech = "do you want to buy ... or sell?"
            bubble_w, bubble_h = 360, 85
        scale = 3.5
        head_r = 18 * scale
        rect_top = 180 + market_top
        rect_bottom = rect_top + bubble_h
        tip_y = rect_bottom + 28
        canvas.create_rectangle(cx - bubble_w // 2, rect_top, cx + bubble_w // 2, rect_bottom,
                                fill="white", outline="black", width=3)
        canvas.create_polygon(cx - 25, rect_bottom, cx + 25, rect_bottom, cx, tip_y,
                             fill="white", outline="black", width=3)
        canvas.create_text(cx, (rect_top + rect_bottom) // 2, text=speech,
                          font=("Arial", 15), fill="black", width=bubble_w - 50)
        gap = 35
        head_top = tip_y + gap
        draw_stick_figure(cx, head_top, head_r, scale, face_scale=scale)
        return

    # --- Lobby ---
    if lobby_message in ("please, eat 1 of your fish", "please, eat 2 of your fish", "go to the market to sell your remaining fish", "you are supposed to sell your fish at the market, but since you don't have fish to sell, you must go to the announcements.", STARVATION_LOBBY_TEXT, "go to the announcements now", "Now go catch some fish!"):
        lobby_text = lobby_message
    elif hammer_purchased:
        lobby_text = "go over to the lake, where there are some pufferfish for you to catch"
    else:
        lobby_text = lobby_message
    bubble_w = max(220, min(420, len(lobby_text) * 9))
    bubble_h = 65 if len(lobby_text) > 45 else 55
    rect_top = h * 35 // 100
    rect_bottom = rect_top + bubble_h

    canvas.create_rectangle(
        cx - bubble_w // 2, rect_top,
        cx + bubble_w // 2, rect_bottom,
        fill="white", outline="black", width=2
    )
    tip_y = rect_bottom + 22
    canvas.create_polygon(
        cx - 15, rect_bottom,
        cx + 15, rect_bottom,
        cx, tip_y,
        fill="white", outline="black", width=2
    )
    canvas.create_text(cx, (rect_top + rect_bottom) // 2 - 2,
                      text=lobby_text, font=("Arial", 12), fill="black", width=bubble_w - 30)

    gap = 28
    head_top = tip_y + gap
    head_r = 18
    draw_stick_figure(cx, head_top, head_r, 1, face_scale=1)


def _dismiss_pillow_warning():
    global _PIL_AVAILABLE
    _PIL_AVAILABLE = False  # user chose to continue without Pillow; do not treat as available
    try:
        pillow_warning_frame.destroy()
    except tk.TclError:
        pass
    window.after(50, draw_content)


_PILLOW_WARNING_TEXT = (
    'YOU DID NOT INSTALL PILLOW. (you can install it by entering "pip3 install Pillow" into the '
    'terminal and wait until it says "Successfully installed Pillow".) CONTINUE EVEN WITHOUT IT? '
    "GRAPHICS MAY BECOME WORSE."
)

if not _PIL_IMPORTED:
    pillow_warning_frame = tk.Frame(window, bg="black")
    pillow_warning_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    tk.Label(
        pillow_warning_frame,
        text=_PILLOW_WARNING_TEXT,
        font=("Arial", 16),
        fg="white",
        bg="black",
        wraplength=900,
        justify="center",
    ).pack(expand=True, padx=40, pady=40)
    tk.Button(
        pillow_warning_frame,
        text="continue",
        font=("Arial", 18, "bold"),
        command=_dismiss_pillow_warning,
    ).pack(pady=(0, 60))
    pillow_warning_frame.lift()

window.after(50, draw_content)

window.mainloop()
