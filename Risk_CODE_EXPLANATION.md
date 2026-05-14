# Risk.py — Code Explanation

This document walks through the Risk-style board game: mode selection, grid, brick layout, continents, bridges, placement, attack (including blitz), move, cards, player elimination, continent outlines, save/load, and main menu.

---

## 1. Overview and Structure

- **UI**: Tkinter; fullscreen mode selection, then a label, canvas (board + right panel), and “End turn” / “Done attacking” / “Save game” / “Main menu”.
- **Game state** is stored on the **canvas** (e.g. `canvas.assignment`, `canvas.armies`, `canvas.phase`, `canvas.continents`, `canvas.eliminated_players`).
- **Dialogs**: Attack, defend, and move count dialogs are placed in the **bottom-right corner** via **`_place_dialog_bottom_right`** (window is withdrawn until positioned, then deiconified).
- **Spinbox note (Python 3.13+)**: **`_select_all`** uses **`selection_range`** when present (Spinbox), else **`select_range`** (Entry). Count dialogs parse counts with **`int(float(...))`** so values like `"2."` still work.
- **Territories** are indexed **0 to TOTAL−1**. TOTAL depends on mode: **27** (2-player), **44** (3-player), **62** (4-player). The board is a grid (8×8, 10×10, or 12×12) with some cells removed; the rest are playable territories. Mapping: `cell_to_territory`, `territory_to_cell`, `removed`.

---

## 2. Constants and Modes

- **ROWS, COLS, TOTAL, NUM_CAPITALS**: Set per mode (see below).
- **COLORS** / **COLOR_NAMES**: 2 players = Red, Blue; 3 = + Green; 4 = + Yellow.
- **CARD_TYPES**: Cannon, Horse, Infantry.
- **PIECE_SIZE**: 0.7 (piece radius as fraction of half the smaller cell dimension).
- **CONTINENT_BORDER_COLORS**: 8 colors for continent outlines (no red/blue so they don’t match player colors).
- **`SAVE_FORMAT_VERSION`**: Current on-disk save format (3). Loader writes v3; loader accepts v2/v3; bump when the JSON shape changes and extend **`_decode_save`**.

**Mode selection (`main`, `_set_xxx_player_mode`):**

- **2 player**: 8×8 grid, **27** territories (12+15), **4** continents.
- **3 player**: 10×10 grid, **44** territories (12+15+17), **6** continents.
- **4 player**: 12×12 grid, **62** territories (12+15+17+18), **8** continents.

---

## 3. Territory Name Generation

- Names use **syllable blocks** (CV or CVC); **1, 2, or 3 blocks** per name (no 4-block names).
- **`make_territory_names()`**: Returns **TOTAL** unique names.

---

## 4. Cards and Set Turn-In

- **`get_bonus_armies(turn_in_index)`**: 4, 6, 8, …, 16 for 1st–7th+ turn-in.
- **`has_valid_set(cards)`**: Valid set = one of each type or three of the same.
- **Mandatory turn-in**: If a player has **more than 6 cards** and a valid set, they **must** turn in before ending the turn.
- **`advance_to_next_player`**: Skips eliminated players; if only one remains, shows “X wins!” and hides End turn. Otherwise sets **`placements_remaining`** via **`armies_per_turn`** (see below).

---

## 5. Armies per Turn

- **`armies_per_turn(canvas, player_index)`**:
  - Base: **floor(territories_owned / 3)**.
  - Plus **continent bonus**: for each continent the player **fully** owns, add **floor(continent_size / 2)**.
- Used at start of each turn and for the first player’s initial placements.

---

## 6. Playable Region and Continents (`make_playable_region`)

- **Capitals**: **`NUM_CAPITALS`** seeds are chosen so **no two capitals are brick-adjacent** (**`_adjacent_cells_raw`**): greedy pick from a shuffled cell list with a forbidden set (capital + neighbors).
- **Growth**: From those seeds, random frontier expansion until exactly **TOTAL** playable cells; if growth stalls before TOTAL, retry with new capitals (outer loop).
- **Minimum size 4**: After growth, a **steal** pass moves border cells from larger continents into continents that still have fewer than **4** territories. **Capital cells are never stolen** (they stay on their starting continent).
- **Player-count size band (when feasible)**: If **TOTAL** can be partitioned with each continent between **`num_players`** and **`floor(3.5 * num_players)`** territories (with **`num_players = len(COLORS)`** at generation time), the whole map is **rejected and regenerated** until every continent’s size lies in that range. If that band is **impossible** for the mode (e.g. 2-player 27 territories across 4 continents cannot all be ≤ 5), this check is **skipped** so generation can still finish.
- **Hard cap**: After many failed attempts, raises **`RuntimeError`** instead of looping forever.
- Returns: **`removed`**, **`cell_to_territory`**, **`territory_to_cell`**, **`capitals`**, **`continents`**, **`capital_territory_for_continent`** (capital territory index per continent for the right panel).

---

## 7. Assignment (`make_assignment`)

- Gives **12, 15, 17, 18** to players 0–3 (only the first `num_players` counts are used).
- Shuffles territory indices, then assigns the first 12 to player 0, next 15 to player 1, etc.
- Then fixes **3/4 rule**: no player may own more than **floor(0.75 × size)** of any continent; swaps territories across continents to fix violations while keeping the same per-player totals.

---

## 8. Bridges

- **`compute_bridges(canvas, cell_w, cell_h)`**: Runs **once per game** (so connections don’t change on resize). Finds connected components using only physical adjacency; repeatedly adds the **nearest** pair of territories in different components whose connecting segment doesn’t intersect any other territory rectangle (pixel geometry). Tie-break: lexicographically smallest (i, j).
- **Warp bridges (left/right wrap)**: For each row, if both edge cells are land (`(row, 0)` and `(row, COLS-1)` exist), a wrap bridge is added between them. These are stored in **`canvas.wrap_bridge_edges`** and also included in **`canvas.bridge_neighbors`**, so attack/move connectivity wraps horizontally.
- Drawing: normal bridges are center-to-center lines. Wrap bridges are drawn as two short segments from the two territories out to the left/right screen edges, visually indicating horizontal wrap.
- Adjacency (attack/move) uses **`get_adjacent_territory_indices`** (physical + all bridges, including wrap bridges).

---

## 9. Continent Boundary Outlines

- **`_continent_boundary_loops(cell_w, cell_h, removed, cell_to_territory, continents)`**:
  - For each continent, collects **boundary segments**: for each cell (r,c) and each brick-neighbor (nr,nc) **not** in the same continent, adds the **exact shared edge** from **`_shared_edge_brick`**.
  - **Chains** segments into closed loops using **angle ordering** at each vertex (smallest left turn = next edge CCW) so the outline doesn’t cut across the continent.
  - Segments that **don’t** close (e.g. open chain) are kept as **orphan_segments** and drawn as lines so the boundary is still complete.
- Returns per continent: **(cid, loops, segments, orphan_segments)**. Drawing: **`create_polygon`** for each closed loop, then **`create_line`** for each orphan segment, in the continent’s color.

---

## 10. Grid, Hit-Testing, and Drawing

- **`cell_center`**, **`_adjacent_cells_raw`**, **`cell_from_xy`**: Brick layout uses **cell_w = w / (COLS + 0.5)**, **cell_h = h / ROWS**; odd rows offset by half a cell.
- **`draw_grid`**: Clears “grid” tag; computes cell_w/cell_h; **computes bridges once** if not yet done; draws holes, territories (rectangle + oval), names, **continent outlines** (loops + orphans), **bridge lines**, then ghost and army counts. **Capital** territories use a distinct label color (**goldenrod**). Right panel: **Continents** (color swatch, capital name, bonus), **Cards**, and **Dice rolls** (offense/defense 1–6 per player). Panel width grows slightly for 3+ players so dice labels fit.

---

## 11. Attack, Blitz, and Conquest (`do_attack_phase_click`)

- **Flow**: Pick attacking territory, then adjacent enemy; **`ask_attack_count`** returns either an **int** (dice count), **`None`** (“I don’t want to attack”), or a **blitz params dict** (see below).
- **Single battle**: **`ask_defend_count`** for the defender; **`resolve_battle`**; apply casualties; on **capture** set **`conquered_this_turn = True`**.
- **Continue attacking (blitz)**: Extra button opens **`ask_blitz_params`**: stop when attacker’s source has ≤ X armies, or defender has ≤ Y armies, attacking with Z dice each round when possible. Runs a loop with auto-defend (max dice for defender). **`captured`** is initialized before the loop so an immediate stop doesn’t raise **`UnboundLocalError`**.
- **Elimination**: If the defender ends with **0 territories**, they are **eliminated** (same as before: cards to conqueror, +8 armies on conquered territory, etc.).
- **Dice**: **`_roll_d6()`** uses **`secrets.randbelow(6) + 1`**; stats accumulate in **`dice_offense`** / **`dice_defense`** for the right panel.

---

## 12. Move Phase and Reachability

- **`reachable_from`**: BFS over **physical + bridge** adjacency, only through territories of **`player_color`**.
- **`do_move_phase_click`**: Select source (≥2 armies), then destination in **`move_targets`**; **`ask_move_count`**; transfer armies.

---

## 13. End Turn and Cards

- **`end_turn()`**: If phase was attack → move; if phase was move: conquest card draw, optional set turn-in → **bonus_place**, else **`advance_to_next_player`**.

---

## 14. `main()` and `_run_game`

1. **Title screen** (fullscreen): 2 / 3 / 4 player or **Load game** (paste JSON). **`load_game_state`** parses and returns expanded state; **`_run_game(root, saved_state=...)`** builds the board from it.
2. **`_run_game`**: Same window goes fullscreen; **`make_playable_region`** / **`make_assignment`** only if **not** loading a save.
3. **Main menu** (in-game): returns to the title screen; loop until window close.

---

## 15. Data Flow Summary

- **Modes**: 2 (27, 12+15), 3 (44, 12+15+17), 4 (62, 12+15+17+18); grid 8×8 / 10×10 / 12×12 with **`removed`** cells.
- **Continents**: **`NUM_CAPITALS`** continents; capitals not adjacent; steal pass ensures **≥ 4** territories each (capitals not stolen); optional per-continent size band vs **`num_players`** when mathematically possible. Continent growth uses only physical brick adjacency (not bridges), so continents do not form across warp bridges.
- **Bridges**: Once per game; includes geometric bridges plus conditional left/right wrap bridges; gameplay adjacency includes both.
- **Elimination**: 0 territories → eliminated; cards to conqueror; +8 on conquered territory; winner when one player left.
- **Armies per turn**: floor(territories/3) + continent bonuses for full continents.

---

## 16. Save / Load (current format v3; loads v2/v3)

- **Wire format**: JSON object with **`"v": SAVE_FORMAT_VERSION`** (currently **3**). Loader accepts **v2 and v3** compact saves. Saves without `v` (old v1 style) or other versions are rejected with a **`ValueError`** shown in the Load dialog.
- **`save_game_state`**: Compact keys (**`m`**, **`R`**, **`c`**, **`t`**, **`a`**, **`y`**, …), **linear cell indices** **`r * COLS + c`** instead of many `[r,c]` pairs, **`assignment`** as one string of letters **`R` / `B` / `G` / `Y`** (player order matches **`COLORS`**). **`json.dumps(..., separators=(",", ":"))`** for a single tight line when copying.
- Bridge fields include **`b`** (bridge edges), **`W`** (wrap-bridge edge subset), and **`N`** (bridge neighbors adjacency list).
- **Compact key legend (v3)**:
  - **`v`**: save format version.
  - **`m`**: player count / mode (2, 3, or 4).
  - **`R`**: removed cells (linear indices).
  - **`c`**: cell-to-territory map (`"linear_cell_index" -> territory_index`).
  - **`t`**: territory-to-cell list (linear index per territory).
  - **`C`**: capital territory indices (set serialized as list).
  - **`o`**: continent id per territory.
  - **`k`**: capital territory index per continent.
  - **`n`**: territory names list.
  - **`b`**: bridge edges (`[from_territory, to_territory]` pairs).
  - **`W`**: wrap-bridge edge subset (left/right warp bridges).
  - **`N`**: bridge-neighbor adjacency lists (per territory).
  - **`P`**: player colors list (hex strings). If missing in v3 load, colors are randomized.
  - **`a`**: territory ownership as letter string (`R/B/G/Y` by player slot).
  - **`y`**: armies per territory.
  - **`p`**: current player index.
  - **`h`**: phase (`place`, `attack`, `move`, or `bonus_place`).
  - **`q`**: conquered-this-turn flag.
  - **`e`**: eliminated player indices.
  - **`d`**: player cards (list of hands).
  - **`i`**: set turn-in count.
  - **`l`**: normal placements remaining.
  - **`B`**: bonus placements remaining (set turn-in placement phase).
  - **`O`**: offense dice stats table (`player x face` counts).
  - **`D`**: defense dice stats table (`player x face` counts).
  - **`A`**: attack source cell (`[row, col]`) or `null`.
  - **`T`**: attack targets (linear cell indices).
  - **`M`**: move source cell (`[row, col]`) or `null`.
  - **`U`**: move targets (linear cell indices).
  - **`w`**: winner index (optional; only present when game is won).
- **`_decode_save`**: Validates **`v`**, sets mode from **`m`**, then dispatches by version (**`_expand_save_format_v2`** or **`_expand_save_format_v3`**) into the long-key dict **`_run_game`** expects.
- **`_expand_compact_save`**: Shared converter used by both v2 and v3 expanders so migration paths stay simple.
- **Load game**: Paste the save string on the title screen. **Save game**: Copy from the popup (clipboard button).

---

## 17. Fullscreen and macOS

- **Fullscreen**: Esc or F exits fullscreen; F11 toggles.
- **macOS console**: Messages such as **`IMKCFRunLoopWakeUpReliable`** / mach port come from **Apple’s Input Method Kit + Tk**, not from game logic; they are usually harmless.

