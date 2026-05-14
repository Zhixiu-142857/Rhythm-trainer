# The entire code is written by the AI.

import json
import math
import random
import secrets
import tkinter as tk
from tkinter import messagebox

# Defaults; overridden by mode selection (two player or four player)
ROWS = 8
COLS = 8
TOTAL = 27  # two player: 27 territories in 8x8 (12+15)
NUM_CAPITALS = 4
REMOVED_COUNT = 37  # 64 - 27
COLORS = ["#e74c3c", "#3498db"]  # red, blue
COLOR_NAMES = ["Red", "Blue"]
CARD_TYPES = ["CANNON", "HORSE", "INFANTRY"]
PIECE_SIZE = 0.7  # piece radius as fraction of half the smaller cell dimension (0–1)
CONTINENT_BORDER_COLORS = ["#f1c40f", "#e67e22", "#9b59b6", "#1abc9c", "#e91e63", "#795548", "#00bcd4", "#8bc34a"]  # 8 for 4-player; no red/blue

# Territory name blocks: C = consonant or blend, V = vowel or 2-vowel (y = vowel)
CONSONANTS_SINGLE = list("bcdfghjklmnpqrstvwxz")
CONSONANT_BLENDS = ["br", "ch", "ck", "gr", "pr", "ph", "qu", "sr", "sh", "wh", "tr"]
VOWELS = ["a", "e", "i", "o", "u", "y"]
VOWEL_PAIRS = ["aa", "ae", "ai", "ao", "au", "ay", "ea", "ee", "ei", "eo", "eu", "ey", "ia", "ie", "ii", "io", "iu",
               "oa", "oe", "oi", "oo", "ou", "oy", "ui", "ya", "ye", "yo", "yu"]


def _pick_c():
    """C = any single consonant or blend."""
    return random.choice(CONSONANTS_SINGLE + CONSONANT_BLENDS)


def _pick_c_final():
    """Final C in CVC = single consonant only."""
    return random.choice(CONSONANTS_SINGLE)


def _pick_v():
    """V = any vowel or 2-vowel combination."""
    return random.choice(VOWELS + VOWELS + VOWEL_PAIRS)


def _generate_block():
    """One block: CV or CVC with equal probability."""
    c, v = _pick_c(), _pick_v()
    if random.random() < 0.5:
        return c + v
    else:
        return c + v + _pick_c_final()


def generate_territory_name():
    """Name with 1, 2, or 3 blocks (equal probability)."""
    n_blocks = random.choice([1, 2, 3])
    s = "".join(_generate_block() for _ in range(n_blocks))
    return s.capitalize()


def make_territory_names():
    """Return a list of TOTAL unique territory names."""
    seen = set()
    out = []
    while len(out) < TOTAL:
        name = generate_territory_name()
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def get_bonus_armies(turn_in_index):
    """Armies for turning in a set. First time in game = 4, second = 6, ... seventh+ = 16."""
    return [4, 6, 8, 10, 12, 14, 16][min(turn_in_index, 6)]


def has_valid_set(cards):
    """If player has 3 same or 1 of each type, return (True, list of 3 cards to remove). Else (False, None)."""
    from collections import Counter
    c = Counter(cards)
    if len(cards) < 3:
        return False, None
    if c.get("CANNON", 0) >= 1 and c.get("HORSE", 0) >= 1 and c.get("INFANTRY", 0) >= 1:
        return True, ["CANNON", "HORSE", "INFANTRY"]
    for t in CARD_TYPES:
        if c.get(t, 0) >= 3:
            return True, [t, t, t]
    return False, None


def remove_set_from_hand(hand, to_remove):
    """Remove one of each card in to_remove from hand (in place)."""
    for card in to_remove:
        hand.remove(card)


def armies_per_turn(canvas, player_index):
    """Armies received at start of turn: floor(territories_owned / 3) + continent bonuses (full continent = floor(size/2))."""
    assignment = canvas.assignment
    continents = canvas.continents
    color = COLORS[player_index]
    territories_owned = sum(1 for c in assignment if c == color)
    base = territories_owned // 3
    from collections import defaultdict
    size_per_continent = defaultdict(int)
    owned_per_continent = defaultdict(int)
    for i in range(TOTAL):
        cid = continents[i]
        size_per_continent[cid] += 1
        if assignment[i] == color:
            owned_per_continent[cid] += 1
    bonus = 0
    for cid, size in size_per_continent.items():
        if owned_per_continent[cid] == size and size > 0:
            bonus += size // 2
    return base + bonus


def advance_to_next_player(canvas, turn_label):
    """Switch to next player (skip eliminated). Place phase or attack phase, update label and End turn button."""
    canvas.move_source = None
    canvas.move_targets = set()
    num_players = len(COLORS)
    eliminated = getattr(canvas, "eliminated_players", set())
    next_player = (canvas.current_player + 1) % num_players
    while next_player in eliminated:
        next_player = (next_player + 1) % num_players
    canvas.current_player = next_player
    canvas.phase = "place"
    canvas.conquered_this_turn = False
    if len(eliminated) >= num_players - 1:
        winner = next(p for p in range(num_players) if p not in eliminated)
        turn_label.config(text=f"{COLOR_NAMES[winner]} wins!")
        if hasattr(canvas, "end_turn_btn") and canvas.end_turn_btn.winfo_exists():
            canvas.end_turn_btn.pack_forget()
        draw_grid(canvas)
        return
    hand = canvas.player_cards[next_player]
    has_set, to_remove = has_valid_set(hand)
    if len(hand) > 6 and has_set and to_remove:
        remove_set_from_hand(hand, to_remove)
        n_bonus = get_bonus_armies(canvas.set_turn_in_count)
        canvas.set_turn_in_count += 1
        canvas.phase = "bonus_place"
        canvas.bonus_place_remaining = n_bonus
        if hasattr(canvas, "end_turn_btn") and canvas.end_turn_btn.winfo_exists():
            canvas.end_turn_btn.pack_forget()
        turn_label.config(text=f"{COLOR_NAMES[next_player]}'s turn — place {n_bonus} armies (mandatory: had >6 cards)")
        if hasattr(canvas, "update_cards_display"):
            canvas.update_cards_display()
        draw_grid(canvas)
        return
    canvas.placements_remaining = armies_per_turn(canvas, next_player)
    if canvas.placements_remaining > 0:
        turn_label.config(text=f"{COLOR_NAMES[next_player]}'s turn — place {canvas.placements_remaining} armies")
        if hasattr(canvas, "end_turn_btn") and canvas.end_turn_btn.winfo_exists():
            canvas.end_turn_btn.pack_forget()
    else:
        turn_label.config(text=f"{COLOR_NAMES[next_player]}'s turn — select territory to attack from")
        canvas.phase = "attack"
        if hasattr(canvas, "end_turn_btn") and canvas.end_turn_btn.winfo_exists():
            canvas.end_turn_btn.config(text="Done attacking")
            canvas.end_turn_btn.pack(side=tk.LEFT, padx=4)
    draw_grid(canvas)


def _place_dialog_bottom_right(dlg, parent, margin=40):
    """Place the dialog window in the bottom-right corner of the parent. Call before showing the dialog."""
    parent.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dlg.update_idletasks()
    dw = dlg.winfo_reqwidth()
    dh = dlg.winfo_reqheight()
    x = px + pw - dw - margin
    y = py + ph - dh - margin
    dlg.geometry(f"+{max(px, x)}+{max(py, y)}")


def _select_all(entry):
    """Select all text in Entry or Spinbox (Spinbox uses selection_range in Python 3.13+)."""
    sel = getattr(entry, "selection_range", getattr(entry, "select_range", None))
    if sel is not None:
        sel(0, tk.END)


def ask_blitz_params(parent, source_armies, target_armies):
    """
    Dialog for 'Continue attacking': choose stop conditions and armies per round.
    Returns dict with stop_attacker, stop_defender, armies_per_round, or None if cancelled.
    """
    result = [None]
    max_per_round = min(3, source_armies - 1)
    stop_attacker_max = max(1, source_armies - 1)
    stop_defender_max = max(0, target_armies)

    def on_ok():
        try:
            sa = int(float(sb_stop_attacker.get()))
            sd = int(float(sb_stop_defender.get()))
            apr = int(float(sb_armies.get()))
            if 1 <= sa <= stop_attacker_max and 0 <= sd <= stop_defender_max and 1 <= apr <= max_per_round:
                result[0] = {"stop_attacker": sa, "stop_defender": sd, "armies_per_round": apr}
                dlg.destroy()
            else:
                _select_all(sb_stop_attacker)
        except (ValueError, TypeError):
            _select_all(sb_stop_attacker)

    dlg = tk.Toplevel(parent)
    dlg.withdraw()
    dlg.title("Continue attacking")
    dlg.transient(parent)
    dlg.grab_set()
    tk.Label(
        dlg, text="Continue attacking until you don't have more than X armies here, or defender doesn't have more than Y. Attack with Z armies each round when available.",
        wraplength=340
    ).pack(pady=(10, 8))
    row1 = tk.Frame(dlg)
    row1.pack(pady=4)
    tk.Label(row1, text="Stop when you have ≤").pack(side=tk.LEFT, padx=(0, 4))
    sb_stop_attacker = tk.Spinbox(row1, from_=1, to=stop_attacker_max, width=4)
    sb_stop_attacker.pack(side=tk.LEFT)
    sb_stop_attacker.delete(0, tk.END)
    sb_stop_attacker.insert(0, "1")
    tk.Label(row1, text="armies here").pack(side=tk.LEFT, padx=(4, 0))
    row2 = tk.Frame(dlg)
    row2.pack(pady=4)
    tk.Label(row2, text="Or defender has ≤").pack(side=tk.LEFT, padx=(0, 4))
    sb_stop_defender = tk.Spinbox(row2, from_=0, to=stop_defender_max, width=4)
    sb_stop_defender.pack(side=tk.LEFT)
    sb_stop_defender.delete(0, tk.END)
    sb_stop_defender.insert(0, "0")
    tk.Label(row2, text="armies").pack(side=tk.LEFT, padx=(4, 0))
    row3 = tk.Frame(dlg)
    row3.pack(pady=4)
    tk.Label(row3, text="Attack with").pack(side=tk.LEFT, padx=(0, 4))
    sb_armies = tk.Spinbox(row3, from_=1, to=max_per_round, width=4)
    sb_armies.pack(side=tk.LEFT)
    sb_armies.delete(0, tk.END)
    sb_armies.insert(0, str(max_per_round))
    tk.Label(row3, text="armies each round when available").pack(side=tk.LEFT, padx=(4, 0))
    f = tk.Frame(dlg)
    f.pack(pady=(12, 10))
    tk.Button(f, text="OK", command=on_ok).pack(side=tk.LEFT, padx=4)
    tk.Button(f, text="Cancel", command=lambda: dlg.destroy()).pack(side=tk.LEFT, padx=4)
    dlg.protocol("WM_DELETE_WINDOW", lambda: dlg.destroy())
    dlg.update_idletasks()
    _place_dialog_bottom_right(dlg, parent)
    dlg.deiconify()
    dlg.wait_window()
    return result[0]


def ask_attack_count(parent, prompt, minvalue, maxvalue, blitz_context=None):
    """
    Custom dialog: returns int, blitz dict, or None.
    blitz_context: (source_armies, target_armies) to enable 'Continue attacking' button.
    """
    result = [None]

    def on_ok():
        try:
            v = int(float(entry.get()))
            if minvalue <= v <= maxvalue:
                result[0] = v
                dlg.destroy()
            else:
                _select_all(entry)
        except (ValueError, TypeError):
            _select_all(entry)

    def on_cancel():
        result[0] = None
        dlg.destroy()

    def on_continue():
        dlg.withdraw()
        if blitz_context is not None:
            src_armies, tgt_armies = blitz_context
            params = ask_blitz_params(parent, src_armies, tgt_armies)
            if params is not None:
                result[0] = params
        dlg.destroy()

    dlg = tk.Toplevel(parent)
    dlg.withdraw()
    dlg.title("Attack")
    dlg.transient(parent)
    dlg.grab_set()
    tk.Label(dlg, text=prompt, wraplength=320).pack(pady=(10, 5))
    entry = tk.Spinbox(dlg, from_=minvalue, to=maxvalue, width=5)
    entry.pack(pady=5)
    entry.delete(0, tk.END)
    entry.insert(0, str(maxvalue))
    f = tk.Frame(dlg)
    f.pack(pady=(5, 10))
    tk.Button(f, text="OK", command=on_ok).pack(side=tk.LEFT, padx=2)
    if blitz_context is not None:
        tk.Button(f, text="Continue attacking", command=on_continue).pack(side=tk.LEFT, padx=2)
    tk.Button(f, text="I don't want to attack", command=on_cancel).pack(side=tk.LEFT, padx=2)
    dlg.protocol("WM_DELETE_WINDOW", on_cancel)
    dlg.update_idletasks()
    _place_dialog_bottom_right(dlg, parent)
    dlg.deiconify()
    dlg.wait_window()
    return result[0]


def ask_defend_count(parent, prompt, minvalue, maxvalue):
    """Custom dialog for defender: returns int. No cancel / no 'I don't want to attack'."""
    result = [None]

    def on_ok():
        try:
            v = int(float(entry.get()))
            if minvalue <= v <= maxvalue:
                result[0] = v
                dlg.destroy()
            else:
                _select_all(entry)
        except (ValueError, TypeError):
            _select_all(entry)

    dlg = tk.Toplevel(parent)
    dlg.withdraw()
    dlg.title("Defend")
    dlg.transient(parent)
    dlg.grab_set()
    tk.Label(dlg, text=prompt, wraplength=320).pack(pady=(10, 5))
    entry = tk.Spinbox(dlg, from_=minvalue, to=maxvalue, width=5)
    entry.pack(pady=5)
    entry.delete(0, tk.END)
    entry.insert(0, str(maxvalue))
    f = tk.Frame(dlg)
    f.pack(pady=(5, 10))
    tk.Button(f, text="OK", command=on_ok).pack()
    dlg.protocol("WM_DELETE_WINDOW", on_ok)
    dlg.update_idletasks()
    _place_dialog_bottom_right(dlg, parent)
    dlg.deiconify()
    dlg.wait_window()
    return result[0]


def ask_move_count(parent, prompt, minvalue, maxvalue):
    """Dialog for move phase: how many troops to move. Returns int or None."""
    result = [None]

    def on_ok():
        try:
            v = int(float(entry.get()))
            if minvalue <= v <= maxvalue:
                result[0] = v
                dlg.destroy()
            else:
                _select_all(entry)
        except (ValueError, TypeError):
            _select_all(entry)

    def on_cancel():
        result[0] = None
        dlg.destroy()

    dlg = tk.Toplevel(parent)
    dlg.withdraw()
    dlg.title("Move troops")
    dlg.transient(parent)
    dlg.grab_set()
    tk.Label(dlg, text=prompt, wraplength=320).pack(pady=(10, 5))
    entry = tk.Spinbox(dlg, from_=minvalue, to=maxvalue, width=5)
    entry.pack(pady=5)
    entry.delete(0, tk.END)
    entry.insert(0, str(maxvalue))
    f = tk.Frame(dlg)
    f.pack(pady=(5, 10))
    tk.Button(f, text="OK", command=on_ok).pack(side=tk.LEFT, padx=2)
    tk.Button(f, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=2)
    dlg.protocol("WM_DELETE_WINDOW", on_cancel)
    dlg.update_idletasks()
    _place_dialog_bottom_right(dlg, parent)
    dlg.deiconify()
    dlg.wait_window()
    return result[0]


BRICK_LAYOUT = True  # staggered rows like a brick wall


def cell_center(cell_w, cell_h, row, col):
    """Return (cx, cy) for the center of cell (row, col) in brick layout."""
    cy = (row + 0.5) * cell_h
    if BRICK_LAYOUT and row % 2 == 1:
        cx = cell_w * 0.5 + (col + 0.5) * cell_w
    else:
        cx = (col + 0.5) * cell_w
    return cx, cy


def _adjacent_cells_raw(row, col):
    """All grid-adjacent (r, c) to (row, col) in brick layout (no removed filter)."""
    out = []
    if col > 0:
        out.append((row, col - 1))
    if col < COLS - 1:
        out.append((row, col + 1))
    if row % 2 == 0:
        for dc in (-1, 0):
            r, c = row - 1, col + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                out.append((r, c))
        for dc in (-1, 0):
            r, c = row + 1, col + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                out.append((r, c))
    else:
        for dc in (0, 1):
            r, c = row - 1, col + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                out.append((r, c))
        for dc in (0, 1):
            r, c = row + 1, col + dc
            if 0 <= r < ROWS and 0 <= c < COLS:
                out.append((r, c))
    return out


def _cell_center_norm(row, col):
    """Center of cell (row, col) in normalized coords (cell_w=1, cell_h=1), brick layout."""
    cy = (row + 0.5)
    if BRICK_LAYOUT and row % 2 == 1:
        cx = 0.5 + (col + 0.5)
    else:
        cx = (col + 0.5)
    return cx, cy


def _cell_rect_norm(row, col):
    """(x1, y1, x2, y2) in normalized coords for brick layout."""
    if BRICK_LAYOUT and row % 2 == 1:
        x1 = 0.5 + col
    else:
        x1 = col
    x2 = x1 + 1
    y1, y2 = row, row + 1
    return x1, y1, x2, y2


def _cell_rect_pixel(cell_w, cell_h, row, col):
    """(x1, y1, x2, y2) in pixel coords for brick layout."""
    if BRICK_LAYOUT and row % 2 == 1:
        x1 = cell_w * 0.5 + col * cell_w
    else:
        x1 = col * cell_w
    x2 = x1 + cell_w
    y1 = row * cell_h
    y2 = y1 + cell_h
    return x1, y1, x2, y2


def _cell_center_pixel(cell_w, cell_h, row, col):
    """(cx, cy) in pixel coords for brick layout."""
    x1, y1, x2, y2 = _cell_rect_pixel(cell_w, cell_h, row, col)
    return (x1 + x2) / 2, (y1 + y2) / 2


def compute_bridges(canvas, cell_w, cell_h):
    """Compute bridge edges + left/right wrap bridges; sets bridge_edges/bridge_neighbors/wrap_bridge_edges."""
    from collections import deque
    removed = canvas.removed
    territory_to_cell = canvas.territory_to_cell
    cell_to_territory = canvas.cell_to_territory

    def adj(t_idx):
        r, c = territory_to_cell[t_idx]
        out = []
        for (nr, nc) in adjacent_cells(r, c, removed):
            out.append(cell_to_territory[(nr, nc)])
        return out

    physical = [adj(i) for i in range(TOTAL)]

    def components(adj_list):
        seen = set()
        comps = []
        for start in range(TOTAL):
            if start in seen:
                continue
            comp = []
            q = deque([start])
            seen.add(start)
            while q:
                t = q.popleft()
                comp.append(t)
                for u in adj_list[t]:
                    if u not in seen:
                        seen.add(u)
                        q.append(u)
            comps.append(comp)
        return comps

    centers = [_cell_center_pixel(cell_w, cell_h, *territory_to_cell[i]) for i in range(TOTAL)]
    rects = [_cell_rect_pixel(cell_w, cell_h, *territory_to_cell[i]) for i in range(TOTAL)]

    def can_connect(i, j):
        ax, ay = centers[i]
        bx, by = centers[j]
        for k in range(TOTAL):
            if k == i or k == j:
                continue
            r = rects[k]
            if _segment_intersects_rect(ax, ay, bx, by, r[0], r[1], r[2], r[3]):
                return False
        return True

    bridge_edges = []
    wrap_bridge_edges = []
    bridge_neighbors = [set() for _ in range(TOTAL)]
    adj_list = [list(physical[i]) for i in range(TOTAL)]

    while True:
        comps = components(adj_list)
        if len(comps) <= 1:
            break
        best_pair = None
        best_dist = float("inf")
        for c1 in comps:
            for c2 in comps:
                if c1 is c2:
                    continue
                for i in c1:
                    for j in c2:
                        if not can_connect(i, j):
                            continue
                        ax, ay = centers[i]
                        bx, by = centers[j]
                        d = (ax - bx) ** 2 + (ay - by) ** 2
                        if d < best_dist or (d == best_dist and (best_pair is None or (i, j) < best_pair)):
                            best_dist = d
                            best_pair = (i, j)
        if best_pair is None:
            break
        i, j = best_pair
        adj_list[i].append(j)
        adj_list[j].append(i)
        bridge_edges.append((i, j))
        bridge_neighbors[i].add(j)
        bridge_neighbors[j].add(i)

    # Horizontal wrap: connect leftmost and rightmost territory in each row.
    by_cell = {cell: idx for idx, cell in enumerate(territory_to_cell)}
    for r in range(ROWS):
        left_cell = (r, 0)
        right_cell = (r, COLS - 1)
        # Wrap bridge exists only when both true edge columns are land.
        if left_cell not in by_cell or right_cell not in by_cell:
            continue
        left_idx = by_cell[left_cell]
        right_idx = by_cell[right_cell]
        if right_idx in bridge_neighbors[left_idx]:
            continue
        bridge_edges.append((left_idx, right_idx))
        wrap_bridge_edges.append((left_idx, right_idx))
        bridge_neighbors[left_idx].add(right_idx)
        bridge_neighbors[right_idx].add(left_idx)

    canvas.bridge_edges = bridge_edges
    canvas.wrap_bridge_edges = wrap_bridge_edges
    canvas.bridge_neighbors = bridge_neighbors


def _segment_intersects_rect(ax, ay, bx, by, rx1, ry1, rx2, ry2):
    """True if segment (a,b) intersects rectangle (rx1,ry1)-(rx2,ry2). Uses correct parametric t for segment (a,b)."""
    def inside(x, y):
        return rx1 <= x <= rx2 and ry1 <= y <= ry2
    dx, dy = bx - ax, by - ay
    # Segment (ax,ay)+t*(dx,dy), t in [0,1]. Edge (ex1,ey1)+u*(ex,ey), u in [0,1].
    # Intersection: t = ((ey1-ay)*ex - (ex1-ax)*ey) / (dx*ey - dy*ex),  u = ((ex1-ax)*dy - (ey1-ay)*dx) / (dx*ey - dy*ex)
    for (ex1, ey1, ex2, ey2) in [(rx1, ry1, rx2, ry1), (rx2, ry1, rx2, ry2), (rx2, ry2, rx1, ry2), (rx1, ry2, rx1, ry1)]:
        ex, ey = ex2 - ex1, ey2 - ey1
        denom = dx * ey - dy * ex
        if abs(denom) < 1e-10:
            continue
        t = ((ey1 - ay) * ex - (ex1 - ax) * ey) / denom
        u = ((ex1 - ax) * dy - (ey1 - ay) * dx) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return True
    if inside(ax, ay) or inside(bx, by):
        return True
    return False


def make_playable_region():
    """
    Grow from NUM_CAPITALS random capitals until we have TOTAL playable cells. Each gets a continent.
    No continent has 1–3 territories. When a partition is possible, every continent size is in
    [num_players, 3.5 * num_players]; otherwise the map is regenerated. If TOTAL cannot fit that
    range (e.g. 2-player map), the limit is skipped. Returns (removed, cell_to_territory, ...).
    Bridges are computed later in draw_grid using pixel geometry.
    """
    from collections import deque, Counter
    all_cells = [(r, c) for r in range(ROWS) for c in range(COLS)]
    num_players = len(COLORS)
    min_by_players = num_players
    max_by_players = 3.5 * num_players
    max_per_continent_int = math.floor(max_by_players)
    check_size_limits = (
        NUM_CAPITALS * min_by_players <= TOTAL <= NUM_CAPITALS * max_per_continent_int
    )

    attempts = 0
    while True:
        attempts += 1
        if attempts > 100_000:
            raise RuntimeError(
                "make_playable_region: could not satisfy continent size limits after many tries; "
                "try different ROWS/COLS/TOTAL/NUM_CAPITALS."
            )
        # Pick NUM_CAPITALS so no two are adjacent (brick adjacency)
        chosen = []
        forbidden = set()
        pool = list(all_cells)
        random.shuffle(pool)
        for cell in pool:
            if len(chosen) == NUM_CAPITALS:
                break
            if cell in forbidden:
                continue
            chosen.append(cell)
            forbidden.add(cell)
            for (nr, nc) in _adjacent_cells_raw(*cell):
                forbidden.add((nr, nc))
        if len(chosen) != NUM_CAPITALS:
            continue
        capitals_cells = chosen
        continent_of_cell = {cap: i for i, cap in enumerate(capitals_cells)}
        assigned = set(capitals_cells)
        # Grow until we have exactly TOTAL cells (keep going if frontier empties early)
        while len(assigned) < TOTAL:
            frontier = []
            for (r, c) in assigned:
                cid = continent_of_cell[(r, c)]
                for (nr, nc) in _adjacent_cells_raw(r, c):
                    if (nr, nc) not in assigned:
                        frontier.append(((nr, nc), cid))
            if not frontier:
                break
            (cell, cid) = random.choice(frontier)
            continent_of_cell[cell] = cid
            assigned.add(cell)
        if len(assigned) != TOTAL:
            continue

        # Ensure no continent has 1, 2, or 3 territories: each must have at least 4
        min_continent_size = 4
        while True:
            sizes = Counter(continent_of_cell[cell] for cell in assigned)
            small_cid = next((c for c, n in sizes.items() if n < min_continent_size), None)
            if small_cid is None:
                break
            # Need to steal a neighbor from a continent with size >= min_continent_size + 1 so donor stays >= 4
            donor = None
            capitals_set = set(capitals_cells)
            for cell in assigned:
                if continent_of_cell[cell] != small_cid:
                    continue
                for (nr, nc) in _adjacent_cells_raw(*cell):
                    if (nr, nc) not in assigned:
                        continue
                    if (nr, nc) in capitals_set:
                        continue
                    other_cid = continent_of_cell[(nr, nc)]
                    if other_cid != small_cid and sizes[other_cid] >= min_continent_size + 1:
                        donor = (nr, nc)
                        break
                if donor is not None:
                    break
            if donor is None:
                break
            continent_of_cell[donor] = small_cid

        if check_size_limits:
            sizes = Counter(continent_of_cell[cell] for cell in assigned)
            if not all(min_by_players <= n <= max_by_players for n in sizes.values()):
                continue
        break

    removed = set(all_cells) - assigned
    territory_to_cell = sorted(assigned)
    cell_to_territory = {cell: i for i, cell in enumerate(territory_to_cell)}
    # Capital territory index per continent (seed cell); fixed before any reassignment
    capital_territory_for_continent = [cell_to_territory[capitals_cells[cid]] for cid in range(NUM_CAPITALS)]

    capitals = set(cell_to_territory[cap] for cap in capitals_cells)
    continents = [continent_of_cell[territory_to_cell[i]] for i in range(TOTAL)]

    return removed, cell_to_territory, territory_to_cell, capitals, continents, capital_territory_for_continent


def adjacent_cells(row, col, removed=None):
    """Return list of (r, c) adjacent to (row, col), optionally excluding removed cells."""
    out = _adjacent_cells_raw(row, col)
    if removed is not None:
        out = [(r, c) for (r, c) in out if (r, c) not in removed]
    return out


def get_adjacent_territory_indices(canvas, territory_idx):
    """Territory indices adjacent to territory_idx (physical + bridge)."""
    cell_to_territory = canvas.cell_to_territory
    territory_to_cell = canvas.territory_to_cell
    removed = canvas.removed
    r, c = territory_to_cell[territory_idx]
    physical = [cell_to_territory[(nr, nc)] for (nr, nc) in adjacent_cells(r, c, removed)]
    bridge = getattr(canvas, "bridge_neighbors", None)
    if bridge is not None:
        return list(set(physical) | bridge[territory_idx])
    return physical


def reachable_from(player_color, start_row, start_col, assignment, cell_to_territory, territory_to_cell, removed, bridge_neighbors):
    """Set of (r, c) reachable from start territory using only player_color (physical + bridge adjacency)."""
    start_idx = cell_to_territory[(start_row, start_col)]
    result_idx = {start_idx}
    stack = [start_idx]
    while stack:
        idx = stack.pop()
        for u in get_adjacent_territory_indices_from_lists(cell_to_territory, territory_to_cell, removed, bridge_neighbors, idx):
            if u in result_idx:
                continue
            if assignment[u] == player_color:
                result_idx.add(u)
                stack.append(u)
    return {territory_to_cell[t] for t in result_idx}


def get_adjacent_territory_indices_from_lists(cell_to_territory, territory_to_cell, removed, bridge_neighbors, territory_idx):
    """Same as get_adjacent_territory_indices but takes explicit args (for reachable_from)."""
    r, c = territory_to_cell[territory_idx]
    physical = [cell_to_territory[(nr, nc)] for (nr, nc) in adjacent_cells(r, c, removed)]
    if bridge_neighbors is not None:
        return list(set(physical) | bridge_neighbors[territory_idx])
    return physical


def _roll_d6():
    """Fair d6 using OS CSPRNG (secrets) so dice are unbiased and independent of other RNG use."""
    return secrets.randbelow(6) + 1


def resolve_battle(attack_count, defend_count):
    """
    Roll one d6 per army, sort both sets high-to-low, then pair: 1st vs 1st, 2nd vs 2nd, etc.
    E.g. attacker [6, 6, 2] vs defender [5, 4] → pairs (6,5) and (6,4) → defender loses 2.
    Attacker wins a pair if attack > defend; else defender wins (tie = defender).
    """
    attack_dice = sorted([_roll_d6() for _ in range(attack_count)], reverse=True)
    defend_dice = sorted([_roll_d6() for _ in range(defend_count)], reverse=True)
    pairs = min(len(attack_dice), len(defend_dice))
    attacker_casualties = defender_casualties = 0
    for i in range(pairs):
        if attack_dice[i] > defend_dice[i]:
            defender_casualties += 1
        else:
            attacker_casualties += 1
    return (attacker_casualties, defender_casualties, attack_dice, defend_dice)


def make_assignment(continents):
    """Assign so 1st gets 12, 2nd gets 15, 3rd gets 17, 4th gets 18 (no player >3/4 of any continent)."""
    num_players = len(COLORS)
    # Targets: 12, 15, 17, 18 for 2/3/4 players
    targets = [12, 15, 17, 18][:num_players]
    from collections import defaultdict
    by_continent = defaultdict(list)
    for i in range(TOTAL):
        by_continent[continents[i]].append(i)
    # Step 1: Assign exactly targets[p] to each player (shuffle order so distribution is random)
    indices = list(range(TOTAL))
    random.shuffle(indices)
    assignment = [None] * TOTAL
    start = 0
    for p in range(num_players):
        end = start + targets[p]
        for k in range(start, end):
            assignment[indices[k]] = COLORS[p]
        start = end
    # Step 2: Fix 3/4 violations by swapping (totals stay equal)
    def count_per_player_in_continent():
        pc = defaultdict(lambda: defaultdict(int))
        for i in range(TOTAL):
            cid = continents[i]
            color = assignment[i]
            p = COLORS.index(color) if color in COLORS else 0
            pc[p][cid] += 1
        return pc

    def would_violate(p, cid, delta):
        size = len(by_continent[cid])
        max_allowed = size * 3 // 4
        current = count_per_player_in_continent()[p][cid]
        return current + delta > max_allowed

    for _ in range(TOTAL * 3):
        pc = count_per_player_in_continent()
        # Find any continent where a player exceeds 3/4
        violator = None
        for cid, inds in by_continent.items():
            size = len(inds)
            max_allowed = size * 3 // 4
            for p in range(num_players):
                if pc[p][cid] > max_allowed:
                    violator = (p, cid)
                    break
            if violator is not None:
                break
        if violator is None:
            break
        over_p, viol_cid = violator
        # Find territory i in viol_cid owned by over_p, and j in another continent owned by someone else; swap if it fixes or doesn't worsen
        for i in by_continent[viol_cid]:
            if assignment[i] != COLORS[over_p]:
                continue
            for j in range(TOTAL):
                if continents[j] == viol_cid or assignment[j] == COLORS[over_p]:
                    continue
                other_cid = continents[j]
                other_p = COLORS.index(assignment[j])
                # After swap: over_p loses 1 in viol_cid, gains 1 in other_cid; other_p gains 1 in viol_cid, loses 1 in other_cid
                if would_violate(over_p, other_cid, 1) or would_violate(other_p, viol_cid, 1):
                    continue
                assignment[i], assignment[j] = assignment[j], assignment[i]
                break
            else:
                continue
            break
    return assignment


def cell_from_xy(canvas, x, y):
    """Return (row, col) or None if outside grid. Brick layout uses staggered columns for odd rows."""
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        return None
    if BRICK_LAYOUT:
        cell_w = w / (COLS + 0.5)
        cell_h = h / ROWS
        row = int(y / cell_h)
        if row < 0 or row >= ROWS:
            return None
        if row % 2 == 0:
            col = int(x / cell_w)
        else:
            x0 = x - cell_w * 0.5
            if x0 < 0:
                return None
            col = int(x0 / cell_w)
        if 0 <= col < COLS:
            if getattr(canvas, "removed", set()) and (row, col) in canvas.removed:
                return None
            return (row, col)
        return None
    cell_w = w / COLS
    cell_h = h / ROWS
    col = int(x / cell_w)
    row = int(y / cell_h)
    if 0 <= row < ROWS and 0 <= col < COLS:
        if getattr(canvas, "removed", set()) and (row, col) in canvas.removed:
            return None
        return (row, col)
    return None


def _cell_rect_brick(cell_w, cell_h, ri, cj):
    """(x1, y1, x2, y2) in pixel coords for brick layout."""
    if BRICK_LAYOUT and ri % 2 == 1:
        x1 = cell_w * 0.5 + cj * cell_w
    else:
        x1 = cj * cell_w
    x2 = x1 + cell_w
    y1 = ri * cell_h
    y2 = y1 + cell_h
    return x1, y1, x2, y2


def _shared_edge_brick(r, c, nr, nc, cell_w, cell_h):
    """Exact line segment shared by adjacent cells (r,c) and (nr,nc) in brick layout. Returns ((x1,y1), (x2,y2)) or None."""
    x1, y1, x2, y2 = _cell_rect_brick(cell_w, cell_h, r, c)
    nx1, ny1, nx2, ny2 = _cell_rect_brick(cell_w, cell_h, nr, nc)
    # Shared vertical edge: our right = neighbor's left or our left = neighbor's right
    eps = 1e-6
    if abs(x2 - nx1) < eps and _ranges_overlap(y1, y2, ny1, ny2):
        return ((x2, max(y1, ny1)), (x2, min(y2, ny2)))
    if abs(x1 - nx2) < eps and _ranges_overlap(y1, y2, ny1, ny2):
        return ((x1, max(y1, ny1)), (x1, min(y2, ny2)))
    # Shared horizontal edge: our bottom = neighbor's top or our top = neighbor's bottom
    if abs(y2 - ny1) < eps and _ranges_overlap(x1, x2, nx1, nx2):
        return ((max(x1, nx1), y2), (min(x2, nx2), y2))
    if abs(y1 - ny2) < eps and _ranges_overlap(x1, x2, nx1, nx2):
        return ((max(x1, nx1), y1), (min(x2, nx2), y1))
    return None


def _ranges_overlap(a1, a2, b1, b2):
    return not (a2 <= b1 or b2 <= a1)


def _continent_boundary_loops(cell_w, cell_h, removed, cell_to_territory, continents):
    """For each continent, return (list of closed loops, list of raw segments). Uses brick adjacency and exact shared edges so outline stays on boundary."""
    if continents is None:
        return []
    by_continent = {}
    for (r, c) in cell_to_territory:
        if (r, c) in removed:
            continue
        idx = cell_to_territory[(r, c)]
        cid = continents[idx]
        by_continent.setdefault(cid, set()).add((r, c))

    def neighbor_in_continent(nr, nc, cid):
        if nr < 0 or nr >= ROWS or nc < 0 or nc >= COLS:
            return False
        if (nr, nc) in removed:
            return False
        if (nr, nc) not in cell_to_territory:
            return False
        return continents[cell_to_territory[(nr, nc)]] == cid

    _eps = 1e-6

    def pt_eq(p, q):
        return abs(p[0] - q[0]) < _eps and abs(p[1] - q[1]) < _eps

    result = []
    for cid in sorted(by_continent.keys()):
        cells = by_continent[cid]
        segments = []
        for (r, c) in sorted(cells):
            for (nr, nc) in _adjacent_cells_raw(r, c):
                if neighbor_in_continent(nr, nc, cid):
                    continue
                seg = _shared_edge_brick(r, c, nr, nc, cell_w, cell_h)
                if seg is not None:
                    segments.append(seg)
        # Chain segments into closed loops; track orphans (segments that didn't close) so we still draw them
        segs = list(segments)
        loops = []
        orphan_segments = []
        while segs:
            a, b = segs.pop(0)
            used = [(a, b)]
            loop = [a, b]
            start = a
            prev, current = a, b
            while True:
                if pt_eq(current, start) and len(loop) >= 3:
                    loops.append(loop)
                    break
                candidates = []
                for i, (p, q) in enumerate(segs):
                    if pt_eq(p, current) and not pt_eq(q, prev):
                        candidates.append((i, q))
                    elif pt_eq(q, current) and not pt_eq(p, prev):
                        candidates.append((i, p))
                if not candidates:
                    orphan_segments.extend(used)
                    break
                if len(candidates) == 1:
                    i, next_pt = candidates[0]
                else:
                    v_in = (current[0] - prev[0], current[1] - prev[1])
                    def turn_angle(idx_next):
                        next_pt = idx_next[1]
                        v_out = (next_pt[0] - current[0], next_pt[1] - current[1])
                        cross = v_in[0] * v_out[1] - v_in[1] * v_out[0]
                        dot = v_in[0] * v_out[0] + v_in[1] * v_out[1]
                        ang = math.atan2(cross, dot)
                        return ang if ang > 0 else ang + 2 * math.pi
                    candidates.sort(key=turn_angle)
                    i, next_pt = candidates[0]
                seg = segs.pop(i)
                used.append(seg)
                loop.append(next_pt)
                prev, current = current, next_pt
        result.append((cid, loops, segments, orphan_segments))
    return result


def draw_grid(canvas):
    canvas.delete("grid")
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        return
    if BRICK_LAYOUT:
        cell_w = w / (COLS + 0.5)
    else:
        cell_w = w / COLS
    cell_h = h / ROWS
    # Compute bridges once per game so continent connections never change (e.g. on resize)
    if not getattr(canvas, "_bridge_computed_for", False) and getattr(canvas, "territory_to_cell", None):
        compute_bridges(canvas, cell_w, cell_h)
        canvas._bridge_computed_for = True
    assignment = getattr(canvas, "assignment", None)
    armies = getattr(canvas, "armies", None)
    territory_names = getattr(canvas, "territory_names", None)
    removed = getattr(canvas, "removed", set())
    cell_to_territory = getattr(canvas, "cell_to_territory", None)
    continents = getattr(canvas, "continents", None)
    capitals = getattr(canvas, "capitals", set())
    if assignment is None:
        return
    if armies is None:
        armies = [1] * TOTAL
    if cell_to_territory is None:
        if ROWS * COLS != TOTAL:
            return
        cell_to_territory = {(i, j): i * COLS + j for i in range(ROWS) for j in range(COLS)}
        removed = set()
    half = min(cell_w, cell_h) / 2
    r = half * PIECE_SIZE
    phase = getattr(canvas, "phase", "place")
    attack_source = getattr(canvas, "attack_source", None)
    attack_targets = getattr(canvas, "attack_targets", set())
    move_source = getattr(canvas, "move_source", None)
    move_targets = getattr(canvas, "move_targets", set())
    for i in range(ROWS):
        for j in range(COLS):
            if (i, j) in removed:
                x1 = (cell_w * 0.5 if i % 2 == 1 else 0) + j * cell_w
                x2 = x1 + cell_w
                y1, y2 = i * cell_h, (i + 1) * cell_h
                canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=2, fill="#555555", tags="grid")
                continue
            idx = cell_to_territory[(i, j)]
            continent_id = continents[idx] if continents is not None else None
            cx, cy = cell_center(cell_w, cell_h, i, j)
            if BRICK_LAYOUT:
                x1 = (cell_w * 0.5 if i % 2 == 1 else 0) + j * cell_w
                x2 = x1 + cell_w
                y1, y2 = i * cell_h, (i + 1) * cell_h
                canvas.create_rectangle(x1, y1, x2, y2, outline="gray", width=1, fill=assignment[idx], tags="grid")

            outline = "gray"
            width = 1
            if phase == "attack" and (i, j) == attack_source:
                outline = "black"
                width = 4
            elif phase == "attack" and (i, j) in attack_targets:
                outline = "orange"
                width = 3
            elif phase == "move" and (i, j) == move_source:
                outline = "black"
                width = 4
            elif phase == "move" and (i, j) in move_targets:
                outline = "green"
                width = 3
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=assignment[idx], outline=outline, width=width, tags="grid")
            if territory_names and idx < len(territory_names):
                cell_top = i * cell_h
                name_y = cell_top + 0.22 * cell_h
                font_size = max(6, min(10, int(cell_w * 0.2)))
                base_name = territory_names[idx]
                if capitals and idx in capitals:
                    display_name = f"★ {base_name}"
                else:
                    display_name = base_name
                name_color = "goldenrod" if capitals and idx in capitals else "black"
                canvas.create_text(cx, name_y, text=display_name, font=("Helvetica", font_size), fill=name_color, anchor="n", tags=("grid", "territory_name"))
    # One bold outline per continent
    if BRICK_LAYOUT and continents is not None and cell_to_territory:
        for cid, loops, segments, orphan_segments in _continent_boundary_loops(cell_w, cell_h, removed, cell_to_territory, continents):
            color = CONTINENT_BORDER_COLORS[cid % len(CONTINENT_BORDER_COLORS)]
            if loops:
                for loop in loops:
                    if len(loop) < 3:
                        continue
                    pts = [c for p in loop for c in p]
                    canvas.create_polygon(pts, outline=color, fill="", width=4, tags="grid")
            else:
                for (a, b) in segments:
                    canvas.create_line(a[0], a[1], b[0], b[1], fill=color, width=4, tags="grid")
            for (a, b) in orphan_segments:
                canvas.create_line(a[0], a[1], b[0], b[1], fill=color, width=4, tags="grid")
    # Draw bridge lines (connect territories in different continents)
    territory_to_cell = getattr(canvas, "territory_to_cell", None)
    bridge_edges = getattr(canvas, "bridge_edges", [])
    if territory_to_cell and bridge_edges:
        wrap_bridge_edges = {tuple(sorted(pair)) for pair in getattr(canvas, "wrap_bridge_edges", [])}
        for (idx_a, idx_b) in bridge_edges:
            r1, c1 = territory_to_cell[idx_a]
            r2, c2 = territory_to_cell[idx_b]
            x1, y1 = cell_center(cell_w, cell_h, r1, c1)
            x2, y2 = cell_center(cell_w, cell_h, r2, c2)
            if tuple(sorted((idx_a, idx_b))) in wrap_bridge_edges:
                if x1 <= x2:
                    lx, ly, rx, ry = x1, y1, x2, y2
                else:
                    lx, ly, rx, ry = x2, y2, x1, y1
                canvas.create_line(lx, ly, 0, ly, fill="black", width=2, tags="grid")
                canvas.create_line(rx, ry, w, ry, fill="black", width=2, tags="grid")
            else:
                canvas.create_line(x1, y1, x2, y2, fill="black", width=2, tags="grid")
    if not BRICK_LAYOUT:
        for i in range(ROWS + 1):
            y = i * cell_h
            canvas.create_line(0, y, w, y, tags="grid", fill="gray", width=2)
        for j in range(COLS + 1):
            x = j * cell_w
            canvas.create_line(x, 0, x, h, tags="grid", fill="gray", width=2)
    update_ghost(canvas)
    for i in range(ROWS):
        for j in range(COLS):
            if (i, j) in removed:
                continue
            idx = cell_to_territory[(i, j)]
            if armies[idx] > 1:
                cx, cy = cell_center(cell_w, cell_h, i, j)
                canvas.create_text(cx, cy, text=str(armies[idx]), font=("Helvetica", max(8, int(r))), fill="white", tags=("grid", "army_text"))


def update_ghost(canvas):
    """Show or hide the placement ghost at the current mouse cell."""
    if not hasattr(canvas, "ghost_id"):
        canvas.ghost_id = None
    if canvas.ghost_id is not None:
        canvas.delete(canvas.ghost_id)
        canvas.ghost_id = None
    placement = getattr(canvas, "placement_cell", None)
    if placement is None:
        return
    row, col = placement
    current = getattr(canvas, "current_player", 0)
    assignment = getattr(canvas, "assignment", None)
    phase = getattr(canvas, "phase", "place")
    if phase == "bonus_place":
        placements_left = getattr(canvas, "bonus_place_remaining", 0)
    else:
        placements_left = getattr(canvas, "placements_remaining", 0)
    if assignment is None or placements_left <= 0:
        return
    cell_to_territory = getattr(canvas, "cell_to_territory", None)
    if cell_to_territory is None:
        return
    idx = cell_to_territory[(row, col)]
    if assignment[idx] != COLORS[current]:
        return
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        return
    if BRICK_LAYOUT:
        cell_w = w / (COLS + 0.5)
    else:
        cell_w = w / COLS
    cell_h = h / ROWS
    half = min(cell_w, cell_h) / 2
    r = half * PIECE_SIZE
    cx, cy = cell_center(cell_w, cell_h, row, col)
    canvas.ghost_id = canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=COLORS[current], outline="gray", width=2, stipple="gray50", tags="ghost")
    canvas.tag_raise("army_text")


def on_motion(canvas, event):
    cell = cell_from_xy(canvas, event.x, event.y)
    canvas.placement_cell = cell
    update_ghost(canvas)


def do_attack_phase_click(canvas, turn_label, root, row, col):
    cell_to_territory = canvas.cell_to_territory
    removed = canvas.removed
    idx = cell_to_territory[(row, col)]
    current = getattr(canvas, "current_player", 0)
    assignment = canvas.assignment
    armies = canvas.armies
    source = getattr(canvas, "attack_source", None)
    if source is None:
        if assignment[idx] != COLORS[current]:
            return
        if armies[idx] < 2:
            messagebox.showinfo("Attack", "You need at least 2 armies to attack from a territory.")
            return
        canvas.attack_source = (row, col)
        adj_indices = get_adjacent_territory_indices(canvas, idx)
        territory_to_cell = canvas.territory_to_cell
        canvas.attack_targets = {territory_to_cell[t] for t in adj_indices if assignment[t] != COLORS[current]}
        if not canvas.attack_targets:
            canvas.attack_source = None
            messagebox.showinfo("Attack", "No adjacent enemy territories.")
            return
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select adjacent enemy to attack")
        draw_grid(canvas)
        return
    if (row, col) == source:
        canvas.attack_source = None
        canvas.attack_targets = set()
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to attack from")
        draw_grid(canvas)
        return
    if (row, col) not in canvas.attack_targets:
        return
    target_idx = cell_to_territory[(row, col)]
    source_idx = cell_to_territory[source]
    max_attack = min(3, armies[source_idx] - 1)
    if max_attack < 1:
        canvas.attack_source = None
        canvas.attack_targets = set()
        draw_grid(canvas)
        return
    attacker_name = COLOR_NAMES[current]
    attack_prompt = f"{attacker_name}, should 1, 2, or 3 armies attack this territory?" if max_attack == 3 else (f"{attacker_name}, should 1 or 2 armies attack this territory?" if max_attack == 2 else f"{attacker_name}, should 1 army attack this territory?")
    n_attack = ask_attack_count(root, attack_prompt, 1, max_attack, blitz_context=(armies[source_idx], armies[target_idx]))
    if n_attack is None:
        return
    defender_color = assignment[target_idx]
    defender_name = COLOR_NAMES[COLORS.index(defender_color)]
    defender_idx = COLORS.index(defender_color)

    # Blitz mode: continue attacking until stop conditions, auto-defend with max
    if isinstance(n_attack, dict):
        blitz = n_attack
        stop_attacker = blitz["stop_attacker"]
        stop_defender = blitz["stop_defender"]
        armies_per_round = blitz["armies_per_round"]
        round_msgs = []
        captured = False
        while True:
            src = canvas.armies[source_idx]
            tgt = canvas.armies[target_idx]
            if src <= stop_attacker or tgt <= stop_defender:
                break
            n_attack_this = min(armies_per_round, src - 1)
            if n_attack_this < 1:
                break
            n_defend_this = min(2, tgt)
            canvas.armies[source_idx] -= n_attack_this
            ac, dc, attack_dice, defend_dice = resolve_battle(n_attack_this, n_defend_this)
            for d in attack_dice:
                canvas.dice_offense[current][d - 1] += 1
            for d in defend_dice:
                canvas.dice_defense[defender_idx][d - 1] += 1
            if hasattr(canvas, "update_dice_display"):
                canvas.update_dice_display()
            canvas.armies[target_idx] -= dc
            round_msgs.append(f"Round: Attacker {sorted(attack_dice, reverse=True)} vs Defender {sorted(defend_dice, reverse=True)} → Attacker lost {ac}, Defender lost {dc}.")
            captured = canvas.armies[target_idx] <= 0
            if captured:
                canvas.assignment[target_idx] = COLORS[current]
                canvas.armies[target_idx] = n_attack_this - ac
                canvas.conquered_this_turn = True
                defender_territories = sum(1 for c in canvas.assignment if c == defender_color)
                if defender_territories == 0:
                    eliminated = getattr(canvas, "eliminated_players", set())
                    eliminated.add(defender_idx)
                    canvas.eliminated_players = eliminated
                    canvas.player_cards[current].extend(canvas.player_cards[defender_idx])
                    canvas.player_cards[defender_idx] = []
                    canvas.armies[target_idx] += 8
                    if hasattr(canvas, "update_cards_display"):
                        canvas.update_cards_display()
                    messagebox.showinfo("Elimination", f"{defender_name} has been eliminated! {attacker_name} receives all their cards and 8 extra armies on the conquered territory.")
                break
            canvas.armies[source_idx] += (n_attack_this - ac)
        summary = "\n".join(round_msgs) if round_msgs else "No rounds fought (already at stop conditions)."
        if captured:
            summary += "\n\nTerritory captured!"
        messagebox.showinfo("Battle result", summary)
        canvas.attack_source = None
        canvas.attack_targets = set()
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to attack from")
        draw_grid(canvas)
        return

    # Single attack
    max_defend = min(2, armies[target_idx])
    defend_prompt = f"{defender_name}, you must use your 1 army stationed here to defend." if max_defend == 1 else f"{defender_name}, should 1 or 2 armies defend this territory?"
    n_defend = ask_defend_count(root, defend_prompt, 1, max_defend)
    if n_defend is None:
        return
    source_idx = cell_to_territory[source]
    canvas.armies[source_idx] -= n_attack
    ac, dc, attack_dice, defend_dice = resolve_battle(n_attack, n_defend)
    for d in attack_dice:
        canvas.dice_offense[current][d - 1] += 1
    for d in defend_dice:
        canvas.dice_defense[defender_idx][d - 1] += 1
    if hasattr(canvas, "update_dice_display"):
        canvas.update_dice_display()
    canvas.armies[target_idx] -= dc
    captured = canvas.armies[target_idx] <= 0
    if captured:
        canvas.assignment[target_idx] = COLORS[current]
        canvas.armies[target_idx] = n_attack - ac
        canvas.conquered_this_turn = True
        defender_territories = sum(1 for c in canvas.assignment if c == defender_color)
        if defender_territories == 0:
            eliminated = getattr(canvas, "eliminated_players", set())
            eliminated.add(defender_idx)
            canvas.eliminated_players = eliminated
            canvas.player_cards[current].extend(canvas.player_cards[defender_idx])
            canvas.player_cards[defender_idx] = []
            canvas.armies[target_idx] += 8
            if hasattr(canvas, "update_cards_display"):
                canvas.update_cards_display()
            messagebox.showinfo("Elimination", f"{defender_name} has been eliminated! {attacker_name} receives all their cards and 8 extra armies on the conquered territory.")
    else:
        canvas.armies[source_idx] += (n_attack - ac)
    msg = f"Attacker rolled: {sorted(attack_dice, reverse=True)}\nDefender rolled: {sorted(defend_dice, reverse=True)}\nAttacker lost {ac}, Defender lost {dc}."
    if captured:
        msg += "\nTerritory captured!"
    messagebox.showinfo("Battle result", msg)
    canvas.attack_source = None
    canvas.attack_targets = set()
    turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to attack from")
    draw_grid(canvas)


def do_move_phase_click(canvas, turn_label, root, row, col):
    cell_to_territory = canvas.cell_to_territory
    removed = canvas.removed
    current = getattr(canvas, "current_player", 0)
    assignment = canvas.assignment
    armies = canvas.armies
    player_color = COLORS[current]
    source = getattr(canvas, "move_source", None)
    if source is None:
        idx = cell_to_territory[(row, col)]
        if assignment[idx] != player_color:
            return
        if armies[idx] < 2:
            messagebox.showinfo("Move", "You need at least 2 armies in a territory to move from it.")
            return
        canvas.move_source = (row, col)
        reachable = reachable_from(player_color, row, col, assignment, cell_to_territory, canvas.territory_to_cell, removed, canvas.bridge_neighbors)
        reachable.discard((row, col))
        canvas.move_targets = reachable
        if not canvas.move_targets:
            canvas.move_source = None
            messagebox.showinfo("Move", "No other territory reachable from here (only your own territories).")
            return
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select destination territory to move to")
        draw_grid(canvas)
        return
    if (row, col) == source:
        canvas.move_source = None
        canvas.move_targets = set()
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to move from")
        draw_grid(canvas)
        return
    if (row, col) not in canvas.move_targets:
        return
    source_idx = cell_to_territory[source]
    dest_idx = cell_to_territory[(row, col)]
    max_move = armies[source_idx] - 1
    player_name = COLOR_NAMES[current]
    prompt = f"{player_name}, how many armies move to this territory? (1–{max_move})"
    n_move = ask_move_count(root, prompt, 1, max_move)
    if n_move is None:
        return
    canvas.armies[source_idx] -= n_move
    canvas.armies[dest_idx] += n_move
    canvas.move_source = None
    canvas.move_targets = set()
    turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to move from (or End turn)")
    draw_grid(canvas)


def on_click(canvas, turn_label, root, event):
    cell = cell_from_xy(canvas, event.x, event.y)
    if cell is None:
        return
    row, col = cell
    cell_to_territory = getattr(canvas, "cell_to_territory", None)
    if cell_to_territory is None:
        return
    idx = cell_to_territory[(row, col)]
    current = getattr(canvas, "current_player", 0)
    assignment = getattr(canvas, "assignment", [])
    phase = getattr(canvas, "phase", "place")
    if phase == "attack":
        do_attack_phase_click(canvas, turn_label, root, row, col)
        return
    if phase == "move":
        do_move_phase_click(canvas, turn_label, root, row, col)
        return
    if phase == "bonus_place":
        if assignment[idx] != COLORS[current]:
            return
        bonus = getattr(canvas, "bonus_place_remaining", 0)
        if bonus <= 0:
            return
        canvas.armies[idx] += 1
        canvas.bonus_place_remaining -= 1
        draw_grid(canvas)
        if canvas.bonus_place_remaining > 0:
            turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — place {canvas.bonus_place_remaining} armies (set turn-in)")
        else:
            advance_to_next_player(canvas, turn_label)
        return
    if phase != "place":
        return
    if assignment[idx] != COLORS[current]:
        return
    placements = getattr(canvas, "placements_remaining", 0)
    if placements <= 0:
        return
    canvas.armies[idx] += 1
    canvas.placements_remaining -= 1
    draw_grid(canvas)
    placements = canvas.placements_remaining
    if placements > 0:
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — place {placements} more")
    else:
        canvas.phase = "attack"
        canvas.attack_source = None
        canvas.attack_targets = set()
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to attack from")
        if hasattr(canvas, "end_turn_btn") and canvas.end_turn_btn.winfo_exists():
            canvas.end_turn_btn.config(text="Done attacking")
            canvas.end_turn_btn.pack(side=tk.LEFT, padx=4)


def on_resize(event):
    draw_grid(event.widget)


def _set_two_player_mode():
    """Set globals for 2 players: 27 territories in 8×8 grid (1st: 12, 2nd: 15)."""
    global ROWS, COLS, TOTAL, NUM_CAPITALS, REMOVED_COUNT, COLORS, COLOR_NAMES
    ROWS, COLS = 8, 8
    TOTAL = 27
    NUM_CAPITALS = 4
    REMOVED_COUNT = 64 - 27
    COLORS = ["#e74c3c", "#3498db"]
    COLOR_NAMES = ["Red", "Blue"]


def _set_three_player_mode():
    """Set globals for 3 players: 44 territories in 10×10 grid (12, 15, 17)."""
    global ROWS, COLS, TOTAL, NUM_CAPITALS, REMOVED_COUNT, COLORS, COLOR_NAMES
    ROWS, COLS = 10, 10
    TOTAL = 44
    NUM_CAPITALS = 6
    REMOVED_COUNT = 100 - 44
    COLORS = ["#e74c3c", "#3498db", "#2ecc71"]
    COLOR_NAMES = ["Red", "Blue", "Green"]


def _set_four_player_mode():
    """Set globals for 4 players: 62 territories in 12×12 grid, 8 continents (12, 15, 17, 18)."""
    global ROWS, COLS, TOTAL, NUM_CAPITALS, REMOVED_COUNT, COLORS, COLOR_NAMES
    ROWS, COLS = 12, 12
    TOTAL = 62
    NUM_CAPITALS = 8
    REMOVED_COUNT = 144 - 62
    COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f"]
    COLOR_NAMES = ["Red", "Blue", "Green", "Yellow"]


_SAVE_COLS = {2: 8, 3: 10, 4: 12}
# Current save format written by save_game_state.
SAVE_FORMAT_VERSION = 3
# One letter per player index (matches COLOR_NAMES order: Red, Blue, Green, Yellow)
_ASSIGNMENT_LETTERS = "RBGY"


def _assignment_to_letters(assignment):
    return "".join(_ASSIGNMENT_LETTERS[COLORS.index(c)] for c in assignment)


def _letters_to_assignment(s_a):
    """Restore hex colors from compact letter string (must be str of length TOTAL)."""
    lut = {_ASSIGNMENT_LETTERS[i]: COLORS[i] for i in range(len(COLORS))}
    return [lut[c] for c in s_a]


def _set_loaded_player_colors(mode, compact_save):
    """
    For compact saves:
    - if colors are present, use them;
    - if not present (older v3), auto-fill from current mode defaults.
    """
    global COLORS
    saved_colors = compact_save.get("P")
    if saved_colors is not None:
        if not isinstance(saved_colors, list) or len(saved_colors) != mode:
            raise ValueError("Invalid saved colors (P): expected a list with one color per player.")
        COLORS = list(saved_colors)
        return
    # Keep colors set by _set_*_player_mode and write them back into save data.
    compact_save["P"] = list(COLORS)


def _lin(cols, r, c):
    return r * cols + c


def _cell(cols, i):
    return divmod(int(i), cols)


def _expand_compact_save(s):
    """Compact wire-format (v2/v3) -> dict shape expected by _run_game."""
    cols = _SAVE_COLS[s["m"]]
    rc = lambda i: list(_cell(cols, i))
    c2t = {}
    for k, v in s["c"].items():
        r, c = _cell(cols, k)
        c2t[f"{r},{c}"] = v
    assignment_letters = s.get("a")
    if assignment_letters is None:
        # Missing ownership field: randomize territory colors on load.
        assignment = [random.choice(COLORS) for _ in range(len(s["t"]))]
    else:
        assignment = _letters_to_assignment(assignment_letters)
    return {
        "version": s.get("v", 2),
        "mode": s["m"],
        "removed": [rc(i) for i in s["R"]],
        "cell_to_territory": c2t,
        "territory_to_cell": [rc(i) for i in s["t"]],
        "capitals": s["C"],
        "continents": s["o"],
        "capital_territory_for_continent": s["k"],
        "territory_names": s["n"],
        "bridge_edges": s["b"],
        "wrap_bridge_edges": s.get("W", []),
        "bridge_neighbors": s["N"],
        "assignment": assignment,
        "armies": s["y"],
        "current_player": s["p"],
        "phase": s["h"],
        "conquered_this_turn": s["q"],
        "eliminated_players": s["e"],
        "player_cards": s["d"],
        "set_turn_in_count": s["i"],
        "placements_remaining": s["l"],
        "bonus_place_remaining": s.get("B", 0),
        "dice_offense": s["O"],
        "dice_defense": s["D"],
        "attack_source": s["A"],
        "attack_targets": [rc(i) for i in s.get("T", [])],
        "move_source": s["M"],
        "move_targets": [rc(i) for i in s.get("U", [])],
        **({"winner": s["w"]} if "w" in s else {}),
    }


def _expand_save_format_v2(s):
    """Wire-format v=2 -> dict shape expected by _run_game."""
    return _expand_compact_save(s)


def _expand_save_format_v3(s):
    """Wire-format v=3 -> dict shape expected by _run_game."""
    return _expand_compact_save(s)


def save_game_state(canvas):
    """Return a compact JSON-serializable dict (SAVE_FORMAT_VERSION: short keys, linear indices, letter assignment)."""
    cols = COLS
    ln = lambda r, c: _lin(cols, r, c)
    targets = lambda s: sorted(ln(r, c) for (r, c) in s)
    state = {
        "v": SAVE_FORMAT_VERSION,
        "m": len(COLORS),
        "R": [ln(r, c) for (r, c) in canvas.removed],
        "c": {str(ln(r, c)): v for (r, c), v in canvas.cell_to_territory.items()},
        "t": [ln(r, c) for (r, c) in canvas.territory_to_cell],
        "C": list(canvas.capitals),
        "o": list(canvas.continents),
        "k": list(canvas.capital_territory_for_continent),
        "n": list(canvas.territory_names),
        "b": [list(p) for p in canvas.bridge_edges],
        "W": [list(p) for p in getattr(canvas, "wrap_bridge_edges", [])],
        "N": [list(x) for x in canvas.bridge_neighbors],
        "P": list(COLORS),
        "a": _assignment_to_letters(canvas.assignment),
        "y": list(canvas.armies),
        "p": canvas.current_player,
        "h": canvas.phase,
        "q": canvas.conquered_this_turn,
        "e": list(canvas.eliminated_players),
        "d": [list(h) for h in canvas.player_cards],
        "i": canvas.set_turn_in_count,
        "l": getattr(canvas, "placements_remaining", 0),
        "B": getattr(canvas, "bonus_place_remaining", 0),
        "O": [list(row) for row in canvas.dice_offense],
        "D": [list(row) for row in canvas.dice_defense],
        "A": list(canvas.attack_source) if getattr(canvas, "attack_source", None) else None,
        "T": targets(getattr(canvas, "attack_targets", set())),
        "M": list(canvas.move_source) if getattr(canvas, "move_source", None) else None,
        "U": targets(getattr(canvas, "move_targets", set())),
    }
    eliminated = canvas.eliminated_players
    np = len(COLORS)
    if len(eliminated) >= np - 1:
        state["w"] = next(p for p in range(np) if p not in eliminated)
    return state


def _decode_save(data):
    """Dispatch on save format version; returns dict for _run_game."""
    v = data.get("v")
    if v is None:
        raise ValueError(
            "Save has no format version (field \"v\"). Supported versions: v=2 or v=3."
        )
    if v not in (2, 3):
        raise ValueError(
            f"Unsupported save format v={v!r}. Supported versions: v=2 or v=3."
        )
    mode = data["m"]
    if mode == 2:
        _set_two_player_mode()
    elif mode == 3:
        _set_three_player_mode()
    elif mode == 4:
        _set_four_player_mode()
    else:
        raise ValueError(f"Invalid player count in save (m): {mode!r}.")
    # For compact v3 saves, apply saved colors if present; otherwise regenerate random colors.
    if v == 3:
        _set_loaded_player_colors(mode, data)
    if v == 2:
        return _expand_save_format_v2(data)
    return _expand_save_format_v3(data)


def load_game_state(s):
    """Parse JSON, set mode globals, decode save. Returns dict for _run_game."""
    data = json.loads(s) if isinstance(s, str) else s
    return _decode_save(data)


def _run_game(root, saved_state=None, on_go_to_menu=None):
    """Build the game UI on the given root (current ROWS, COLS, TOTAL, COLORS must be set by mode)."""
    root.title("Risk")
    root.geometry("")  # clear launcher size
    root.resizable(True, True)
    def exit_fullscreen(e=None):
        root.attributes("-fullscreen", False)
    root.bind_all("<Escape>", exit_fullscreen)
    root.bind_all("<f>", exit_fullscreen)
    root.bind_all("<F>", exit_fullscreen)
    root.bind_all("<F11>", lambda e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
    turn_label = tk.Label(root, text="Red's turn", font=("Helvetica", 24), fg="#c0392b")
    turn_label.pack(pady=10)
    content = tk.Frame(root)
    content.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(content, bg="white", highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    num_players = len(COLORS)
    if saved_state:
        s = saved_state
        canvas.territory_names = s["territory_names"]
        canvas.removed = set(tuple(c) for c in s["removed"])
        canvas.cell_to_territory = {tuple(int(x) for x in k.split(",")): v for k, v in s["cell_to_territory"].items()}
        canvas.territory_to_cell = [tuple(c) for c in s["territory_to_cell"]]
        canvas.capitals = set(s["capitals"])
        canvas.continents = s["continents"]
        canvas.capital_territory_for_continent = s["capital_territory_for_continent"]
        canvas.assignment = s["assignment"]
        canvas.bridge_edges = [tuple(p) for p in s["bridge_edges"]]
        canvas.wrap_bridge_edges = [tuple(p) for p in s.get("wrap_bridge_edges", [])]
        canvas.bridge_neighbors = [set(n) for n in s["bridge_neighbors"]]
        canvas.armies = s["armies"]
        canvas.current_player = s["current_player"]
        canvas.phase = s["phase"]
        canvas.conquered_this_turn = s["conquered_this_turn"]
        canvas.eliminated_players = set(s["eliminated_players"])
        canvas.player_cards = [list(h) for h in s["player_cards"]]
        canvas.set_turn_in_count = s["set_turn_in_count"]
        canvas.placements_remaining = s["placements_remaining"]
        canvas.bonus_place_remaining = s.get("bonus_place_remaining", 0)
        canvas.dice_offense = [list(r) for r in s.get("dice_offense", [[0]*6]*num_players)]
        canvas.dice_defense = [list(r) for r in s.get("dice_defense", [[0]*6]*num_players)]
        canvas.attack_source = tuple(s["attack_source"]) if s.get("attack_source") else None
        canvas.attack_targets = set(tuple(c) for c in s.get("attack_targets", []))
        canvas.move_source = tuple(s["move_source"]) if s.get("move_source") else None
        canvas.move_targets = set(tuple(c) for c in s.get("move_targets", []))
        canvas._bridge_computed_for = True
    else:
        canvas.territory_names = make_territory_names()
        removed, cell_to_territory, territory_to_cell, capitals, continents, capital_territory_for_continent = make_playable_region()
        canvas.removed = removed
        canvas.cell_to_territory = cell_to_territory
        canvas.territory_to_cell = territory_to_cell
        canvas.capitals = capitals
        canvas.continents = continents
        canvas.capital_territory_for_continent = capital_territory_for_continent
        canvas.assignment = make_assignment(continents)
        canvas.bridge_neighbors = [set() for _ in range(TOTAL)]
        canvas.bridge_edges = []
        canvas.wrap_bridge_edges = []
        canvas.armies = [1] * TOTAL
        canvas.current_player = 0
        canvas.phase = "place"
        canvas.conquered_this_turn = False
        canvas.eliminated_players = set()
        canvas.player_cards = [[] for _ in range(num_players)]
        canvas.dice_offense = [[0] * 6 for _ in range(num_players)]
        canvas.dice_defense = [[0] * 6 for _ in range(num_players)]
        canvas.set_turn_in_count = 0
        canvas.placements_remaining = armies_per_turn(canvas, 0)
        canvas.bonus_place_remaining = 0
        canvas.attack_source = None
        canvas.attack_targets = set()
        canvas.move_source = None
        canvas.move_targets = set()

    # Right panel: continent color, capital, bonus armies (floor(territories/2))
    # Width must fit dice table: 1 + 2*num_players columns (e.g. 3 players = 7 cols)
    right_panel_width = 240 + (num_players - 2) * 90 if num_players > 2 else 240
    right_panel = tk.Frame(content, width=right_panel_width, bg="#f5f5f5", padx=12, pady=12)
    right_panel.pack(side=tk.RIGHT, fill=tk.Y)
    right_panel.pack_propagate(False)
    tk.Label(right_panel, text="Continents", font=("Helvetica", 16, "bold"), bg="#f5f5f5").pack(anchor=tk.W, pady=(0, 12))
    territory_names_list = canvas.territory_names
    capital_territory = getattr(canvas, "capital_territory_for_continent", None)
    for cid in range(NUM_CAPITALS):
        count = sum(1 for i in range(TOTAL) if canvas.continents[i] == cid)
        if count == 0:
            continue
        bonus = count // 2
        capital_idx = capital_territory[cid] if capital_territory and cid < len(capital_territory) else None
        capital_name = territory_names_list[capital_idx] if capital_idx is not None and capital_idx < len(territory_names_list) else "—"
        box = tk.Frame(right_panel, bg="white", relief=tk.RIDGE, borderwidth=2, padx=8, pady=8)
        box.pack(fill=tk.X, pady=6)
        tk.Frame(box, width=24, height=24, bg=CONTINENT_BORDER_COLORS[cid % len(CONTINENT_BORDER_COLORS)], relief=tk.SUNKEN, borderwidth=1).pack(side=tk.LEFT, padx=(0, 8), pady=4)
        inner = tk.Frame(box, bg="white")
        inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(inner, text=f"Capital: {capital_name}", font=("Helvetica", 11), bg="white", anchor=tk.W).pack(anchor=tk.W)
        tk.Label(inner, text=f"Bonus: +{bonus} armies if owned", font=("Helvetica", 10), bg="white", fg="#555", anchor=tk.W).pack(anchor=tk.W)
    tk.Label(right_panel, text="Cards", font=("Helvetica", 16, "bold"), bg="#f5f5f5").pack(anchor=tk.W, pady=(16, 8))
    cards_frame = tk.Frame(right_panel, bg="#f5f5f5")
    cards_frame.pack(fill=tk.X)
    canvas.cards_frame = cards_frame
    tk.Label(right_panel, text="Dice rolls", font=("Helvetica", 16, "bold"), bg="#f5f5f5").pack(anchor=tk.W, pady=(16, 8))
    dice_frame = tk.Frame(right_panel, bg="#f5f5f5")
    dice_frame.pack(fill=tk.X)
    canvas.dice_frame = dice_frame
    canvas.continent_panel = right_panel
    if not saved_state:
        canvas.placements_remaining = armies_per_turn(canvas, 0)
    from collections import Counter
    def update_cards_display():
        for w in canvas.cards_frame.winfo_children():
            w.destroy()
        for i in range(num_players):
            eliminated = getattr(canvas, "eliminated_players", set())
            if i in eliminated:
                row = tk.Frame(canvas.cards_frame, bg="#f5f5f5")
                row.pack(fill=tk.X, pady=4)
                tk.Frame(row, width=20, height=20, bg=COLORS[i], relief=tk.SUNKEN, borderwidth=1).pack(side=tk.LEFT, padx=(0, 8), pady=2)
                tk.Label(row, text=f"{COLOR_NAMES[i]} — eliminated", font=("Helvetica", 11), bg="#f5f5f5", fg="#888").pack(anchor=tk.W)
                continue
            c = Counter(canvas.player_cards[i])
            cannon = c.get("CANNON", 0)
            horse = c.get("HORSE", 0)
            infantry = c.get("INFANTRY", 0)
            row = tk.Frame(canvas.cards_frame, bg="#f5f5f5")
            row.pack(fill=tk.X, pady=4)
            tk.Frame(row, width=20, height=20, bg=COLORS[i], relief=tk.SUNKEN, borderwidth=1).pack(side=tk.LEFT, padx=(0, 8), pady=2)
            tk.Label(row, text=f"{COLOR_NAMES[i]}: Cannon {cannon}, Horse {horse}, Infantry {infantry}", font=("Helvetica", 11), bg="#f5f5f5", anchor=tk.W).pack(anchor=tk.W)
    canvas.update_cards_display = update_cards_display
    update_cards_display()

    def update_dice_display():
        for w in canvas.dice_frame.winfo_children():
            w.destroy()
        eliminated = getattr(canvas, "eliminated_players", set())
        font = ("Helvetica", 10)
        # Header row: empty corner, then per player "Name off", "Name def"
        tk.Label(canvas.dice_frame, text="", font=font, bg="#f5f5f5", width=3).grid(row=0, column=0, padx=2, pady=1)
        for col, i in enumerate(range(num_players)):
            c = 1 + col * 2
            tk.Label(canvas.dice_frame, text=f"{COLOR_NAMES[i]} off", font=font, bg=COLORS[i], fg="white" if i not in eliminated else "#888").grid(row=0, column=c, padx=2, pady=1)
            tk.Label(canvas.dice_frame, text=f"{COLOR_NAMES[i]} def", font=font, bg=COLORS[i], fg="white" if i not in eliminated else "#888").grid(row=0, column=c + 1, padx=2, pady=1)
        # Data rows: 1s, 2s, ..., 6s
        for face in range(1, 7):
            tk.Label(canvas.dice_frame, text=f"{face}s", font=font, bg="#f5f5f5").grid(row=face, column=0, padx=2, pady=1, sticky=tk.W)
            for col, i in enumerate(range(num_players)):
                c = 1 + col * 2
                off = canvas.dice_offense[i][face - 1]
                defe = canvas.dice_defense[i][face - 1]
                tk.Label(canvas.dice_frame, text=str(off), font=font, bg="#f5f5f5").grid(row=face, column=c, padx=2, pady=1)
                tk.Label(canvas.dice_frame, text=str(defe), font=font, bg="#f5f5f5", fg="#555").grid(row=face, column=c + 1, padx=2, pady=1)
    canvas.update_dice_display = update_dice_display
    update_dice_display()
    if not saved_state:
        canvas.set_turn_in_count = 0
        canvas.placements_remaining = armies_per_turn(canvas, 0)
    current = canvas.current_player
    phase = canvas.phase
    if phase == "place":
        n = getattr(canvas, "placements_remaining", 0)
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — place {n} armies" if n > 0 else f"{COLOR_NAMES[current]}'s turn — select territory to attack from")
    elif phase == "attack":
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to attack from")
    elif phase == "move":
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to move from (or End turn)")
    elif phase == "bonus_place":
        n = getattr(canvas, "bonus_place_remaining", 0)
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — place {n} armies (set turn-in)")
    else:
        turn_label.config(text=f"{COLOR_NAMES[current]}'s turn")
    winner = saved_state.get("winner") if saved_state else None
    if winner is not None:
        turn_label.config(text=f"{COLOR_NAMES[winner]} wins!")
    def end_turn():
        phase = getattr(canvas, "phase", "place")
        if phase == "attack":
            canvas.attack_source = None
            canvas.attack_targets = set()
            canvas.phase = "move"
            canvas.move_source = None
            canvas.move_targets = set()
            current = canvas.current_player
            turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — select territory to move from (or End turn)")
            end_turn_btn.config(text="End turn")
            draw_grid(canvas)
            return
        if phase != "move":
            return
        canvas.move_source = None
        canvas.move_targets = set()
        current = canvas.current_player
        if getattr(canvas, "conquered_this_turn", False):
            messagebox.showinfo("Conquest", "Congratulations! You conquered a territory during your turn!")
            card = random.choice(CARD_TYPES)
            canvas.player_cards[current].append(card)
            messagebox.showinfo("Card", f"You drew: {card}")
            canvas.conquered_this_turn = False
            canvas.update_cards_display()
        hand = canvas.player_cards[current]
        has_set, to_remove = has_valid_set(hand)
        if len(hand) > 6 and has_set and to_remove:
            messagebox.showinfo("Mandatory turn-in", "You have more than 6 cards and must turn in a set.")
            remove_set_from_hand(hand, to_remove)
            n_bonus = get_bonus_armies(canvas.set_turn_in_count)
            canvas.set_turn_in_count += 1
            canvas.phase = "bonus_place"
            canvas.bonus_place_remaining = n_bonus
            end_turn_btn.pack_forget()
            turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — place {n_bonus} armies (mandatory set turn-in)")
            canvas.update_cards_display()
            draw_grid(canvas)
            return
        if has_set and to_remove and messagebox.askyesno("Turn in set", f"You have a valid set (3 same or 1 of each). Turn in for {get_bonus_armies(canvas.set_turn_in_count)} armies?"):
            remove_set_from_hand(hand, to_remove)
            n_bonus = get_bonus_armies(canvas.set_turn_in_count)
            canvas.set_turn_in_count += 1
            canvas.phase = "bonus_place"
            canvas.bonus_place_remaining = n_bonus
            end_turn_btn.pack_forget()
            turn_label.config(text=f"{COLOR_NAMES[current]}'s turn — place {n_bonus} armies (set turn-in)")
            canvas.update_cards_display()
            draw_grid(canvas)
            return
        advance_to_next_player(canvas, turn_label)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=2)
    def do_save():
        state = save_game_state(canvas)
        save_str = json.dumps(state, separators=(",", ":"))
        win = tk.Toplevel(root)
        win.title("Save game — copy text below")
        win.geometry("500x400")
        txt = tk.Text(win, wrap=tk.WORD, font=("Consolas", 10))
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt.insert("1.0", save_str)
        txt.focus_set()
        def copy_and_close():
            root.clipboard_clear()
            root.clipboard_append(txt.get("1.0", tk.END))
            root.update()
            win.destroy()
        tk.Button(win, text="Copy to clipboard", font=("Helvetica", 12), command=copy_and_close).pack(pady=8)
    tk.Button(btn_frame, text="Save game", font=("Helvetica", 12), command=do_save).pack(side=tk.LEFT, padx=4)
    if on_go_to_menu:
        def open_main_menu_popup():
            popup = tk.Toplevel(root)
            popup.withdraw()
            popup.title("Main menu")
            popup.transient(root)
            popup.resizable(False, False)
            box = tk.Frame(popup, padx=10, pady=10)
            box.pack()
            tk.Label(box, text="Main menu", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))

            def close_popup():
                if popup.winfo_exists():
                    popup.destroy()

            def go_to_menu_and_close():
                close_popup()
                on_go_to_menu()

            tk.Button(box, text="Return to title", font=("Helvetica", 11), command=go_to_menu_and_close).pack(fill=tk.X, pady=2)
            tk.Button(box, text="Cancel", font=("Helvetica", 11), command=close_popup).pack(fill=tk.X, pady=2)
            popup.bind("<FocusOut>", lambda e: close_popup())
            popup.protocol("WM_DELETE_WINDOW", close_popup)
            popup.update_idletasks()
            bx = main_menu_btn.winfo_rootx()
            by = main_menu_btn.winfo_rooty() + main_menu_btn.winfo_height() + 4
            popup.geometry(f"+{bx}+{by}")
            popup.deiconify()
            popup.focus_force()

        main_menu_btn = tk.Button(btn_frame, text="Main menu", font=("Helvetica", 12), command=open_main_menu_popup)
        main_menu_btn.pack(side=tk.LEFT, padx=4)
    end_turn_btn = tk.Button(btn_frame, text="Done attacking", font=("Helvetica", 14), command=end_turn)
    canvas.end_turn_btn = end_turn_btn
    if saved_state and saved_state.get("winner") is None and canvas.phase in ("attack", "move"):
        end_turn_btn.config(text="Done attacking" if canvas.phase == "attack" else "End turn")
        end_turn_btn.pack(side=tk.LEFT, padx=4)
    canvas.bind("<Configure>", on_resize)
    canvas.bind("<Motion>", lambda e: on_motion(canvas, e))
    canvas.bind("<Button-1>", lambda e: on_click(canvas, turn_label, root, e))
    if not saved_state:
        canvas.phase = "place"

    def go_fullscreen_then_draw():
        try:
            root.attributes("-fullscreen", True)
        except tk.TclError:
            pass
        try:
            root.state("zoomed")  # Windows maximized fallback
        except tk.TclError:
            pass
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        if w > 1 and h > 1:
            root.geometry(f"{w}x{h}+0+0")
        draw_grid(canvas)
    root.after(100, go_fullscreen_then_draw)


def main():
    """Show mode selection fullscreen; after choice, game stays fullscreen on same window."""
    root = tk.Tk()
    root.title("Risk — Choose Mode")
    root.attributes("-fullscreen", True)
    def exit_fullscreen(e=None):
        root.attributes("-fullscreen", False)
    root.bind_all("<Escape>", exit_fullscreen)
    root.bind_all("<f>", exit_fullscreen)
    root.bind_all("<F>", exit_fullscreen)
    while True:
        choice = tk.StringVar()
        loaded_state = [None]
        tk.Label(root, text="Select number of players", font=("Helvetica", 24)).pack(pady=40)
        frame = tk.Frame(root)
        frame.pack(pady=20)
        def start_two():
            _set_two_player_mode()
            choice.set("2")
        def start_three():
            _set_three_player_mode()
            choice.set("3")
        def start_four():
            _set_four_player_mode()
            choice.set("4")
        def do_load():
            win = tk.Toplevel(root)
            win.title("Load game — paste save text")
            win.geometry("500x400")
            txt = tk.Text(win, wrap=tk.WORD, font=("Consolas", 10))
            txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            txt.focus_set()
            def try_load():
                s = txt.get("1.0", tk.END).strip()
                if not s:
                    messagebox.showwarning("Load", "Paste your save text first.")
                    return
                try:
                    loaded_state[0] = load_game_state(s)
                    win.destroy()
                    choice.set("load")
                except Exception as e:
                    messagebox.showerror("Load failed", str(e))
            tk.Button(win, text="Load game", font=("Helvetica", 12), command=try_load).pack(pady=8)
        tk.Button(frame, text="2 Player — 8×8 (27 territories: 12+15)", font=("Helvetica", 18), command=start_two, width=36).pack(pady=12)
        tk.Button(frame, text="3 Player — 10×10 (44 territories: 12+15+17)", font=("Helvetica", 18), command=start_three, width=36).pack(pady=12)
        tk.Button(frame, text="4 Player — 12×12 (62 territories: 12+15+17+18)", font=("Helvetica", 18), command=start_four, width=36).pack(pady=12)
        tk.Button(frame, text="Load game", font=("Helvetica", 18), command=do_load, width=36).pack(pady=12)
        root.wait_variable(choice)
        for w in root.winfo_children():
            w.destroy()
        return_to_menu = [False]
        def go_to_menu():
            return_to_menu[0] = True
            root.quit()
        _run_game(root, saved_state=loaded_state[0] if choice.get() == "load" else None, on_go_to_menu=go_to_menu)
        root.mainloop()
        if not return_to_menu[0]:
            break


if __name__ == "__main__":
    main()
