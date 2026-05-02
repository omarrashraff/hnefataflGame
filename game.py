"""
Hnefatafl (Viking Chess) - CS361 AI Project
Two-player asymmetric strategy game with Alpha-Beta Pruning AI
"""

import tkinter as tk
from tkinter import messagebox, ttk
import copy
import math
import threading

# ─── BOARD CONSTANTS ───────────────────────────────────────────────────────────
EMPTY    = 0
ATTACKER = 1   # Black
DEFENDER = 2   # White
KING     = 3

BOARD_SIZE = 11

# Corner squares (King wins by reaching these)
CORNERS = {(0, 0), (0, 10), (10, 0), (10, 10)}
THRONE  = (5, 5)

# Difficulty depths
DIFFICULTY = {"Easy": 1.0, "Medium": 3.0, "Hard": 6.0}  # seconds per move


# ─── BOARD REPRESENTATION ──────────────────────────────────────────────────────
def initial_board():
    """Returns the 11×11 starting board as a 2D list."""
    b = [[EMPTY]*BOARD_SIZE for _ in range(BOARD_SIZE)]

    # King on throne
    b[5][5] = KING

    # 12 Defenders around king (cross formation)
    defenders = [
        (3,5),(4,5),(6,5),(7,5),
        (5,3),(5,4),(5,6),(5,7),
        (4,4),(4,6),(6,4),(6,6)
    ]
    for r, c in defenders:
        b[r][c] = DEFENDER

    # 24 Attackers in 4 groups of 6 on perimeter
    attackers = [
        # Top
        (0,3),(0,4),(0,5),(0,6),(0,7),(1,5),
        # Bottom
        (10,3),(10,4),(10,5),(10,6),(10,7),(9,5),
        # Left
        (3,0),(4,0),(5,0),(6,0),(7,0),(5,1),
        # Right
        (3,10),(4,10),(5,10),(6,10),(7,10),(5,9),
    ]
    for r, c in attackers:
        b[r][c] = ATTACKER

    return b


# ─── MOVE GENERATION ───────────────────────────────────────────────────────────
def _would_be_sandwiched(board, r, c, piece):
    """
    Returns True if placing `piece` at (r,c) puts it between two
    hostile anchors on either axis — meaning it would be immediately captured.
    Throne and corners count as hostile anchors. Board edges do NOT.
    """
    is_attacker = (piece == ATTACKER)

    def is_hostile_anchor(rr, cc):
        if not (0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE):
            return False  # walls do not count as anchors
        cell = board[rr][cc]
        if is_attacker:
            return cell in (DEFENDER, KING) or (rr, cc) == THRONE or (rr, cc) in CORNERS
        else:
            return cell == ATTACKER or (rr, cc) == THRONE or (rr, cc) in CORNERS

    for (dr1, dc1), (dr2, dc2) in [((-1,0),(1,0)), ((0,-1),(0,1))]:
        if is_hostile_anchor(r+dr1, c+dc1) and is_hostile_anchor(r+dr2, c+dc2):
            return True
    return False


def get_moves(board, is_attacker_turn):
    """Returns list of all legal moves: (from_row, from_col, to_row, to_col)."""
    moves = []
    piece_types = [ATTACKER] if is_attacker_turn else [DEFENDER, KING]

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            piece = board[r][c]
            if piece in piece_types:
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    while 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                        dest = board[nr][nc]
                        if dest != EMPTY:
                            break
                        # Throne is restricted: only king may rest on it
                        if (nr, nc) == THRONE and piece != KING:
                            nr += dr; nc += dc
                            continue
                        # Corners: only king may enter
                        if (nr, nc) in CORNERS and piece != KING:
                            nr += dr; nc += dc
                            continue
                        # Exclude squares where piece would be sandwiched
                        if not _would_be_sandwiched(board, nr, nc, piece):
                            moves.append((r, c, nr, nc))
                        nr += dr; nc += dc
    return moves


# ─── APPLY MOVE & CAPTURE ──────────────────────────────────────────────────────
def apply_move(board, move):
    """Returns new board state after move, with captures resolved."""
    r1, c1, r2, c2 = move
    b = copy.deepcopy(board)
    piece = b[r1][c1]
    b[r1][c1] = EMPTY
    b[r2][c2] = piece

    # King is unarmed: only soldiers (ATTACKER or DEFENDER) may perform captures
    if piece == KING:
        return b

    is_attacker_piece = (piece == ATTACKER)

    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r2+dr, c2+dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            continue

        neighbour = b[nr][nc]

        if is_attacker_piece:
            if neighbour not in (DEFENDER, KING):
                continue
        else:
            if neighbour != ATTACKER:
                continue

        nr2, nc2 = nr+dr, nc+dc

        beyond_friendly = False
        if 0 <= nr2 < BOARD_SIZE and 0 <= nc2 < BOARD_SIZE:
            cell = b[nr2][nc2]
            if is_attacker_piece:
                beyond_friendly = (cell == ATTACKER or (nr2,nc2) == THRONE or (nr2,nc2) in CORNERS)
            else:
                beyond_friendly = (cell == DEFENDER or (nr2,nc2) == THRONE or (nr2,nc2) in CORNERS)

        if not beyond_friendly:
            continue

        # King cannot be taken by custodial capture alone; requires all-4 surround
        if neighbour == KING:
            continue

        b[nr][nc] = EMPTY

    return b


# ─── FAST BOARD (bytearray) HELPERS FOR AI ─────────────────────────────────────
def _board_to_arr(board):
    return bytearray(board[r][c] for r in range(BOARD_SIZE) for c in range(BOARD_SIZE))

def _get(arr, r, c):
    return arr[r * BOARD_SIZE + c]

def _set(arr, r, c, v):
    arr[r * BOARD_SIZE + c] = v

def _apply_move_fast(arr, move):
    """Apply move in-place on bytearray. Returns undo list of (index, old_val)."""
    r1, c1, r2, c2 = move
    piece = _get(arr, r1, c1)
    undo = [(r1*BOARD_SIZE+c1, piece), (r2*BOARD_SIZE+c2, _get(arr, r2, c2))]
    _set(arr, r1, c1, EMPTY)
    _set(arr, r2, c2, piece)

    if piece == KING:
        return undo

    is_atk = (piece == ATTACKER)
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r2+dr, c2+dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            continue
        nb = _get(arr, nr, nc)
        if is_atk:
            if nb not in (DEFENDER, KING): continue
        else:
            if nb != ATTACKER: continue
        nr2, nc2 = nr+dr, nc+dc
        ok = False
        if 0 <= nr2 < BOARD_SIZE and 0 <= nc2 < BOARD_SIZE:
            cell = _get(arr, nr2, nc2)
            if is_atk:
                ok = (cell == ATTACKER or (nr2,nc2) == THRONE or (nr2,nc2) in CORNERS)
            else:
                ok = (cell == DEFENDER or (nr2,nc2) == THRONE or (nr2,nc2) in CORNERS)
        if not ok or nb == KING:
            continue
        undo.append((nr*BOARD_SIZE+nc, nb))
        _set(arr, nr, nc, EMPTY)
    return undo

def _undo_move_fast(arr, undo):
    for idx, val in undo:
        arr[idx] = val

def _check_winner_fast(arr):
    SZ = BOARD_SIZE
    kr = kc = -1
    for i in range(SZ * SZ):
        if arr[i] == KING:
            kr, kc = i // SZ, i % SZ; break
    if kr == -1: return 'attacker'
    if (kr, kc) in CORNERS: return 'defender'
    for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
        nr, nc = kr+dr, kc+dc
        if not (0<=nr<SZ and 0<=nc<SZ): continue
        if (nr,nc) in CORNERS: continue
        if arr[nr*SZ+nc] != ATTACKER: return None
    return 'attacker'

def _utility_fast(arr, _unused):
    SZ = BOARD_SIZE
    kr = kc = -1
    atk = def_ = 0
    for i in range(SZ * SZ):
        v = arr[i]
        if v == KING:        kr, kc = i // SZ, i % SZ
        elif v == ATTACKER:  atk += 1
        elif v == DEFENDER:  def_ += 1
    if kr == -1: return 10000
    if (kr, kc) in CORNERS: return -10000
    min_cd = min(abs(kr-cr)+abs(kc-cc) for cr,cc in CORNERS)
    sn = sc = 0
    for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
        nr, nc = kr+dr, kc+dc
        if not (0<=nr<SZ and 0<=nc<SZ): continue
        if (nr,nc) in CORNERS: continue
        sn += 1
        if arr[nr*SZ+nc] == ATTACKER: sc += 1
    sm = sn - sc
    enc = 500 if sm==0 else (200 if sm==1 else (60 if sm==2 else sc*15)) if sn else 0
    return (atk-def_)*10 + min_cd*5 + enc - def_*8

def _get_moves_fast(arr, is_attacker_turn):
    """Move generation on bytearray."""
    moves = []
    SZ = BOARD_SIZE
    piece_types = (ATTACKER,) if is_attacker_turn else (DEFENDER, KING)
    for r in range(SZ):
        row = r * SZ
        for c in range(SZ):
            piece = arr[row + c]
            if piece not in piece_types:
                continue
            is_atk = (piece == ATTACKER)
            for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                nr, nc = r+dr, c+dc
                while 0 <= nr < SZ and 0 <= nc < SZ:
                    if arr[nr*SZ+nc] != EMPTY:
                        break
                    if (nr, nc) == THRONE and piece != KING:
                        nr += dr; nc += dc; continue
                    if (nr, nc) in CORNERS and piece != KING:
                        nr += dr; nc += dc; continue
                    ok = True
                    for d1r,d1c,d2r,d2c in ((-1,0,1,0),(0,-1,0,1)):
                        ar1,ac1 = nr+d1r, nc+d1c
                        ar2,ac2 = nr+d2r, nc+d2c
                        in1 = 0<=ar1<SZ and 0<=ac1<SZ
                        in2 = 0<=ar2<SZ and 0<=ac2<SZ
                        if is_atk:
                            h1 = in1 and (arr[ar1*SZ+ac1] in (DEFENDER,KING) or (ar1,ac1)==THRONE or (ar1,ac1) in CORNERS)
                            h2 = in2 and (arr[ar2*SZ+ac2] in (DEFENDER,KING) or (ar2,ac2)==THRONE or (ar2,ac2) in CORNERS)
                        else:
                            h1 = in1 and (arr[ar1*SZ+ac1]==ATTACKER or (ar1,ac1)==THRONE or (ar1,ac1) in CORNERS)
                            h2 = in2 and (arr[ar2*SZ+ac2]==ATTACKER or (ar2,ac2)==THRONE or (ar2,ac2) in CORNERS)
                        if h1 and h2:
                            ok = False; break
                    if ok:
                        moves.append((r, c, nr, nc))
                    nr += dr; nc += dc
    return moves


def check_winner(board):
    """Returns: 'attacker', 'defender', or None"""
    king_pos = None
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == KING:
                king_pos = (r, c)
                break

    if king_pos is None:
        return 'attacker'

    kr, kc = king_pos

    if king_pos in CORNERS:
        return 'defender'

    open_sides = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = kr+dr, kc+dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            continue
        if (nr, nc) in CORNERS:
            continue
        open_sides.append((nr, nc))

    if open_sides and all(board[nr][nc] == ATTACKER for nr, nc in open_sides):
        return 'attacker'

    return None


# ─── UTILITY FUNCTION ──────────────────────────────────────────────────────────
def utility(board, is_attacker_turn):
    """Heuristic evaluation from attacker's perspective (positive = good for attacker)."""
    king_pos = None
    attacker_count = 0
    defender_count = 0

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell == KING:
                king_pos = (r, c)
            elif cell == ATTACKER:
                attacker_count += 1
            elif cell == DEFENDER:
                defender_count += 1

    if king_pos is None:
        return 10000
    if king_pos in CORNERS:
        return -10000

    kr, kc = king_pos
    min_corner_dist = min(abs(kr - cr) + abs(kc - cc) for cr, cc in CORNERS)

    open_sides = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = kr+dr, kc+dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            continue
        if (nr, nc) in CORNERS:
            continue
        open_sides.append((nr, nc))

    sides_needed   = len(open_sides)
    sides_covered  = sum(1 for nr, nc in open_sides if board[nr][nc] == ATTACKER)
    sides_missing  = sides_needed - sides_covered

    encircle_score = 0
    if sides_needed > 0:
        if sides_missing == 0:
            encircle_score = 500
        elif sides_missing == 1:
            encircle_score = 120
        elif sides_missing == 2:
            encircle_score = 40
        else:
            encircle_score = sides_covered * 15

    score = 0
    score += (attacker_count - defender_count) * 10
    score += min_corner_dist * 5
    score += encircle_score
    score -= defender_count * 8

    return score


# ─── ALPHA-BETA PRUNING (fast bytearray + transposition table) ────────────────
_TT = {}

def _tt_key(arr):
    return bytes(arr)

def _score_move_fast(arr, move, is_attacker_turn):
    r1, c1, r2, c2 = move
    bonus = 0
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r2+dr, c2+dc
        if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
            nb = _get(arr, nr, nc)
            if is_attacker_turn:
                if nb == KING:      bonus += 80
                elif nb == DEFENDER: bonus += 40
            else:
                if nb == ATTACKER:  bonus += 40
    return bonus


def alpha_beta_fast(arr, depth, alpha, beta, maximizing, is_attacker_turn, deadline=None):
    import time as _time
    if deadline and _time.time() >= deadline:
        raise _TimeUp()

    key = _tt_key(arr)
    tt_entry = _TT.get(key)
    if tt_entry and tt_entry[0] >= depth:
        tt_depth, tt_flag, tt_score, tt_move = tt_entry
        if tt_flag == 0:   return tt_score, tt_move
        if tt_flag == 1:   alpha = max(alpha, tt_score)
        elif tt_flag == 2: beta  = min(beta,  tt_score)
        if alpha >= beta:  return tt_score, tt_move

    winner = _check_winner_fast(arr)
    if winner == 'attacker': return 10000 + depth, None
    if winner == 'defender': return -10000 - depth, None

    if depth == 0:
        return _utility_fast(arr, is_attacker_turn), None

    moves = _get_moves_fast(arr, is_attacker_turn)
    if not moves:
        return (10000 if is_attacker_turn else -10000), None

    tt_best = tt_entry[3] if tt_entry else None
    moves.sort(key=lambda m: (
        100 if m == tt_best else 0
    ) + _score_move_fast(arr, m, is_attacker_turn), reverse=True)

    best_move = moves[0]
    orig_alpha = alpha

    if maximizing:
        max_eval = -math.inf
        for move in moves:
            undo = _apply_move_fast(arr, move)
            ev, _ = alpha_beta_fast(arr, depth-1, alpha, beta, False, not is_attacker_turn, deadline)
            _undo_move_fast(arr, undo)
            if ev > max_eval:
                max_eval = ev
                best_move = move
            alpha = max(alpha, ev)
            if beta <= alpha: break
        flag = 0 if orig_alpha < max_eval < beta else (1 if max_eval >= beta else 2)
        _TT[key] = (depth, flag, max_eval, best_move)
        return max_eval, best_move
    else:
        min_eval = math.inf
        for move in moves:
            undo = _apply_move_fast(arr, move)
            ev, _ = alpha_beta_fast(arr, depth-1, alpha, beta, True, not is_attacker_turn, deadline)
            _undo_move_fast(arr, undo)
            if ev < min_eval:
                min_eval = ev
                best_move = move
            beta = min(beta, ev)
            if beta <= alpha: break
        flag = 0 if orig_alpha < min_eval < beta else (1 if min_eval >= beta else 2)
        _TT[key] = (depth, flag, min_eval, best_move)
        return min_eval, best_move


def get_best_move(board, is_attacker_turn, time_limit):
    """Iterative deepening with a time budget (seconds)."""
    import time as _time
    global _TT
    _TT = {}
    arr = _board_to_arr(board)
    maximizing = is_attacker_turn
    deadline = _time.time() + time_limit
    best = None
    for d in range(1, 20):
        if _time.time() >= deadline:
            break
        try:
            _, move = alpha_beta_fast(arr, d, -math.inf, math.inf,
                                      maximizing, is_attacker_turn,
                                      deadline)
            if move:
                best = move
        except _TimeUp:
            break
    return best


class _TimeUp(Exception):
    pass


# ─── GUI ───────────────────────────────────────────────────────────────────────
CELL = 52
MARGIN = 30
COLORS = {
    "bg":         "#1a120b",
    "board":      "#c8a87a",
    "board_alt":  "#b8976a",
    "grid":       "#7a5c3a",
    "attacker":   "#2d2d2d",
    "defender":   "#f5f0e8",
    "king":       "#ffd700",
    "throne":     "#8b1a1a",
    "corner":     "#5c3a1a",
    "select":     "#00e5ff",
    "move_hint":  "#90ee90",
    "text":       "#f5deb3",
    "btn":        "#3d2b1a",
    "btn_hover":  "#5c3a1a",
    "status_atk": "#ff6b6b",
    "status_def": "#87ceeb",
}

CANVAS_W = BOARD_SIZE * CELL + 2 * MARGIN
CANVAS_H = BOARD_SIZE * CELL + 2 * MARGIN


class HnefataflGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Hnefatafl — Viking Chess")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        self.board = initial_board()
        self.is_attacker_turn = True
        self.human_is_attacker = True
        self.difficulty = "Medium"
        self.selected = None
        self.hints = []
        self.game_over = False
        self.ai_thinking = False

        self._build_ui()
        self._draw_board()
        self._update_status()

    def _build_ui(self):
        top = tk.Frame(self.root, bg=COLORS["bg"], pady=8)
        top.pack(fill="x")

        tk.Label(top, text="⚔  HNEFATAFL", font=("Georgia", 20, "bold"),
                 bg=COLORS["bg"], fg=COLORS["text"]).pack()

        ctrl = tk.Frame(self.root, bg=COLORS["bg"])
        ctrl.pack(pady=4)

        tk.Label(ctrl, text="Play as:", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Georgia", 11)).grid(row=0, column=0, padx=6)

        self.side_var = tk.StringVar(value="Attacker (Black)")
        side_cb = ttk.Combobox(ctrl, textvariable=self.side_var, state="readonly", width=16,
                               values=["Attacker (Black)", "Defender (White)"])
        side_cb.grid(row=0, column=1, padx=6)

        tk.Label(ctrl, text="Difficulty:", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Georgia", 11)).grid(row=0, column=2, padx=6)

        self.diff_var = tk.StringVar(value="Medium")
        diff_cb = ttk.Combobox(ctrl, textvariable=self.diff_var, state="readonly", width=8,
                               values=["Easy", "Medium", "Hard"])
        diff_cb.grid(row=0, column=3, padx=6)

        btn = tk.Button(ctrl, text="New Game", font=("Georgia", 11, "bold"),
                        bg=COLORS["btn"], fg=COLORS["text"], relief="flat",
                        padx=10, command=self._new_game, cursor="hand2")
        btn.grid(row=0, column=4, padx=12)

        self.canvas = tk.Canvas(self.root, width=CANVAS_W, height=CANVAS_H,
                                bg=COLORS["board"], highlightthickness=0)
        self.canvas.pack(padx=MARGIN, pady=4)
        self.canvas.bind("<Button-1>", self._on_click)

        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(self.root, textvariable=self.status_var,
                                   font=("Georgia", 12), bg=COLORS["bg"],
                                   fg=COLORS["text"], pady=6)
        self.status_lbl.pack()

        leg = tk.Frame(self.root, bg=COLORS["bg"])
        leg.pack(pady=(0, 10))
        items = [
            ("●", COLORS["attacker"], "Attacker"),
            ("●", COLORS["defender"], "Defender"),
            ("♛", COLORS["king"],     "King"),
        ]
        for sym, col, label in items:
            tk.Label(leg, text=f"{sym} {label}", fg=col, bg=COLORS["bg"],
                     font=("Georgia", 10)).pack(side="left", padx=12)

    def _rc_to_xy(self, r, c):
        x = MARGIN + c * CELL + CELL // 2
        y = MARGIN + r * CELL + CELL // 2
        return x, y

    def _xy_to_rc(self, x, y):
        c = (x - MARGIN) // CELL
        r = (y - MARGIN) // CELL
        return r, c

    def _draw_board(self):
        self.canvas.delete("all")
        b = self.board

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x1 = MARGIN + c * CELL
                y1 = MARGIN + r * CELL
                x2 = x1 + CELL
                y2 = y1 + CELL

                if (r, c) in CORNERS:
                    fill = COLORS["corner"]
                elif (r, c) == THRONE:
                    fill = COLORS["throne"]
                elif (r + c) % 2 == 0:
                    fill = COLORS["board"]
                else:
                    fill = COLORS["board_alt"]

                if self.selected == (r, c):
                    fill = COLORS["select"]

                if (r, c) in self.hints:
                    fill = COLORS["move_hint"]

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill,
                                             outline=COLORS["grid"], width=1)

                if (r, c) in CORNERS:
                    self.canvas.create_text(x1+CELL//2, y1+CELL//2,
                                            text="✦", fill="#ffd700", font=("Arial", 12))

        pad = 8
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                cell = b[r][c]
                if cell == EMPTY:
                    continue
                x1 = MARGIN + c * CELL + pad
                y1 = MARGIN + r * CELL + pad
                x2 = MARGIN + (c+1) * CELL - pad
                y2 = MARGIN + (r+1) * CELL - pad

                if cell == ATTACKER:
                    self.canvas.create_oval(x1, y1, x2, y2,
                                            fill=COLORS["attacker"], outline="#555", width=2)
                elif cell == DEFENDER:
                    self.canvas.create_oval(x1, y1, x2, y2,
                                            fill=COLORS["defender"], outline="#aaa", width=2)
                elif cell == KING:
                    cx = (x1+x2)//2
                    cy = (y1+y2)//2
                    self.canvas.create_oval(x1, y1, x2, y2,
                                            fill=COLORS["king"], outline="#b8860b", width=2)
                    self.canvas.create_text(cx, cy, text="♛",
                                            font=("Arial", 18, "bold"), fill="#5c3a00")

        for i in range(BOARD_SIZE):
            x = MARGIN + i * CELL + CELL // 2
            self.canvas.create_text(x, MARGIN//2, text=str(i),
                                    fill=COLORS["text"], font=("Arial", 9))
            self.canvas.create_text(MARGIN//2, MARGIN + i * CELL + CELL//2,
                                    text=str(i), fill=COLORS["text"], font=("Arial", 9))

    def _update_status(self):
        if self.game_over:
            return
        if self.ai_thinking:
            self.status_var.set("🤖  AI is thinking...")
            self.status_lbl.config(fg="#ffaa00")
            return

        is_human_turn = (self.is_attacker_turn == self.human_is_attacker)
        side = "Attacker (Black)" if self.is_attacker_turn else "Defender (White)"
        who = "Your" if is_human_turn else "AI's"
        col = COLORS["status_atk"] if self.is_attacker_turn else COLORS["status_def"]
        self.status_var.set(f"{who} turn — {side}")
        self.status_lbl.config(fg=col)

    def _new_game(self):
        self.board = initial_board()
        self.is_attacker_turn = True
        self.human_is_attacker = (self.side_var.get() == "Attacker (Black)")
        self.difficulty = self.diff_var.get()
        self.selected = None
        self.hints = []
        self.game_over = False
        self.ai_thinking = False
        self._draw_board()
        self._update_status()

        if not self.human_is_attacker:
            self.root.after(400, self._ai_move)

    def _on_click(self, event):
        if self.game_over or self.ai_thinking:
            return
        if self.is_attacker_turn != self.human_is_attacker:
            return

        r, c = self._xy_to_rc(event.x, event.y)
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            return

        cell = self.board[r][c]

        if self.selected is None:
            if self._is_own_piece(cell):
                self.selected = (r, c)
                self.hints = self._calc_hints(r, c)
                self._draw_board()
        else:
            sr, sc = self.selected
            if (r, c) in self.hints:
                self._make_move(sr, sc, r, c)
            elif self._is_own_piece(cell):
                self.selected = (r, c)
                self.hints = self._calc_hints(r, c)
                self._draw_board()
            else:
                self.selected = None
                self.hints = []
                self._draw_board()

    def _is_own_piece(self, cell):
        if self.human_is_attacker:
            return cell == ATTACKER
        else:
            return cell in (DEFENDER, KING)

    def _calc_hints(self, r, c):
        moves = get_moves(self.board, self.is_attacker_turn)
        return [(tr, tc) for (fr, fc, tr, tc) in moves if fr == r and fc == c]

    def _make_move(self, r1, c1, r2, c2):
        self.board = apply_move(self.board, (r1, c1, r2, c2))
        self.selected = None
        self.hints = []
        self._draw_board()

        winner = check_winner(self.board)
        if winner:
            self._end_game(winner)
            return

        self.is_attacker_turn = not self.is_attacker_turn
        self._update_status()

        if self.is_attacker_turn != self.human_is_attacker:
            self.root.after(300, self._ai_move)

    def _ai_move(self):
        if self.game_over:
            return
        self.ai_thinking = True
        self._update_status()

        depth = DIFFICULTY[self.difficulty]

        def run():
            move = get_best_move(self.board, self.is_attacker_turn, depth)
            self.root.after(0, lambda: self._apply_ai_move(move))

        threading.Thread(target=run, daemon=True).start()

    def _apply_ai_move(self, move):
        self.ai_thinking = False
        if move is None or self.game_over:
            return

        self.board = apply_move(self.board, move)
        self._draw_board()

        winner = check_winner(self.board)
        if winner:
            self._end_game(winner)
            return

        self.is_attacker_turn = not self.is_attacker_turn
        self._update_status()

    def _end_game(self, winner):
        self.game_over = True
        if winner == 'attacker':
            msg = "⚔  Attackers Win!\nThe King has been captured."
            col = COLORS["status_atk"]
        else:
            msg = "👑  Defenders Win!\nThe King escaped to a corner!"
            col = COLORS["status_def"]

        self.status_var.set(msg.split("\n")[0])
        self.status_lbl.config(fg=col)
        messagebox.showinfo("Game Over", msg)


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = HnefataflGUI(root)
    root.mainloop()
