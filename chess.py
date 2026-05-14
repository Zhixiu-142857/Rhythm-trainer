# Chess game — tkinter UI with standard rules (castling, en passant, promotion).

from __future__ import annotations

import datetime
import json
import random
import time
import tkinter as tk
from pathlib import Path
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox
from typing import Callable, Dict, List, Optional, Sequence, Tuple

Cell = Optional[Tuple[str, str]]  # (color 'w'|'b', piece 'P'|'N'|'B'|'R'|'Q'|'K')

UNICODE = {
    ("w", "K"): "\u2654",
    ("w", "Q"): "\u2655",
    ("w", "R"): "\u2656",
    ("w", "B"): "\u2657",
    ("w", "N"): "\u2658",
    ("w", "P"): "\u2659",
    ("b", "K"): "\u265a",
    ("b", "Q"): "\u265b",
    ("b", "R"): "\u265c",
    ("b", "B"): "\u265d",
    ("b", "N"): "\u265e",
    ("b", "P"): "\u265f",
}


@dataclass
class GameState:
    board: List[List[Cell]]
    turn: str  # 'w' or 'b'
    castling: str  # substring of KQkq
    ep: Optional[Tuple[int, int]]  # en passant target square (row, col), or None
    halfmove: int = 0
    fullmove: int = 1
    # Position (board+turn+rights+ep) occurrence counts for threefold; only maintained on the live game.
    rep_counts: dict[str, int] = field(default_factory=dict)


def empty_board() -> List[List[Cell]]:
    return [[None for _ in range(8)] for _ in range(8)]


def initial_board() -> List[List[Cell]]:
    b = empty_board()
    back = "RNBQKBNR"
    for c, p in enumerate(back):
        b[0][c] = ("b", p)
        b[1][c] = ("b", "P")
        b[6][c] = ("w", "P")
        b[7][c] = ("w", p)
    return b


def clone_state(gs: GameState) -> GameState:
    return GameState(
        board=[row[:] for row in gs.board],
        turn=gs.turn,
        castling=gs.castling,
        ep=gs.ep,
        halfmove=gs.halfmove,
        fullmove=gs.fullmove,
        rep_counts={},  # search clones must not carry live repetition tallies
    )


def copy_game_state(gs: GameState) -> GameState:
    """Full copy of position (for move-history rewind); not used in engine search."""
    return GameState(
        board=[[cell for cell in row] for row in gs.board],
        turn=gs.turn,
        castling=gs.castling,
        ep=gs.ep,
        halfmove=gs.halfmove,
        fullmove=gs.fullmove,
        rep_counts=dict(gs.rep_counts),
    )


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8


def opponent(c: str) -> str:
    return "b" if c == "w" else "w"


def piece_at(gs: GameState, r: int, c: int) -> Cell:
    return gs.board[r][c]


def is_square_attacked(gs: GameState, r: int, c: int, by_color: str) -> bool:
    """True if square (r,c) is attacked by any piece of by_color."""
    oc = opponent(by_color)
    # Pawns: square (r,c) is attacked by pawn one row "behind" the attack direction
    for dc in (-1, 1):
        if by_color == "w":
            ar, ac = r + 1, c + dc  # white pawn attacks toward decreasing row
        else:
            ar, ac = r - 1, c + dc
        if in_bounds(ar, ac):
            p = piece_at(gs, ar, ac)
            if p and p[0] == by_color and p[1] == "P":
                return True
    # Knight
    for dr, dc in (
        (2, 1),
        (2, -1),
        (-2, 1),
        (-2, -1),
        (1, 2),
        (1, -2),
        (-1, 2),
        (-1, -2),
    ):
        ar, ac = r + dr, c + dc
        if in_bounds(ar, ac):
            p = piece_at(gs, ar, ac)
            if p and p[0] == by_color and p[1] == "N":
                return True
    # King
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            ar, ac = r + dr, c + dc
            if in_bounds(ar, ac):
                p = piece_at(gs, ar, ac)
                if p and p[0] == by_color and p[1] == "K":
                    return True
    # Rook / Queen rays
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ar, ac = r + dr, c + dc
        while in_bounds(ar, ac):
            p = piece_at(gs, ar, ac)
            if p:
                if p[0] == by_color and p[1] in "RQ":
                    return True
                break
            ar, ac = ar + dr, ac + dc
    # Bishop / Queen diagonals
    for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        ar, ac = r + dr, c + dc
        while in_bounds(ar, ac):
            p = piece_at(gs, ar, ac)
            if p:
                if p[0] == by_color and p[1] in "BQ":
                    return True
                break
            ar, ac = ar + dr, ac + dc
    return False


def find_king(gs: GameState, color: str) -> Optional[Tuple[int, int]]:
    for r in range(8):
        for c in range(8):
            p = piece_at(gs, r, c)
            if p and p[0] == color and p[1] == "K":
                return r, c
    return None


def in_check(gs: GameState, color: str) -> bool:
    k = find_king(gs, color)
    if not k:
        return False
    return is_square_attacked(gs, k[0], k[1], opponent(color))


def raw_moves_from(gs: GameState, r: int, c: int) -> List[Tuple[int, int, Optional[str]]]:
    """
    Pseudo-legal moves from (r,c): list of (to_r, to_c, promotion_piece_or_None).
    promotion_piece is 'Q','R','B','N' for pawn promotions.
    """
    p = piece_at(gs, r, c)
    if not p or p[0] != gs.turn:
        return []
    color, kind = p
    out: List[Tuple[int, int, Optional[str]]] = []

    def add(tr: int, tc: int, promo: Optional[str] = None) -> None:
        if in_bounds(tr, tc):
            out.append((tr, tc, promo))

    if kind == "P":
        step = -1 if color == "w" else 1
        start_rank = 6 if color == "w" else 1
        promo_rank = 0 if color == "w" else 7
        tr = r + step
        if in_bounds(tr, c) and piece_at(gs, tr, c) is None:
            if tr == promo_rank:
                for pr in "QRBN":
                    add(tr, c, pr)
            else:
                add(tr, c)
            if r == start_rank:
                tr2 = r + 2 * step
                if piece_at(gs, tr2, c) is None:
                    add(tr2, c)
        for dc in (-1, 1):
            tr, tc = r + step, c + dc
            if not in_bounds(tr, tc):
                continue
            cap = piece_at(gs, tr, tc)
            if cap and cap[0] != color:
                if tr == promo_rank:
                    for pr in "QRBN":
                        add(tr, tc, pr)
                else:
                    add(tr, tc)
            elif gs.ep and (tr, tc) == gs.ep and not cap:
                victim_r = tr + (1 if color == "w" else -1)
                vic = piece_at(gs, victim_r, tc)
                if vic and vic[0] != color and vic[1] == "P":
                    add(tr, tc)

    elif kind == "N":
        for dr, dc in (
            (2, 1),
            (2, -1),
            (-2, 1),
            (-2, -1),
            (1, 2),
            (1, -2),
            (-1, 2),
            (-1, -2),
        ):
            tr, tc = r + dr, c + dc
            if in_bounds(tr, tc):
                t = piece_at(gs, tr, tc)
                if t is None or t[0] != color:
                    add(tr, tc)

    elif kind == "K":
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                tr, tc = r + dr, c + dc
                if in_bounds(tr, tc):
                    t = piece_at(gs, tr, tc)
                    if t is None or t[0] != color:
                        add(tr, tc)
        # Castling
        if not in_check(gs, color):
            row = r
            if color == "w" and r == 7:
                if "K" in gs.castling and piece_at(gs, 7, 5) is None and piece_at(gs, 7, 6) is None:
                    if not is_square_attacked(gs, 7, 5, "b") and not is_square_attacked(gs, 7, 6, "b"):
                        add(7, 6)
                if (
                    "Q" in gs.castling
                    and piece_at(gs, 7, 1) is None
                    and piece_at(gs, 7, 2) is None
                    and piece_at(gs, 7, 3) is None
                ):
                    if not is_square_attacked(gs, 7, 3, "b") and not is_square_attacked(gs, 7, 2, "b"):
                        add(7, 2)
            if color == "b" and r == 0:
                if "k" in gs.castling and piece_at(gs, 0, 5) is None and piece_at(gs, 0, 6) is None:
                    if not is_square_attacked(gs, 0, 5, "w") and not is_square_attacked(gs, 0, 6, "w"):
                        add(0, 6)
                if (
                    "q" in gs.castling
                    and piece_at(gs, 0, 1) is None
                    and piece_at(gs, 0, 2) is None
                    and piece_at(gs, 0, 3) is None
                ):
                    if not is_square_attacked(gs, 0, 3, "w") and not is_square_attacked(gs, 0, 2, "w"):
                        add(0, 2)

    else:  # R, B, Q
        dirs: List[Tuple[int, int]] = []
        if kind in "RQ":
            dirs.extend(((1, 0), (-1, 0), (0, 1), (0, -1)))
        if kind in "BQ":
            dirs.extend(((1, 1), (1, -1), (-1, 1), (-1, -1)))
        for dr, dc in dirs:
            tr, tc = r + dr, c + dc
            while in_bounds(tr, tc):
                t = piece_at(gs, tr, tc)
                if t is None:
                    add(tr, tc)
                elif t[0] != color:
                    add(tr, tc)
                    break
                else:
                    break
                tr, tc = tr + dr, tc + dc

    return out


def apply_move(gs: GameState, fr: int, fc: int, tr: int, tc: int, promo: Optional[str]) -> None:
    """Mutate gs in place (assumes move is legal)."""
    piece = gs.board[fr][fc]
    assert piece is not None
    color, kind = piece
    captured = gs.board[tr][tc]
    # En passant capture
    if kind == "P" and gs.ep and (tr, tc) == gs.ep and captured is None:
        pr = tr + (1 if color == "w" else -1)
        gs.board[pr][tc] = None
        captured = ("b" if color == "w" else "w", "P")

    gs.board[tr][tc] = gs.board[fr][fc]
    gs.board[fr][fc] = None

    if kind == "P" and promo:
        gs.board[tr][tc] = (color, promo)

    # Castling rook move
    if kind == "K" and abs(tc - fc) == 2:
        if tc > fc:  # kingside: rook h-file -> f-file
            gs.board[fr][5] = gs.board[fr][7]
            gs.board[fr][7] = None
        else:  # queenside: rook a-file -> d-file
            gs.board[fr][3] = gs.board[fr][0]
            gs.board[fr][0] = None

    # Update castling rights
    new_c = gs.castling
    if fr == 7 and fc == 4:
        new_c = new_c.replace("K", "").replace("Q", "")
    if fr == 0 and fc == 4:
        new_c = new_c.replace("k", "").replace("q", "")
    if fr == 7 and fc == 0:
        new_c = new_c.replace("Q", "")
    if fr == 7 and fc == 7:
        new_c = new_c.replace("K", "")
    if fr == 0 and fc == 0:
        new_c = new_c.replace("q", "")
    if fr == 0 and fc == 7:
        new_c = new_c.replace("k", "")
    if kind == "R":
        if fr == 7 and fc == 0:
            new_c = new_c.replace("Q", "")
        if fr == 7 and fc == 7:
            new_c = new_c.replace("K", "")
        if fr == 0 and fc == 0:
            new_c = new_c.replace("q", "")
        if fr == 0 and fc == 7:
            new_c = new_c.replace("k", "")
    if captured and captured[1] == "R":
        if tr == 7 and tc == 0:
            new_c = new_c.replace("Q", "")
        if tr == 7 and tc == 7:
            new_c = new_c.replace("K", "")
        if tr == 0 and tc == 0:
            new_c = new_c.replace("q", "")
        if tr == 0 and tc == 7:
            new_c = new_c.replace("k", "")
    gs.castling = new_c

    # En passant square
    gs.ep = None
    if kind == "P" and abs(tr - fr) == 2:
        gs.ep = ((fr + tr) // 2, fc)

    # Halfmove clock (50-move rule could use this)
    if kind == "P" or captured:
        gs.halfmove = 0
    else:
        gs.halfmove += 1

    if color == "b":
        gs.fullmove += 1
    gs.turn = opponent(color)


def legal_moves(gs: GameState, r: int, c: int) -> List[Tuple[int, int, Optional[str]]]:
    color = gs.turn
    legal: List[Tuple[int, int, Optional[str]]] = []
    for tr, tc, promo in raw_moves_from(gs, r, c):
        test = clone_state(gs)
        apply_move(test, r, c, tr, tc, promo)
        if not in_check(test, color):
            legal.append((tr, tc, promo))
    return legal


def all_legal_moves(gs: GameState) -> List[Tuple[int, int, int, int, Optional[str]]]:
    """Every legal move for the side to move: (from_r, from_c, to_r, to_c, promotion_or_None)."""
    out: List[Tuple[int, int, int, int, Optional[str]]] = []
    c = gs.turn
    for r in range(8):
        for col in range(8):
            p = piece_at(gs, r, col)
            if p and p[0] == c:
                for tr, tc, promo in legal_moves(gs, r, col):
                    out.append((r, col, tr, tc, promo))
    return out


def is_capture_move(gs: GameState, fr: int, fc: int, tr: int, tc: int) -> bool:
    mover = piece_at(gs, fr, fc)
    if not mover:
        return False
    dest = piece_at(gs, tr, tc)
    if dest is not None and dest[0] != mover[0]:
        return True
    if mover[1] == "P" and gs.ep is not None and (tr, tc) == gs.ep:
        return True
    return False


def move_gives_check(gs: GameState, fr: int, fc: int, tr: int, tc: int, promo: Optional[str]) -> bool:
    t = clone_state(gs)
    apply_move(t, fr, fc, tr, tc, promo)
    return in_check(t, t.turn)


def _cand_uci4(m: Tuple[int, int, int, int, Optional[str]]) -> str:
    fr, fc, tr, tc, _pr = m
    return chr(ord("a") + fc) + str(8 - fr) + chr(ord("a") + tc) + str(8 - tr)


def _hist_shuffle_penalty_amount(history: Optional[Sequence[str]], m: Tuple[int, int, int, int, Optional[str]]) -> int:
    """
    Positive magnitude: same-side shuffle patterns from recent plies (-2, -4, …):
    2-move swap, repeated UCI, or a closed 3-edge tour (e.g. a8b8, b8a7, a7a8).
    Applied at the root of Standard/Challenging search only (Greedy unchanged).
    """
    if not history or len(history) < 2:
        return 0
    cand4 = _cand_uci4(m)
    c_f, c_t = cand4[:2], cand4[2:4]
    tot = 0
    # Moderate sizes only—large penalties swamp shallow search vs random opponents.
    for k in range(2, min(len(history) + 1, 10), 2):
        prev = history[-k]
        if len(prev) < 4:
            continue
        p4 = prev[:4]
        if p4[0:2] == cand4[2:4] and p4[2:4] == cand4[0:2]:
            tot += 520
        elif p4 == cand4:
            tot += 420
    # Closed triangle on three squares: old o_f->o_t, mid o_t->m_t, candidate m_t->o_f
    for k in range(4, min(len(history) + 1, 12), 2):
        if len(history) < k:
            break
        old = history[-k]
        mid = history[-(k - 2)]
        if len(old) < 4 or len(mid) < 4:
            continue
        o_f, o_t = old[:2], old[2:4]
        m_f, m_t = mid[:2], mid[2:4]
        if o_t == m_f and m_t == c_f and c_t == o_f:
            tot += 520
    return min(tot, 2200)


def _root_history_shuffle_penalties(history: Optional[Sequence[str]], m: Tuple[int, int, int, int, Optional[str]]) -> int:
    return -_hist_shuffle_penalty_amount(history, m)


def _root_major_piece_revisit_penalty(gs: GameState, history: Optional[Sequence[str]], m: Move5) -> int:
    """
    King/rook/queen touring (b8-a8-a7-b8-…) is not a 2-move undo or 3-cycle in UCI space.
    Penalize quiet moves that land on a square we already stepped on recently (same color).
    """
    fr, fc, tr, tc, _pr = m
    pw = piece_at(gs, fr, fc)
    if not pw or pw[1] not in ("K", "R", "Q"):
        return 0
    if is_capture_move(gs, fr, fc, tr, tc):
        return 0
    if not history:
        return 0
    cand_sq = chr(ord("a") + tc) + str(8 - tr)
    tot = 0
    # history[-2,-4,…] are our side's prior moves; skip k==2 (current square context noise).
    for k in range(4, min(len(history) + 1, 26), 2):
        ent = history[-k]
        if len(ent) < 4:
            continue
        if ent[2:4] == cand_sq:
            tot += 340
    return -min(tot, 2600)


def greedy_move(gs: GameState) -> Optional[Tuple[int, int, int, int, Optional[str]]]:
    """Prefer any capture, else any checking move, else uniform random among all legal moves."""
    moves = all_legal_moves(gs)
    if not moves:
        return None
    captures = [m for m in moves if is_capture_move(gs, m[0], m[1], m[2], m[3])]
    if captures:
        return random.choice(captures)
    checks = [m for m in moves if move_gives_check(gs, m[0], m[1], m[2], m[3], m[4])]
    if checks:
        return random.choice(checks)
    return random.choice(moves)


def casual_move(gs: GameState) -> Optional[Tuple[int, int, int, int, Optional[str]]]:
    """Weaker play: usually picks among non-captures, sometimes any legal move."""
    moves = all_legal_moves(gs)
    if not moves:
        return None
    quiet = [m for m in moves if not is_capture_move(gs, m[0], m[1], m[2], m[3])]
    if quiet and random.random() < 0.58:
        return random.choice(quiet)
    return random.choice(moves)


Move5 = Tuple[int, int, int, int, Optional[str]]

# --- Standard engine: alpha-beta + quiescence, material + piece-square tables ---

_PVAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}

# Knight PST (white; rank 0 = row 0 in our board = 8th rank). Symmetric by file.
_KNIGHT_PST_W = (
    (-50, -40, -30, -30, -30, -30, -40, -50),
    (-40, -20, 0, 5, 5, 0, -20, -40),
    (-30, 5, 10, 15, 15, 10, 5, -30),
    (-30, 0, 15, 20, 20, 15, 0, -30),
    (-30, 5, 15, 20, 20, 15, 5, -30),
    (-30, 0, 10, 15, 15, 10, 0, -30),
    (-40, -20, 0, 0, 0, 0, -20, -40),
    (-50, -40, -30, -30, -30, -30, -40, -50),
)

# Bishop PST (white)
_BISHOP_PST_W = (
    (-20, -10, -10, -10, -10, -10, -10, -20),
    (-10, 5, 0, 0, 0, 0, 5, -10),
    (-10, 10, 10, 10, 10, 10, 10, -10),
    (-10, 0, 10, 10, 10, 10, 0, -10),
    (-10, 5, 5, 10, 10, 5, 5, -10),
    (-10, 0, 5, 10, 10, 5, 0, -10),
    (-10, 0, 0, 0, 0, 0, 0, -10),
    (-20, -10, -10, -10, -10, -10, -10, -20),
)

def _big_piece_weight_total(gs: GameState) -> int:
    """Sum of weights Q=4,R=2,N/B=1 for non-king, non-pawn pieces (both sides)."""
    wgt = 0
    for r in range(8):
        for c in range(8):
            p = piece_at(gs, r, c)
            if not p:
                continue
            kind = p[1]
            if kind == "K" or kind == "P":
                continue
            if kind == "Q":
                wgt += 4
            elif kind == "R":
                wgt += 2
            elif kind in ("B", "N"):
                wgt += 1
    return wgt


def _pawn_push_phase_multiplier(big_wgt: int) -> float:
    """Stronger pawn-advance bonus as heavy pieces leave the board."""
    if big_wgt >= 12:
        return 1.0
    if big_wgt >= 8:
        return 1.22
    if big_wgt >= 5:
        return 1.58
    if big_wgt >= 2:
        return 2.1
    return 2.85


def _opening_mid_phase_factor(big_wgt: int) -> float:
    """0 in simplified endgames; ramps up in opening / middlegame (Q,R,N,B still on board)."""
    if big_wgt <= 5:
        return 0.0
    return min(1.0, (big_wgt - 5) / 9.0)


def _king_safety_penalty(gs: GameState, color: str) -> int:
    """
    Positive = worse king safety for ``color`` (centipawns scale, not material).
    Uses ring attacks, pawn shield, rook/queen on open lines to king, mild central king tax.
    """
    k = find_king(gs, color)
    if not k:
        return 0
    kr, kc = k
    opp = opponent(color)
    pen = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            ar, ac = kr + dr, kc + dc
            if in_bounds(ar, ac) and is_square_attacked(gs, ar, ac, opp):
                pen += 11
    if color == "w":
        fr = kr - 1
    else:
        fr = kr + 1
    if 0 <= fr <= 7:
        for dc in (-1, 0, 1):
            cc = kc + dc
            if 0 <= cc <= 7:
                pc = piece_at(gs, fr, cc)
                if pc is None or pc[0] != color or pc[1] != "P":
                    pen += 9
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r, c = kr + dr, kc + dc
        while in_bounds(r, c):
            p = piece_at(gs, r, c)
            if p:
                if p[0] == opp and p[1] in ("R", "Q"):
                    pen += 22
                break
            r, c = r + dr, c + dc
    if color == "w":
        home = {(7, 4), (7, 6), (7, 2)}
        if (kr, kc) not in home and kr <= 5 and 2 <= kc <= 5:
            pen += 16
    else:
        home = {(0, 4), (0, 6), (0, 2)}
        if (kr, kc) not in home and kr >= 2 and 2 <= kc <= 5:
            pen += 16
    return pen


# File-relative pawn-push weight: edge pawns (a/h) score less, central pawns (d/e) full.
_PAWN_FILE_W = (0.25, 0.55, 0.75, 1.0, 1.0, 0.75, 0.55, 0.25)


def _self_pawn_block_penalty(gs: GameState, color: str) -> int:
    """
    Penalize a friendly minor piece (B/N) sitting directly in front of an *unmoved*
    central pawn (d-file or e-file). Discourages plans like Bf1-d3 with d2 still home.
    """
    if color == "w":
        pawn_row = 6
        block_row = 5
    else:
        pawn_row = 1
        block_row = 2
    pen = 0
    for col in (3, 4):
        p_pawn = piece_at(gs, pawn_row, col)
        if p_pawn and p_pawn[0] == color and p_pawn[1] == "P":
            p_block = piece_at(gs, block_row, col)
            if p_block and p_block[0] == color and p_block[1] in ("B", "N"):
                pen += 35
    return pen


def _development_penalty(gs: GameState, color: str) -> int:
    """Positive if pieces still on home development squares (opening heuristic)."""
    pen = 0
    if color == "w":
        starts = ((7, 1, "N"), (7, 6, "N"), (7, 2, "B"), (7, 5, "B"))
        qr, qc = 7, 3
    else:
        starts = ((0, 1, "N"), (0, 6, "N"), (0, 2, "B"), (0, 5, "B"))
        qr, qc = 0, 3
    for r, c, kind in starts:
        p = piece_at(gs, r, c)
        if p and p[0] == color and p[1] == kind:
            pen += 12 if kind == "N" else 9
    pq = piece_at(gs, qr, qc)
    if pq and pq[0] == color and pq[1] == "Q":
        pen += 7
    return pen


def _pst_value(piece: str, color: str, r: int, c: int) -> int:
    if piece == "N":
        return _KNIGHT_PST_W[r][c] if color == "w" else _KNIGHT_PST_W[7 - r][c]
    if piece == "B":
        return _BISHOP_PST_W[r][c] if color == "w" else _BISHOP_PST_W[7 - r][c]
    if piece == "P":
        if color == "w":
            return max(0, (6 - r)) * 5
        return max(0, (r - 1)) * 5
    if piece in ("K", "R", "Q"):
        # Mild file bias so symmetric shuffles (e.g. a8 vs b8) are not scored identically.
        edge_dist = min(c, 7 - c)
        return edge_dist * 2
    return 0


def evaluate_white_advantage(gs: GameState) -> int:
    """Static evaluation: positive favors White (material + PST + bishop pair)."""
    w_mat_ex_k = b_mat_ex_k = 0
    for r in range(8):
        for c in range(8):
            p = piece_at(gs, r, c)
            if not p or p[1] == "K":
                continue
            val = _PVAL[p[1]]
            if p[0] == "w":
                w_mat_ex_k += val
            else:
                b_mat_ex_k += val
    mat_balance = w_mat_ex_k - b_mat_ex_k
    big_wgt = _big_piece_weight_total(gs)
    eg_pawn_mult = _pawn_push_phase_multiplier(big_wgt)
    hm = gs.halfmove
    fifty_urgency = 1.0
    if hm >= 28:
        fifty_urgency = 1.0 + min(hm - 28, 62) * 0.0055

    score = 0
    wb = bb = 0
    for r in range(8):
        for c in range(8):
            p = piece_at(gs, r, c)
            if not p:
                continue
            color, kind = p
            v = _PVAL[kind]
            pst = _pst_value(kind, color, r, c)
            if kind == "P":
                if color == "w":
                    adv = max(0, 6 - r)
                else:
                    adv = max(0, r - 1)
                # In the opening/middlegame, damp pawn pushes; weight by file (edge pawns less).
                opening_damp = 1.0 - 0.55 * _opening_mid_phase_factor(big_wgt)
                file_w = _PAWN_FILE_W[c]
                quad = adv * adv * 8 * eg_pawn_mult * file_w * opening_damp
                if mat_balance >= 120 and color == "w":
                    quad *= fifty_urgency
                elif mat_balance <= -120 and color == "b":
                    quad *= fifty_urgency
                pst += int(quad)
            if color == "w":
                score += v + pst
                if kind == "B":
                    wb += 1
            else:
                score -= v + pst
                if kind == "B":
                    bb += 1
    if wb >= 2:
        score += 18
    if bb >= 2:
        score -= 18

    ph = _opening_mid_phase_factor(big_wgt)
    if ph > 0:
        w_ks = _king_safety_penalty(gs, "w")
        b_ks = _king_safety_penalty(gs, "b")
        score -= int(w_ks * ph)
        score += int(b_ks * ph)
        w_dev = _development_penalty(gs, "w")
        b_dev = _development_penalty(gs, "b")
        score -= int(w_dev * ph)
        score += int(b_dev * ph)
        w_blk = _self_pawn_block_penalty(gs, "w")
        b_blk = _self_pawn_block_penalty(gs, "b")
        score -= int(w_blk * ph)
        score += int(b_blk * ph)
    return score


MATE_SCORE = 100_000


class SearchTimeout(Exception):
    """Raised when a time-budgeted search must stop (Challenging bot)."""


_SEARCH: dict = {"deadline": None, "nodes": 0}


def _search_reset(deadline: Optional[float]) -> None:
    _SEARCH["deadline"] = deadline
    _SEARCH["nodes"] = 0


def _search_clear() -> None:
    _SEARCH["deadline"] = None


def _poll_search_deadline() -> None:
    d = _SEARCH["deadline"]
    if d is None:
        return
    _SEARCH["nodes"] += 1
    if _SEARCH["nodes"] % 4096 == 0 and time.perf_counter() >= d:
        raise SearchTimeout()


def _mvv_lva_score(gs: GameState, m: Move5) -> int:
    fr, fc, tr, tc, _pr = m
    mover = piece_at(gs, fr, fc)
    if not mover:
        return 0
    victim_val = 0
    dest = piece_at(gs, tr, tc)
    if dest:
        victim_val = _PVAL[dest[1]]
    elif is_capture_move(gs, fr, fc, tr, tc):
        victim_val = _PVAL["P"]
    return 10 * victim_val - _PVAL[mover[1]]


def _ordered_moves(gs: GameState, captures_only: bool = False) -> List[Move5]:
    moves = all_legal_moves(gs)
    if captures_only:
        moves = [m for m in moves if is_capture_move(gs, m[0], m[1], m[2], m[3])]
    moves.sort(key=lambda m: (0, -_mvv_lva_score(gs, m)) if is_capture_move(gs, m[0], m[1], m[2], m[3]) else (1, 0))
    return moves


# Capture-only quiescence depth; in-check nodes search full width (see _quiescence).
_QUIESCENCE_CAPTURE_DEPTH = 10

# After checks, extend remaining depth so recaptures / king escapes stay inside the tree.
_CHECK_EXTEND_BUDGET_INITIAL = 14


def _quiescence(gs: GameState, alpha: int, beta: int, depth: int) -> int:
    _poll_search_deadline()
    if not any_legal_move(gs):
        if in_check(gs, gs.turn):
            return -MATE_SCORE + depth
        return 0
    in_chk = in_check(gs, gs.turn)
    stand = evaluate_white_advantage(gs)
    stand_perspective = stand if gs.turn == "w" else -stand
    if not in_chk:
        if stand_perspective >= beta:
            return beta
        if stand_perspective > alpha:
            alpha = stand_perspective
        if depth <= 0:
            return alpha
        moves = _ordered_moves(gs, captures_only=True)
    else:
        # In check: no standing pat; must search evasions (avoids misevaluating sac lines).
        if depth <= 0:
            depth = 3
        moves = _ordered_moves(gs, captures_only=False)
    for m in moves:
        _poll_search_deadline()
        child = clone_state(gs)
        apply_move(child, m[0], m[1], m[2], m[3], m[4])
        sc = -_quiescence(child, -beta, -alpha, depth - 1)
        if sc >= beta:
            return beta
        if sc > alpha:
            alpha = sc
    return alpha


# Penalize one-move undo of the previous position inside search (clone has no rep_counts).
_SEARCH_REVERSAL_PENALTY = 180


def _negamax(
    gs: GameState,
    depth: int,
    alpha: int,
    beta: int,
    parent_key: Optional[str] = None,
    check_ext_budget: int = _CHECK_EXTEND_BUDGET_INITIAL,
) -> int:
    _poll_search_deadline()
    if not any_legal_move(gs):
        if in_check(gs, gs.turn):
            return -MATE_SCORE + depth
        return 0
    if depth <= 0:
        return _quiescence(gs, alpha, beta, _QUIESCENCE_CAPTURE_DEPTH)
    cur_key = position_key(gs)
    for m in _ordered_moves(gs, captures_only=False):
        _poll_search_deadline()
        child = clone_state(gs)
        apply_move(child, m[0], m[1], m[2], m[3], m[4])
        rev = 0
        if parent_key is not None and position_key(child) == parent_key:
            rev = -_SEARCH_REVERSAL_PENALTY
        ext = 0
        nb = check_ext_budget
        if check_ext_budget > 0 and in_check(child, child.turn):
            ext = 1
            nb = check_ext_budget - 1
        sc = -_negamax(child, depth - 1 + ext, -beta, -alpha, parent_key=cur_key, check_ext_budget=nb) + rev
        if sc > alpha:
            alpha = sc
        if alpha >= beta:
            break
    return alpha


def search_best_move(
    gs: GameState,
    depth: int = 3,
    deadline: Optional[float] = None,
    move_history: Optional[Sequence[str]] = None,
    learn_root_hook: Optional[Callable[[GameState, Move5], int]] = None,
    partial_ok: bool = False,
    first_move: Optional[Move5] = None,
) -> Optional[Move5]:
    """
    Pick a move by alpha-beta search. Optional ``deadline`` (perf_counter time) bounds wall time.

    When ``partial_ok`` is True, a deadline hit returns the best move found so far at this depth
    instead of raising ``SearchTimeout``. ``first_move`` (typically the prior iteration's best)
    is searched first so the partial result is at least as informed as the previous depth.
    """
    moves = all_legal_moves(gs)
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]
    _search_reset(deadline)
    try:
        root_moves = _ordered_moves(gs, captures_only=False)
        if first_move is not None and first_move in root_moves:
            root_moves = [first_move] + [m for m in root_moves if m != first_move]
        best_move: Optional[Move5] = None
        best_score = -MATE_SCORE * 3
        alpha0 = -MATE_SCORE * 2
        beta0 = MATE_SCORE * 2
        for m in root_moves:
            if deadline is not None and time.perf_counter() >= deadline:
                if partial_ok:
                    break
                raise SearchTimeout()
            try:
                _poll_search_deadline()
                child = clone_state(gs)
                apply_move(child, m[0], m[1], m[2], m[3], m[4])
                learn_b = learn_root_hook(gs, m) if learn_root_hook else 0
                sc = (
                    -_negamax(
                        child,
                        depth - 1,
                        alpha0,
                        beta0,
                        parent_key=position_key(gs),
                        check_ext_budget=_CHECK_EXTEND_BUDGET_INITIAL,
                    )
                    + _root_repetition_penalty(gs, child)
                    + _root_history_shuffle_penalties(move_history, m)
                    + _root_major_piece_revisit_penalty(gs, move_history, m)
                    + learn_b
                )
            except SearchTimeout:
                if partial_ok:
                    break
                raise
            if sc > best_score:
                best_score = sc
                best_move = m
                alpha0 = max(alpha0, sc)
        return best_move if best_move is not None else moves[0]
    finally:
        _search_clear()


CHALLENGING_TIME_LIMIT_SEC = 15.0
STANDARD_TIME_LIMIT_SEC = 15.0
LEARNING_TIME_LIMIT_SEC = 15.0
STANDARD_SEARCH_DEPTH = 4
STANDARD_MAX_DEPTH = 6
LEARNING_MAX_DEPTH = 6

LEARNING_LOG_PATH = Path(__file__).resolve().parent / "chess_ai.log"
_LEARN_STATS: Dict[str, Tuple[int, float]] = {}
_LEARN_LOADED = False


def learn_ensure_loaded() -> None:
    global _LEARN_STATS, _LEARN_LOADED
    if _LEARN_LOADED:
        return
    _LEARN_LOADED = True
    if not LEARNING_LOG_PATH.is_file():
        return
    try:
        raw = LEARNING_LOG_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return
        data = json.loads(raw)
        ent = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(ent, dict):
            return
        for k, v in ent.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                _LEARN_STATS[str(k)] = (int(v[0]), float(v[1]))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass


def learn_save() -> None:
    try:
        payload = {
            "v": 1,
            "entries": {k: [n, s] for k, (n, s) in _LEARN_STATS.items()},
        }
        tmp = LEARNING_LOG_PATH.parent / (LEARNING_LOG_PATH.name + ".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        tmp.replace(LEARNING_LOG_PATH)
    except OSError:
        pass


def learn_move_bonus(pos_key: str, uci: str) -> int:
    """Centipawn bias from stored outcomes for (position before move, move UCI)."""
    learn_ensure_loaded()
    k = pos_key + "|" + uci.strip().lower()
    t = _LEARN_STATS.get(k)
    if not t:
        return 0
    n, ssum = t
    if n <= 0:
        return 0
    # Shrink toward 0 when few samples; reward in [-1, 1] for the side that played the move.
    prior_n, prior_s = 8.0, 0.0
    avg = (ssum + prior_s) / (n + prior_n)
    adj = 48.0 * avg / (1.0 + 0.03 * max(0, n - 1))
    return int(max(-42, min(42, adj)))


def learn_record_completed_game(snapshots: List[GameState], move_history: Sequence[str], status: str) -> None:
    """
    Update running stats from one finished game: each (position_key, uci) gets mover's outcome
    (+1 win, -1 loss, 0 draw). Persists to ``chess_ai.log``.
    """
    if len(snapshots) != len(move_history) + 1:
        return
    learn_ensure_loaded()
    final = snapshots[-1]
    for i, uci in enumerate(move_history):
        gs0 = snapshots[i]
        u = uci.strip().lower()
        if len(u) < 4:
            continue
        mover = gs0.turn
        if status == "Checkmate":
            loser = final.turn
            winner = opponent(loser)
            r = 1.0 if mover == winner else -1.0
        else:
            r = 0.0
        key = position_key(gs0) + "|" + u
        n, ssum = _LEARN_STATS.get(key, (0, 0.0))
        _LEARN_STATS[key] = (n + 1, ssum + r)
    learn_save()


def learning_move(gs: GameState, move_history: Optional[Sequence[str]] = None) -> Optional[Move5]:
    """
    Iterative deepening alpha-beta (same eval as Standard) with learned root bonuses from
    ``chess_ai.log``. Hard wall clock LEARNING_TIME_LIMIT_SEC; partial deeper depths are kept.
    """
    learn_ensure_loaded()

    def _hook(g: GameState, m: Move5) -> int:
        return learn_move_bonus(position_key(g), uci_from_move(m[0], m[1], m[2], m[3], m[4]).lower())

    deadline = time.perf_counter() + LEARNING_TIME_LIMIT_SEC
    last: Optional[Move5] = None
    for depth in range(1, LEARNING_MAX_DEPTH + 1):
        if time.perf_counter() >= deadline:
            break
        bm = search_best_move(
            gs,
            depth=depth,
            deadline=deadline,
            move_history=move_history,
            learn_root_hook=_hook,
            partial_ok=True,
            first_move=last,
        )
        if bm is not None:
            last = bm
    if last is not None:
        return last
    return greedy_move(gs)


def standard_move(gs: GameState, move_history: Optional[Sequence[str]] = None) -> Optional[Move5]:
    """
    Iterative deepening alpha-beta + quiescence (piece-square evaluation). Hard wall clock
    STANDARD_TIME_LIMIT_SEC; partial deeper depths are kept (best move so far wins).
    """
    deadline = time.perf_counter() + STANDARD_TIME_LIMIT_SEC
    last: Optional[Move5] = None
    for depth in range(1, STANDARD_MAX_DEPTH + 1):
        if time.perf_counter() >= deadline:
            break
        bm = search_best_move(
            gs,
            depth=depth,
            deadline=deadline,
            move_history=move_history,
            partial_ok=True,
            first_move=last,
        )
        if bm is not None:
            last = bm
    if last is not None:
        return last
    return greedy_move(gs)


ENGINE_OPTIONS: Tuple[str, ...] = ("Casual", "Standard", "Challenging", "Learning", "Random", "Greedy")
ENGINE_PROFILES = frozenset(ENGINE_OPTIONS)


def square_uci(r: int, c: int) -> str:
    return chr(ord("a") + c) + str(8 - r)


def uci_from_move(fr: int, fc: int, tr: int, tc: int, promo: Optional[str]) -> str:
    s = square_uci(fr, fc) + square_uci(tr, tc)
    if promo:
        s += promo.lower()
    return s


def parse_square_uci(sq: str) -> Tuple[int, int]:
    if len(sq) != 2:
        raise ValueError(f"bad square {sq!r}")
    file = ord(sq[0].lower()) - ord("a")
    rank = int(sq[1])
    if file < 0 or file > 7 or rank < 1 or rank > 8:
        raise ValueError(f"bad square {sq!r}")
    return 8 - rank, file


def move_tuple_from_uci(uci: str) -> Move5:
    u = uci.strip().lower().replace(" ", "")
    if len(u) < 4:
        raise ValueError(f"bad uci {uci!r}")
    fr, fc = parse_square_uci(u[0:2])
    tr, tc = parse_square_uci(u[2:4])
    promo = u[4].upper() if len(u) > 4 else None
    return fr, fc, tr, tc, promo


def format_log_game_label(start_line: Optional[str], end_line: str) -> str:
    end_parts = end_line.split("\t")
    result = end_parts[1] if len(end_parts) > 1 else "?"
    ply_s = ""
    for p in end_parts:
        if p.startswith("ply="):
            ply_s = p[4:]
            break
    meta = ""
    if start_line and start_line.startswith("START\t"):
        sp = start_line.split("\t")
        if len(sp) >= 3:
            meta = sp[2]
            if len(sp) >= 4:
                meta += " · " + sp[3].replace("\t", " ")[:48]
    tail = f"{result} · ply {ply_s}"
    if meta:
        return f"{tail} — {meta}"
    return tail


def games_from_log_lines(lines: Sequence[str]) -> List[Tuple[str, List[str]]]:
    """Parse chess_moves.log-style lines into (label, uci_moves)."""
    games: List[Tuple[str, List[str]]] = []
    cur_start: Optional[str] = None
    fall_moves: List[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("START\t"):
            cur_start = line
            fall_moves = []
        elif line.startswith("MOVE\t"):
            parts = line.split("\t")
            if len(parts) >= 3:
                fall_moves.append(parts[-1].strip())
        elif line.startswith("END\t"):
            moves: List[str] = []
            if "moves=" in line:
                idx = line.index("moves=")
                chunk = line[idx + 6 :].strip()
                moves = [x.strip() for x in chunk.split(",") if x.strip()]
            if not moves and fall_moves:
                moves = list(fall_moves)
            if moves:
                games.append((format_log_game_label(cur_start, line), moves))
            cur_start = None
            fall_moves = []
    return games


def challenging_move(gs: GameState, move_history: Optional[Sequence[str]] = None) -> Optional[Move5]:
    """
    Iterative deepening to depth 6, same eval as Standard. Hard wall clock
    CHALLENGING_TIME_LIMIT_SEC; partial deeper depths are kept (best move so far wins).
    """
    deadline = time.perf_counter() + CHALLENGING_TIME_LIMIT_SEC
    last: Optional[Move5] = None
    for depth in range(1, 7):
        if time.perf_counter() >= deadline:
            break
        bm = search_best_move(
            gs,
            depth=depth,
            deadline=deadline,
            move_history=move_history,
            partial_ok=True,
            first_move=last,
        )
        if bm is not None:
            last = bm
    if last is not None:
        return last
    return greedy_move(gs)


def engine_move_for_profile(
    profile: str, gs: GameState, move_history: Optional[Sequence[str]] = None
) -> Optional[Move5]:
    if profile == "Greedy":
        return greedy_move(gs)
    if profile == "Casual":
        return casual_move(gs)
    if profile == "Standard":
        return standard_move(gs, move_history)
    if profile == "Challenging":
        return challenging_move(gs, move_history)
    if profile == "Learning":
        return learning_move(gs, move_history)
    if profile == "Random":
        moves = all_legal_moves(gs)
        return random.choice(moves) if moves else None
    return None


def any_legal_move(gs: GameState) -> bool:
    c = gs.turn
    for r in range(8):
        for col in range(8):
            p = piece_at(gs, r, col)
            if p and p[0] == c:
                if legal_moves(gs, r, col):
                    return True
    return False


def position_key(gs: GameState) -> str:
    """Key for threefold: board + side to move + castling + en passant."""
    rows: List[str] = []
    for r in range(8):
        cells: List[str] = []
        for c in range(8):
            p = piece_at(gs, r, c)
            cells.append("." if p is None else p[0] + p[1])
        rows.append("".join(cells))
    ep_s = "None" if gs.ep is None else f"{gs.ep[0]},{gs.ep[1]}"
    return "|".join(rows) + f"|{gs.turn}|{gs.castling}|{ep_s}"


def _root_repetition_penalty(root: GameState, child: GameState) -> int:
    """Disfavor re-entering positions already seen in the real game (root search only)."""
    pk = position_key(child)
    seen = root.rep_counts.get(pk, 0)
    if seen <= 0:
        return 0
    return -62 * min(seen, 3)


def is_insufficient_material(gs: GameState) -> bool:
    """
    Automatic draw by dead position (FIDE-style subset): no legal checkmate possible
    with any sequence of moves from this material.
    """
    pieces: List[Tuple[int, int, str, str]] = []
    for r in range(8):
        for c in range(8):
            p = piece_at(gs, r, c)
            if p:
                pieces.append((r, c, p[0], p[1]))
    non_k = [p for p in pieces if p[3] != "K"]
    if len(non_k) == 0:
        return True
    if len(non_k) == 1:
        return non_k[0][3] in ("N", "B")
    if len(non_k) == 2:
        kinds = sorted([p[3] for p in non_k])
        if kinds == ["N", "N"]:
            return non_k[0][2] == non_k[1][2]
        if kinds == ["B", "B"]:
            if non_k[0][2] != non_k[1][2]:
                sq0 = (non_k[0][0] + non_k[0][1]) % 2
                sq1 = (non_k[1][0] + non_k[1][1]) % 2
                return sq0 == sq1
    return False


def is_threefold(gs: GameState) -> bool:
    k = position_key(gs)
    return gs.rep_counts.get(k, 0) >= 3


GAME_OVER_STATUSES = frozenset(
    ("Checkmate", "Stalemate", "Draw50", "DrawRepetition", "DrawMaterial")
)


def game_status(gs: GameState) -> str:
    chk = in_check(gs, gs.turn)
    if not any_legal_move(gs):
        return "Checkmate" if chk else "Stalemate"
    if gs.halfmove >= 100:
        return "Draw50"
    if is_insufficient_material(gs):
        return "DrawMaterial"
    if is_threefold(gs):
        return "DrawRepetition"
    return "Check" if chk else "Playing"


class ChessApp:
    BG = "#302e2b"
    BAR_BG = "#262421"
    FG = "#eeeed2"
    # Optional session log (START / END only); moves are shown beside the board in the app.
    MOVE_LOG_PATH = Path(__file__).resolve().parent / "chess_moves.log"
    CPU_VS_CPU_DELAY_MS = 280

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Chess")
        self.margin = 24
        self.cell = 72
        size = self.margin * 2 + self.cell * 8 + 80
        self.root.geometry(f"{size + 228}x{size}")
        self.root.minsize(size + 228, size)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda _e: self.root.attributes("-fullscreen", False))

        self.state: Optional[GameState] = None
        self.selected: Optional[Tuple[int, int]] = None
        self.legal_targets: List[Tuple[int, int]] = []
        self.status_var = tk.StringVar(value="White to move")
        self.play_mode: Optional[str] = None  # "pass_and_play" | "computer" | "cpu_vs_cpu"
        self.computer_profile: Optional[str] = None
        self.human_color: Optional[str] = None  # "w" | "b" when vs computer
        self.cpu_profile_w: Optional[str] = None
        self.cpu_profile_b: Optional[str] = None
        self.move_history: List[str] = []
        self._logged_game_end = False
        self.snapshots: List[GameState] = []
        self._replay_index: int = 0

        self._draw_scheduled = False

        self.main = tk.Frame(self.root, bg=self.BG)
        self.main.pack(fill=tk.BOTH, expand=True)

        self.selection_frame = tk.Frame(self.main, bg=self.BG)
        self.selection_frame.pack(fill=tk.BOTH, expand=True)
        self._build_selection_screen()

        self.game_frame = tk.Frame(self.main, bg=self.BG)
        self.game_inner = tk.Frame(self.game_frame, bg=self.BG)
        self.game_inner.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.game_inner, highlightthickness=0, bg=self.BG)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)

        self.moves_panel = tk.Frame(self.game_inner, bg=self.BAR_BG, width=228)
        self.moves_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.moves_panel.pack_propagate(False)
        self._build_moves_panel()

        bar = tk.Frame(self.game_frame, bg=self.BAR_BG)
        bar.pack(fill=tk.X)
        bar.columnconfigure(1, weight=1)
        self._replay_menu_btn = tk.Button(
            bar,
            text="← Menu",
            command=self._return_to_main_menu,
            font=("Helvetica", 12),
            fg=self.FG,
            bg="#3d3a36",
            activeforeground=self.FG,
            activebackground="#4a4743",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
        )
        self._replay_menu_btn.grid_remove()
        tk.Label(
            bar,
            textvariable=self.status_var,
            font=("Helvetica", 14),
            fg=self.FG,
            bg=self.BAR_BG,
            pady=8,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 12))

        self.root.bind_all("<Left>", self._on_key_replay_left)
        self.root.bind_all("<Right>", self._on_key_replay_right)

        learn_ensure_loaded()

    def _menu_button(self, parent: tk.Widget, text: str, command, **kw) -> tk.Button:
        opts: dict[str, object] = {
            "font": ("Helvetica", 16),
            "fg": self.FG,
            "bg": "#3d3a36",
            "activeforeground": self.FG,
            "activebackground": "#4a4743",
            "relief": tk.FLAT,
            "padx": 24,
            "pady": 14,
            "cursor": "hand2",
        }
        opts.update(kw)
        return tk.Button(parent, text=text, command=command, **opts)

    def _selection_button(self, parent: tk.Widget, text: str, command, **kw) -> tk.Button:
        """High-contrast control for the menu (no light focus ring)."""
        opts: dict[str, object] = {
            "font": ("Helvetica", 14, "bold"),
            "fg": "#ffffff",
            "bg": "#2a2826",
            "activeforeground": "#ffffff",
            "activebackground": "#3d3a36",
            "relief": tk.FLAT,
            "borderwidth": 0,
            "highlightthickness": 0,
            "padx": 18,
            "pady": 10,
            "cursor": "hand2",
            "takefocus": 0,
        }
        opts.update(kw)
        return tk.Button(parent, text=text, command=command, **opts)

    def _build_moves_panel(self) -> None:
        mp = self.moves_panel
        list_bg = "#1e1d1a"
        tk.Label(
            mp,
            text="Moves",
            fg=self.FG,
            bg=self.BAR_BG,
            font=("Helvetica", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(12, 4))
        wrap = tk.Frame(mp, bg=self.BAR_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        sb = tk.Scrollbar(wrap, orient=tk.VERTICAL, bg=self.BAR_BG, troughcolor=self.BAR_BG)
        self.move_listbox = tk.Listbox(
            wrap,
            height=20,
            yscrollcommand=sb.set,
            font=("Courier", 10),
            bg=list_bg,
            fg=self.FG,
            selectmode=tk.BROWSE,
            highlightthickness=0,
            borderwidth=0,
            selectbackground="#4a6fa5",
            selectforeground="#ffffff",
            activestyle="none",
        )
        sb.config(command=self.move_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.move_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        rw = tk.Frame(mp, bg=self.BAR_BG)
        rw.pack(fill=tk.X, padx=8, pady=(0, 12))
        tk.Label(
            rw,
            text="Rewind (after game ends) — ← →",
            fg="#b0aca6",
            bg=self.BAR_BG,
            font=("Helvetica", 10),
        ).pack(anchor="w", pady=(0, 6))
        bf = tk.Frame(rw, bg=self.BAR_BG)
        bf.pack(fill=tk.X)
        small = dict(
            font=("Helvetica", 10),
            fg=self.FG,
            bg="#3d3a36",
            activeforeground=self.FG,
            activebackground="#4a4743",
            relief=tk.FLAT,
            padx=5,
            pady=4,
            cursor="hand2",
        )
        self._btn_replay_start = tk.Button(bf, text="|<<", command=self._replay_start, **small)
        self._btn_replay_prev = tk.Button(bf, text="<", command=self._replay_prev, **small)
        self._btn_replay_next = tk.Button(bf, text=">", command=self._replay_next, **small)
        self._btn_replay_end = tk.Button(bf, text=">>|", command=self._replay_end, **small)
        for i, b in enumerate((self._btn_replay_start, self._btn_replay_prev, self._btn_replay_next, self._btn_replay_end)):
            b.pack(side=tk.LEFT, padx=(0, 4) if i < 3 else (0, 0))
        for b in (self._btn_replay_start, self._btn_replay_prev, self._btn_replay_next, self._btn_replay_end):
            b.config(state=tk.DISABLED)

    def _at_live_position(self) -> bool:
        if not self.snapshots:
            return True
        return self._replay_index == len(self.snapshots) - 1

    def _replay_go(self, idx: int) -> None:
        if not self.snapshots or self.state is None:
            return
        idx = max(0, min(idx, len(self.snapshots) - 1))
        self._replay_index = idx
        self.state = copy_game_state(self.snapshots[idx])
        self.selected = None
        self.legal_targets = []
        self._update_status()
        self._schedule_draw()

    def _replay_start(self) -> None:
        self._replay_go(0)

    def _replay_prev(self) -> None:
        self._replay_go(self._replay_index - 1)

    def _replay_next(self) -> None:
        self._replay_go(self._replay_index + 1)

    def _replay_end(self) -> None:
        self._replay_go(len(self.snapshots) - 1)

    def _sync_move_list(self) -> None:
        if not hasattr(self, "move_listbox"):
            return
        self.move_listbox.delete(0, tk.END)
        pl = 1
        side = "w"
        for uci in self.move_history:
            prefix = f"{pl}. " if side == "w" else f"{pl}… "
            self.move_listbox.insert(tk.END, f"{prefix}{uci}")
            if side == "w":
                side = "b"
            else:
                side = "w"
                pl += 1
        if self._replay_index > 0:
            row = self._replay_index - 1
            self.move_listbox.selection_set(row)
            self.move_listbox.see(row)
        else:
            self.move_listbox.selection_clear(0, tk.END)

    def _update_replay_buttons(self) -> None:
        if not hasattr(self, "_btn_replay_start"):
            return
        n = len(self.snapshots)
        # Use the *last* snapshot (actual game end), not the board we are currently
        # showing — otherwise rewinding to a mid-game position disables ">" / ">>|".
        final_ended = n > 0 and game_status(self.snapshots[-1]) in GAME_OVER_STATUSES
        can = n > 1 and (final_ended or self.play_mode == "replay")
        for b in (self._btn_replay_start, self._btn_replay_prev, self._btn_replay_next, self._btn_replay_end):
            b.config(state=tk.DISABLED)
        if not can:
            return
        self._btn_replay_start.config(state=tk.NORMAL if self._replay_index > 0 else tk.DISABLED)
        self._btn_replay_prev.config(state=tk.NORMAL if self._replay_index > 0 else tk.DISABLED)
        self._btn_replay_next.config(state=tk.NORMAL if self._replay_index < n - 1 else tk.DISABLED)
        self._btn_replay_end.config(state=tk.NORMAL if self._replay_index < n - 1 else tk.DISABLED)

    def _replay_keyboard_allowed(self) -> bool:
        try:
            if not self.game_frame.winfo_ismapped():
                return False
        except tk.TclError:
            return False
        n = len(self.snapshots)
        if n < 2:
            return False
        return game_status(self.snapshots[-1]) in GAME_OVER_STATUSES or self.play_mode == "replay"

    def _on_key_replay_left(self, event: tk.Event) -> Optional[str]:
        try:
            if event.widget.winfo_toplevel() is not self.root:
                return None
        except tk.TclError:
            return None
        if not self._replay_keyboard_allowed():
            return None
        if self._replay_index > 0:
            self._replay_prev()
            return "break"
        return None

    def _on_key_replay_right(self, event: tk.Event) -> Optional[str]:
        try:
            if event.widget.winfo_toplevel() is not self.root:
                return None
        except tk.TclError:
            return None
        if not self._replay_keyboard_allowed():
            return None
        n = len(self.snapshots)
        if self._replay_index < n - 1:
            self._replay_next()
            return "break"
        return None

    def _set_replay_menu_visible(self, show: bool) -> None:
        if show:
            self._replay_menu_btn.grid(row=0, column=0, padx=(10, 4), pady=6, sticky="ns")
        else:
            self._replay_menu_btn.grid_remove()

    def _return_to_main_menu(self) -> None:
        self.game_frame.pack_forget()
        self._set_replay_menu_visible(False)
        self.selection_frame.pack(fill=tk.BOTH, expand=True)
        self.selection_menu_outer.place(relx=0.5, rely=0.5, anchor="center")
        self.state = None
        self.play_mode = None
        self.move_history = []
        self.snapshots = []
        self._replay_index = 0
        self._logged_game_end = False
        self.computer_profile = None
        self.human_color = None
        self.cpu_profile_w = None
        self.cpu_profile_b = None
        self.selected = None
        self.legal_targets = []
        self.status_var.set("White to move")

    def _show_load_log_dialog(self) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.title("Load game from log")
        dlg.configure(bg=self.BG)
        dlg.transient(self.root)
        dlg.geometry("700x460")

        path_var = tk.StringVar(value=str(self.MOVE_LOG_PATH.resolve()))

        def browse() -> None:
            p = filedialog.askopenfilename(
                parent=dlg,
                title="Chess move log",
                initialdir=str(self.MOVE_LOG_PATH.parent),
                filetypes=[("Log files", "*.log"), ("All files", "*")],
            )
            if p:
                path_var.set(p)

        top = tk.Frame(dlg, bg=self.BG)
        top.pack(fill=tk.X, padx=10, pady=8)
        tk.Entry(top, textvariable=path_var, width=72, bg="#2a2826", fg=self.FG, insertbackground=self.FG).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8)
        )
        tk.Button(top, text="Browse…", command=browse, fg=self.FG, bg="#3d3a36", relief=tk.FLAT).pack(
            side=tk.LEFT
        )

        tk.Label(
            dlg,
            text="Games in file (double-click or Load selected). Newest entries at bottom.",
            fg=self.FG,
            bg=self.BG,
            font=("Helvetica", 11),
        ).pack(anchor="w", padx=10)

        frame = tk.Frame(dlg, bg=self.BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        sb = tk.Scrollbar(frame)
        lb = tk.Listbox(
            frame,
            yscrollcommand=sb.set,
            height=16,
            font=("Courier", 9),
            bg="#1e1d1a",
            fg=self.FG,
            highlightthickness=0,
            selectbackground="#4a6fa5",
        )
        sb.config(command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        games_data_ref: List[Tuple[str, List[str]]] = []
        display_slice_start = [0]

        def refresh() -> None:
            lb.delete(0, tk.END)
            games_data_ref.clear()
            path = Path(path_var.get().strip())
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                messagebox.showerror("Cannot read file", str(exc), parent=dlg)
                return
            games_data_ref[:] = games_from_log_lines(lines)
            if not games_data_ref:
                lb.insert(tk.END, "(No completed games with moves=… or MOVE lines.)")
                display_slice_start[0] = 0
                return
            cap = 100
            start = max(0, len(games_data_ref) - cap)
            display_slice_start[0] = start
            for label, _mv in games_data_ref[start:]:
                lb.insert(tk.END, label)

        def load_selected() -> None:
            sel = lb.curselection()
            if not sel or not games_data_ref:
                messagebox.showinfo("Pick a game", "Select a row in the list.", parent=dlg)
                return
            idx = int(sel[0])
            gi = display_slice_start[0] + idx
            if gi < 0 or gi >= len(games_data_ref):
                return
            label, moves = games_data_ref[gi]
            dlg.destroy()
            self._load_replay_from_log(label, moves)

        tk.Button(dlg, text="Refresh list", command=refresh, fg=self.FG, bg="#3d3a36", relief=tk.FLAT).pack(
            pady=4
        )
        bot = tk.Frame(dlg, bg=self.BG)
        bot.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(bot, text="Cancel", command=dlg.destroy, fg=self.FG, bg="#3d3a36", relief=tk.FLAT).pack(
            side=tk.RIGHT
        )
        tk.Button(bot, text="Load selected", command=load_selected, fg=self.FG, bg="#3d3a36", relief=tk.FLAT).pack(
            side=tk.RIGHT, padx=(0, 10)
        )

        dlg.after(80, refresh)
        lb.bind("<Double-Button-1>", lambda _e: load_selected())

    def _load_replay_from_log(self, summary: str, moves: List[str]) -> None:
        gs = GameState(board=initial_board(), turn="w", castling="KQkq", ep=None)
        gs.rep_counts.clear()
        gs.rep_counts[position_key(gs)] = 1
        snapshots_list = [copy_game_state(gs)]
        mh: List[str] = []
        for raw_uci in moves:
            uci = raw_uci.strip()
            if not uci:
                continue
            try:
                fr, fc, tr, tc, promo_from_uci = move_tuple_from_uci(uci)
            except ValueError as exc:
                messagebox.showerror("Bad move in log", f"{uci!r}: {exc}", parent=self.root)
                return
            mover = piece_at(gs, fr, fc)
            if mover is None:
                messagebox.showerror("Bad move in log", f"No piece on {uci[:2]}", parent=self.root)
                return
            if mover[0] != gs.turn:
                messagebox.showerror("Bad move in log", f"Wrong side to move: {uci}", parent=self.root)
                return
            matches = [
                (tr2, tc2, pr2)
                for fr2, fc2, tr2, tc2, pr2 in all_legal_moves(gs)
                if fr2 == fr and fc2 == fc and tr2 == tr and tc2 == tc
            ]
            if not matches:
                messagebox.showerror("Illegal move in log", uci, parent=self.root)
                return
            if promo_from_uci is not None:
                pick = next((m for m in matches if m[2] == promo_from_uci), None)
                if pick is None:
                    messagebox.showerror("Illegal promotion in log", uci, parent=self.root)
                    return
            elif len(matches) == 1:
                pick = matches[0]
            else:
                pick = next((m for m in matches if m[2] == "Q"), matches[0])
            tr, tc, promo = pick
            apply_move(gs, fr, fc, tr, tc, promo)
            rk = position_key(gs)
            gs.rep_counts[rk] = gs.rep_counts.get(rk, 0) + 1
            mh.append(uci_from_move(fr, fc, tr, tc, promo))
            snapshots_list.append(copy_game_state(gs))

        self.state = gs
        self.move_history = mh
        self.snapshots = snapshots_list
        self._replay_index = len(snapshots_list) - 1
        self.play_mode = "replay"
        self._logged_game_end = True
        self.computer_profile = None
        self.human_color = None
        self.cpu_profile_w = None
        self.cpu_profile_b = None
        self.selected = None
        self.legal_targets = []
        self.selection_menu_outer.place_forget()
        self.selection_cpu_outer.place_forget()
        self.selection_frame.pack_forget()
        self.game_frame.pack(fill=tk.BOTH, expand=True)
        self._set_replay_menu_visible(True)
        self.status_var.set(f"Replay — {summary}")
        self._sync_move_list()
        self._update_status()
        self._schedule_draw()

    def _build_selection_screen(self) -> None:
        sb = self.BG
        sfg = self.FG
        sm = "#b0aca6"

        self.selection_menu_outer = tk.Frame(self.selection_frame, bg=sb)
        self.selection_menu_outer.place(relx=0.5, rely=0.5, anchor="center")
        outer = self.selection_menu_outer

        tk.Label(
            outer,
            text="Chess",
            font=("Helvetica", 40, "bold"),
            fg=sfg,
            bg=sb,
        ).pack(pady=(0, 8))
        tk.Label(
            outer,
            text="Choose how you want to play",
            font=("Helvetica", 16),
            fg=sm,
            bg=sb,
        ).pack(pady=(0, 36))

        self._selection_button(
            outer,
            "Pass and play",
            self._start_pass_and_play,
            font=("Helvetica", 18, "bold"),
            padx=36,
            pady=16,
        ).pack(pady=(0, 8))
        tk.Label(
            outer,
            text="Two players take turns on this device",
            font=("Helvetica", 12),
            fg=sm,
            bg=sb,
        ).pack(pady=(0, 14))

        self._selection_button(
            outer,
            "Load game from log…",
            self._show_load_log_dialog,
            font=("Helvetica", 14),
            padx=28,
            pady=10,
        ).pack(pady=(0, 4))
        tk.Label(
            outer,
            text="Open chess_moves.log, pick a game, rewind / step forward on the board",
            font=("Helvetica", 12),
            fg=sm,
            bg=sb,
        ).pack(pady=(0, 32))

        self._selection_button(
            outer,
            "Computer vs computer",
            self._show_cpu_vs_cpu_menu,
            font=("Helvetica", 18, "bold"),
            padx=36,
            pady=16,
        ).pack(pady=(0, 6))
        tk.Label(
            outer,
            text="Two engines play each other; moves appear beside the board (rewind after the game)",
            font=("Helvetica", 12),
            fg=sm,
            bg=sb,
        ).pack(pady=(0, 32))

        tk.Label(
            outer,
            text="Play against computer",
            font=("Helvetica", 18),
            fg=sfg,
            bg=sb,
        ).pack(pady=(0, 12))

        comp = tk.Frame(outer, bg=sb)
        comp.pack()
        profiles = [
            ("Casual", "Mostly quiet moves; sometimes mixes it up", "Casual"),
            ("Standard", "Iterative alpha-beta + quiescence, max 15s think", "Standard"),
            ("Challenging", "Deepening to depth 6, max 15s think", "Challenging"),
            ("Learning", "Like Standard + bonuses from chess_ai.log; max 15s think", "Learning"),
            ("Random", "Legal moves, picked at random", "Random"),
            ("Greedy", "Capture if possible, else check, else random", "Greedy"),
        ]
        for name, blurb, computer in profiles:
            row = tk.Frame(comp, bg=sb)
            row.pack(pady=6)
            if computer:
                tk.Label(
                    row,
                    text=name,
                    font=("Helvetica", 16, "bold"),
                    fg=sfg,
                    bg=sb,
                    anchor="w",
                ).pack(side=tk.LEFT, padx=(0, 8))
                self._selection_button(
                    row,
                    "White",
                    lambda p=computer: self._begin_computer_game(p, "w"),
                    width=8,
                ).pack(side=tk.LEFT, padx=3)
                self._selection_button(
                    row,
                    "Black",
                    lambda p=computer: self._begin_computer_game(p, "b"),
                    width=8,
                ).pack(side=tk.LEFT, padx=(3, 12))
            else:
                self._selection_button(row, name, lambda n=name: self._computer_not_ready(n), width=12).pack(
                    side=tk.LEFT, padx=(0, 12)
                )
            tk.Label(
                row,
                text=blurb,
                font=("Helvetica", 12),
                fg=sm,
                bg=sb,
            ).pack(side=tk.LEFT)

        self._cpu_w_var = tk.StringVar(value="Random")
        self._cpu_b_var = tk.StringVar(value="Greedy")
        self.selection_cpu_outer = tk.Frame(self.selection_frame, bg=sb)
        cpu = self.selection_cpu_outer
        tk.Label(
            cpu,
            text="Computer vs computer",
            font=("Helvetica", 28, "bold"),
            fg=sfg,
            bg=sb,
        ).pack(pady=(0, 8))
        tk.Label(
            cpu,
            text="Pick an engine for each color, then start.",
            font=("Helvetica", 14),
            fg=sm,
            bg=sb,
        ).pack(pady=(0, 20))
        rw = tk.Frame(cpu, bg=sb)
        rw.pack(pady=6)
        tk.Label(rw, text="White:", fg=sfg, bg=sb, font=("Helvetica", 14), width=8, anchor="w").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        omw = tk.OptionMenu(rw, self._cpu_w_var, *ENGINE_OPTIONS)
        omw.config(bg="#2a2826", fg=self.FG, activebackground="#3d3a36", highlightthickness=0)
        omw.pack(side=tk.LEFT)
        rb = tk.Frame(cpu, bg=sb)
        rb.pack(pady=6)
        tk.Label(rb, text="Black:", fg=sfg, bg=sb, font=("Helvetica", 14), width=8, anchor="w").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        omb = tk.OptionMenu(rb, self._cpu_b_var, *ENGINE_OPTIONS)
        omb.config(bg="#2a2826", fg=self.FG, activebackground="#3d3a36", highlightthickness=0)
        omb.pack(side=tk.LEFT)
        self._selection_button(cpu, "Start match", self._begin_cpu_vs_cpu, font=("Helvetica", 16), padx=28, pady=12).pack(
            pady=(24, 10)
        )
        self._selection_button(cpu, "← Back to menu", self._hide_cpu_vs_cpu_menu, font=("Helvetica", 14)).pack(pady=(8, 0))
        self.selection_cpu_outer.place_forget()

    def _show_cpu_vs_cpu_menu(self) -> None:
        self.selection_menu_outer.place_forget()
        self.selection_cpu_outer.place(relx=0.5, rely=0.5, anchor="center")

    def _hide_cpu_vs_cpu_menu(self) -> None:
        self.selection_cpu_outer.place_forget()
        self.selection_menu_outer.place(relx=0.5, rely=0.5, anchor="center")

    def _log_file_append(self, line: str) -> None:
        try:
            with open(self.MOVE_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

    def _init_game_logging(self, mode: str, extra: str = "") -> None:
        self.move_history = []
        self._logged_game_end = False
        ts = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
        self._log_file_append(f"START\t{ts}\t{mode}\t{extra}")
        if self.state is not None:
            self.state.rep_counts.clear()
            self.state.rep_counts[position_key(self.state)] = 1
            self.snapshots = [copy_game_state(self.state)]
            self._replay_index = 0
        else:
            self.snapshots = []
            self._replay_index = 0
        self._sync_move_list()
        self._update_replay_buttons()

    def _apply_move_recorded(self, fr: int, fc: int, tr: int, tc: int, promo: Optional[str]) -> None:
        if self.state is None:
            return
        apply_move(self.state, fr, fc, tr, tc, promo)
        rk = position_key(self.state)
        self.state.rep_counts[rk] = self.state.rep_counts.get(rk, 0) + 1
        uci = uci_from_move(fr, fc, tr, tc, promo)
        self.move_history.append(uci)
        self.snapshots.append(copy_game_state(self.state))
        self._replay_index = len(self.snapshots) - 1

    def _begin_cpu_vs_cpu(self) -> None:
        wp = self._cpu_w_var.get()
        bp = self._cpu_b_var.get()
        if wp not in ENGINE_PROFILES or bp not in ENGINE_PROFILES:
            return
        self.play_mode = "cpu_vs_cpu"
        self.computer_profile = None
        self.human_color = None
        self.cpu_profile_w = wp
        self.cpu_profile_b = bp
        self.state = GameState(
            board=initial_board(),
            turn="w",
            castling="KQkq",
            ep=None,
        )
        self.selected = None
        self.legal_targets = []
        self._init_game_logging("cpu_vs_cpu", f"white={wp}\tblack={bp}")
        self.selection_menu_outer.place_forget()
        self.selection_cpu_outer.place_forget()
        self.selection_frame.pack_forget()
        self.game_frame.pack(fill=tk.BOTH, expand=True)
        self._update_status()
        self._schedule_draw()
        self._maybe_schedule_computer_move()

    def _computer_not_ready(self, profile: str) -> None:
        messagebox.showinfo(
            "Coming soon",
            f"Playing against “{profile}” is not available yet.\n\n"
            "For now, use Pass and play for two humans on one screen.",
            parent=self.root,
        )

    def _begin_computer_game(self, profile: str, human: str) -> None:
        if profile not in ENGINE_PROFILES:
            return
        self.play_mode = "computer"
        self.computer_profile = profile
        self.human_color = human
        self.cpu_profile_w = None
        self.cpu_profile_b = None
        self.state = GameState(
            board=initial_board(),
            turn="w",
            castling="KQkq",
            ep=None,
        )
        self.selected = None
        self.legal_targets = []
        self._init_game_logging("computer", f"profile={profile}\thuman={human}")
        self.selection_frame.pack_forget()
        self.game_frame.pack(fill=tk.BOTH, expand=True)
        self._update_status()
        self._schedule_draw()
        self._maybe_schedule_computer_move()

    def _start_pass_and_play(self) -> None:
        self.play_mode = "pass_and_play"
        self.computer_profile = None
        self.human_color = None
        self.cpu_profile_w = None
        self.cpu_profile_b = None
        self.state = GameState(
            board=initial_board(),
            turn="w",
            castling="KQkq",
            ep=None,
        )
        self.selected = None
        self.legal_targets = []
        self._init_game_logging("pass_and_play", "")
        self.status_var.set("White to move")
        self.selection_frame.pack_forget()
        self.game_frame.pack(fill=tk.BOTH, expand=True)
        self._schedule_draw()

    def _board_px(self) -> Tuple[float, float, float]:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        side = min(w, h) - 2 * self.margin
        side = max(side, 200)
        ox = (w - side) / 2
        oy = (h - side) / 2
        cell = side / 8
        return ox, oy, cell

    def _board_view_flipped(self) -> bool:
        """When you play Black vs the computer, rotate the board 180° so your pieces are nearer."""
        return self.play_mode == "computer" and self.human_color == "b"

    def _display_to_board(self, drow: int, dcol: int) -> Tuple[int, int]:
        if self._board_view_flipped():
            return 7 - drow, 7 - dcol
        return drow, dcol

    def _schedule_draw(self) -> None:
        if self._draw_scheduled:
            return
        self._draw_scheduled = True
        self.root.after_idle(self._draw)

    def _on_resize(self, _evt: tk.Event) -> None:
        if self.state is not None:
            self._schedule_draw()

    def _rc_from_xy(self, x: float, y: float) -> Optional[Tuple[int, int]]:
        ox, oy, cell = self._board_px()
        if x < ox or y < oy or x >= ox + 8 * cell or y >= oy + 8 * cell:
            return None
        dcol = int((x - ox) / cell)
        drow = int((y - oy) / cell)
        return self._display_to_board(drow, dcol)

    def _is_computer_turn(self) -> bool:
        if self.state is None or not self._at_live_position():
            return False
        if self.play_mode == "replay":
            return False
        if self.play_mode == "cpu_vs_cpu":
            return game_status(self.state) not in GAME_OVER_STATUSES
        return (
            self.play_mode == "computer"
            and self.computer_profile in ENGINE_PROFILES
            and self.human_color is not None
            and self.state.turn != self.human_color
        )

    def _maybe_schedule_computer_move(self) -> None:
        if self.state is None:
            return
        if not self._at_live_position():
            return
        if game_status(self.state) in GAME_OVER_STATUSES:
            return
        if not self._is_computer_turn():
            return
        delay = self.CPU_VS_CPU_DELAY_MS if self.play_mode == "cpu_vs_cpu" else 120
        self.root.after(delay, self._do_computer_move)

    def _do_computer_move(self) -> None:
        if self.state is None or not self._is_computer_turn():
            return
        if game_status(self.state) in GAME_OVER_STATUSES:
            return
        if self.play_mode == "cpu_vs_cpu":
            prof = self.cpu_profile_w if self.state.turn == "w" else self.cpu_profile_b
            pick = engine_move_for_profile(prof or "Random", self.state, self.move_history)
        else:
            pick = engine_move_for_profile(
                self.computer_profile or "Random", self.state, self.move_history
            )
        if pick is None:
            return
        fr, fc, tr, tc, promo = pick
        self._apply_move_recorded(fr, fc, tr, tc, promo)
        self.selected = None
        self.legal_targets = []
        self._update_status()
        self._schedule_draw()
        self._maybe_schedule_computer_move()

    def _ask_promotion(self, mover_color: str) -> Optional[str]:
        """Modal Q/R/B/N choice; returns None if the dialog is closed without a pick."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Promotion")
        dlg.configure(bg=self.BG)
        dlg.transient(self.root)
        dlg.grab_set()
        result: List[Optional[str]] = [None]

        def choose(p: str) -> None:
            result[0] = p
            dlg.destroy()

        tk.Label(
            dlg,
            text="Promote pawn to:",
            fg=self.FG,
            bg=self.BG,
            font=("Helvetica", 14),
        ).pack(pady=(14, 6))
        row = tk.Frame(dlg, bg=self.BG)
        row.pack(pady=10, padx=14)
        for kind in ("Q", "R", "B", "N"):
            label = UNICODE.get((mover_color, kind), kind)
            self._selection_button(row, label, lambda k=kind: choose(k), padx=10, pady=8).pack(side=tk.LEFT, padx=3)
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
        dlg.resizable(False, False)
        self.root.wait_window(dlg)
        return result[0]

    def _on_click(self, evt: tk.Event) -> None:
        if self.state is None:
            return
        if self.play_mode == "replay":
            return
        if not self._at_live_position():
            return
        if game_status(self.state) in GAME_OVER_STATUSES:
            return
        if self.play_mode == "cpu_vs_cpu":
            return
        if self._is_computer_turn():
            return
        hit = self._rc_from_xy(evt.x, evt.y)
        if hit is None:
            return
        r, c = hit
        if self.selected is None:
            p = piece_at(self.state, r, c)
            if p and p[0] == self.state.turn:
                self.selected = (r, c)
                self.legal_targets = [(a, b) for a, b, _ in legal_moves(self.state, r, c)]
            self._update_status()
            self._schedule_draw()
            return

        sr, sc = self.selected
        if (r, c) == (sr, sc):
            self.selected = None
            self.legal_targets = []
            self._schedule_draw()
            return

        moves = legal_moves(self.state, sr, sc)
        chosen: Optional[Tuple[int, int, Optional[str]]] = None
        to_here = [(tr, tc, pr) for tr, tc, pr in moves if tr == r and tc == c]
        if to_here:
            promo_kinds = {pr for tr, tc, pr in to_here if pr is not None}
            if len(promo_kinds) > 1:
                mover = piece_at(self.state, sr, sc)
                pr = self._ask_promotion(mover[0]) if mover else None
                if pr is None or pr not in promo_kinds:
                    self._schedule_draw()
                    return
                chosen = (r, c, pr)
            elif len(promo_kinds) == 1:
                chosen = (r, c, next(iter(promo_kinds)))
            else:
                chosen = (r, c, None)
        if chosen:
            tr, tc, promo = chosen
            self._apply_move_recorded(sr, sc, tr, tc, promo)
            self.selected = None
            self.legal_targets = []
        self._update_status()
        self._schedule_draw()
        self._maybe_schedule_computer_move()

    def _update_status(self) -> None:
        if self.state is None:
            return
        st = game_status(self.state)
        turn_word = "White" if self.state.turn == "w" else "Black"
        suffix = ""
        if self.play_mode == "cpu_vs_cpu" and st in ("Playing", "Check"):
            pw, pb = self.cpu_profile_w or "?", self.cpu_profile_b or "?"
            prof = pw if self.state.turn == "w" else pb
            side = "White" if self.state.turn == "w" else "Black"
            suffix = f" — {side} ({prof}) thinking…"
        elif self.play_mode == "computer" and self.computer_profile in ENGINE_PROFILES and st in ("Playing", "Check"):
            name = self.computer_profile
            if self._is_computer_turn():
                suffix = f" — {name} is thinking…"
            elif self.human_color == self.state.turn:
                suffix = " — your move"
        if st in GAME_OVER_STATUSES and not self._logged_game_end and self.play_mode != "replay":
            self._logged_game_end = True
            joined = ",".join(self.move_history)
            self._log_file_append(f"END\t{st}\tply={len(self.move_history)}\tmoves={joined}")
            if self.move_history and len(self.snapshots) == len(self.move_history) + 1:
                learn_record_completed_game(self.snapshots, self.move_history, st)
        rp = "Replay — " if self.play_mode == "replay" else ""
        if st == "Checkmate":
            winner = "Black" if self.state.turn == "w" else "White"
            self.status_var.set(rp + f"Checkmate — {winner} wins")
        elif st == "Stalemate":
            self.status_var.set(rp + "Stalemate — draw")
        elif st == "Draw50":
            self.status_var.set(rp + "Draw — 50-move rule (100 half-moves without pawn move or capture)")
        elif st == "DrawRepetition":
            self.status_var.set(rp + "Draw — threefold repetition")
        elif st == "DrawMaterial":
            self.status_var.set(rp + "Draw — insufficient material")
        elif st == "Check":
            self.status_var.set(rp + f"{turn_word} to move — in check{suffix}")
        else:
            self.status_var.set(rp + f"{turn_word} to move{suffix}")
        self._sync_move_list()
        self._update_replay_buttons()

    def _draw(self) -> None:
        self._draw_scheduled = False
        self.canvas.delete("all")
        if self.state is None:
            return
        ox, oy, cell = self._board_px()
        light = "#eeeed2"
        dark = "#4a6fa5"

        for drow in range(8):
            for dcol in range(8):
                brow, bcol = self._display_to_board(drow, dcol)
                x0 = ox + dcol * cell
                y0 = oy + drow * cell
                fill = light if (brow + bcol) % 2 == 0 else dark
                if self.selected and self.selected == (brow, bcol):
                    fill = "#c4d8f2" if (brow + bcol) % 2 == 0 else "#6b94c9"
                elif (brow, bcol) in self.legal_targets:
                    fill = "#dce8fa" if (brow + bcol) % 2 == 0 else "#7aa3d4"
                self.canvas.create_rectangle(x0, y0, x0 + cell, y0 + cell, fill=fill, outline="")

        font_size = max(int(cell * 0.62), 18)
        for drow in range(8):
            for dcol in range(8):
                brow, bcol = self._display_to_board(drow, dcol)
                p = piece_at(self.state, brow, bcol)
                if not p:
                    continue
                ch = UNICODE.get(p, "?")
                x0 = ox + dcol * cell
                y0 = oy + drow * cell
                self.canvas.create_text(
                    x0 + cell / 2,
                    y0 + cell / 2,
                    text=ch,
                    font=("Apple Symbols", font_size) if self._darwin_symbols() else ("Segoe UI Symbol", font_size),
                    anchor="center",
                )

        small = max(int(cell * 0.14), 9)
        label_fill = "#a8a8a8"
        for j in range(8):
            _, bcol = self._display_to_board(7, j)
            fl = chr(ord("a") + bcol)
            self.canvas.create_text(
                ox + j * cell + cell / 2,
                oy + 8 * cell + small,
                text=fl,
                fill=label_fill,
                font=("Helvetica", small),
            )
        for i in range(8):
            brow, _ = self._display_to_board(i, 0)
            rank = 8 - brow
            self.canvas.create_text(
                ox - small,
                oy + i * cell + cell / 2,
                text=str(rank),
                fill=label_fill,
                font=("Helvetica", small),
                anchor="e",
            )

    @staticmethod
    def _darwin_symbols() -> bool:
        import sys

        return sys.platform == "darwin"

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ChessApp().run()
