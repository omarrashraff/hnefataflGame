# ♟️ Hnefatafl — Viking Chess AI

Developed in collaboration with @minshawi0 as part of the Cryptography course at Cairo University, Faculty of Engineering.

An 11×11 asymmetric strategy board game from Viking-age Scandinavia, implemented in Python with a **Tkinter GUI** and an **Alpha-Beta Pruning AI** with iterative deepening and a transposition table.

> Built as a CS361 AI course project.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Game Rules](#game-rules)
- [AI Implementation](#ai-implementation)
- [Project Structure](#project-structure)
- [Board Representation](#board-representation)
- [How to Run](#how-to-run)

---

## Overview

Hnefatafl is an asymmetric two-player game: one side plays the **Attackers** (24 black pieces) trying to capture the King, and the other plays the **Defenders** (12 white pieces + King) trying to escort the King to any corner of the board.

This implementation features:
- Full rule-accurate 11×11 board with throne and corner squares
- Custodial capture with special King capture rules
- Anti-starvation move filtering (pieces cannot move into an immediately sandwiched position)
- A playable GUI with move hints, difficulty selection, and side selection
- AI opponent powered by Alpha-Beta Pruning with iterative deepening

---

## Game Rules

### Win Conditions
- **Attackers win** by surrounding the King on all open sides (walls and corners count as blockers, reducing the number of attackers needed near edges)
- **Defenders win** by moving the King to any of the 4 corner squares

### Movement
- All pieces move like rooks in chess (any number of squares horizontally or vertically)
- **Only the King** may land on the Throne (center) or the Corner squares
- Pieces may not move through other pieces

### Capture
- Capture is **custodial**: a piece is captured when an enemy moves to sandwich it between two hostile pieces on one axis
- The **Throne** and **Corner** squares act as hostile anchors (they help complete a capture even without a second piece)
- **Board edges do NOT count** as capture anchors
- The **King cannot be captured by custodial capture alone** — all open sides must be covered by attackers simultaneously
- The King is unarmed and cannot perform captures

### Special Rule — No Suicide Moves
Pieces cannot voluntarily move into a square where they would be immediately captured (sandwiched). This prevents trivial forced captures.

---

## AI Implementation

The AI is built on **Alpha-Beta Pruning** with several optimizations:

### Algorithm
- **Minimax with Alpha-Beta Pruning**: Standard adversarial search; the attacker maximizes the heuristic score, the defender minimizes it
- **Iterative Deepening**: Searches depths 1, 2, 3, … within a fixed time budget. The best move from the deepest completed depth is returned
- **Transposition Table**: Previously evaluated positions are cached with exact/lower-bound/upper-bound flags to avoid redundant computation

### Move Ordering
Moves are sorted before expansion to maximize pruning:
1. The best move from the transposition table is tried first
2. Moves that attack the King or adjacent defenders are prioritized

### Fast Board Representation
For AI search, the 2D list board is converted to a flat `bytearray` for significantly faster copy-free in-place operations. Moves are applied and undone using an undo log instead of deep copying the board.

### Heuristic Evaluation (`utility`)
The heuristic is evaluated from the attacker's perspective (positive = good for attacker):

| Component | Description |
|---|---|
| Material score | `(attackers - defenders) × 10` |
| King-to-corner distance | Manhattan distance to nearest corner × 5 (attacker wants King far from corners) |
| Encirclement score | Exponential reward as open King sides covered by attackers increases (500 = all sides covered, 120 = one missing, 40 = two missing) |
| Defender penalty | `defenders × 8` subtracted (fewer defenders = better for attacker) |

The encirclement score is **wall-aware**: near edges and corners, fewer attackers are needed to trigger the win condition, so the AI correctly values those positions.

### Difficulty Levels

| Level | Time Budget |
|---|---|
| Easy | 1 second per move |
| Medium | 3 seconds per move |
| Hard | 6 seconds per move |

---

## Project Structure

```
hnefataflGame/
│
├── hnefatafl.py        # Full game: board logic, AI, and GUI in one file
└── README.md
```

### Internal Modules (within `hnefatafl.py`)

| Section | Description |
|---|---|
| **Board Constants** | `EMPTY`, `ATTACKER`, `DEFENDER`, `KING`, `CORNERS`, `THRONE` |
| `initial_board()` | Sets up the 11×11 starting position |
| `get_moves()` | Generates all legal moves for a side (with sandwiching filter) |
| `_would_be_sandwiched()` | Checks if a destination square would immediately trap the moving piece |
| `apply_move()` | Deep-copies board, moves piece, resolves custodial captures |
| `check_winner()` | Detects King-captured or King-escaped conditions |
| `utility()` | Heuristic board evaluator |
| `_board_to_arr()` / `_apply_move_fast()` / `_undo_move_fast()` | Fast bytearray board for AI search |
| `_utility_fast()` | Fast heuristic on bytearray |
| `_get_moves_fast()` | Inlined move generation on bytearray |
| `alpha_beta_fast()` | Alpha-Beta Pruning with transposition table |
| `get_best_move()` | Iterative deepening driver |
| `HnefataflGUI` | Full Tkinter UI: drawing, click handling, AI thread |

---

## Board Representation

```
Initial 11×11 Board Layout:

  . . . A A A A A . . .
  . . . . . A . . . . .
  . . . . . . . . . . .
  A . . . . D . . . . A
  A . . . D D D . . . A
  A A . . D K D . . A A
  A . . . D D D . . . A
  A . . . . D . . . . A
  . . . . . . . . . . .
  . . . . . A . . . . .
  . . . A A A A A . . .

  A = Attacker  (24 total)
  D = Defender  (12 total)
  K = King      (starts on throne at center)
  ✦ = Corner escape squares (4 corners)
```

---

## How to Run

### Prerequisites
- Python 3.8 or higher
- `tkinter` (included with standard Python on Windows and most Linux distros)

On Ubuntu/Debian if tkinter is missing:
```bash
sudo apt-get install python3-tk
```

### Run

```bash
python hnefatafl.py
```

### Gameplay
1. Select your side (**Attacker** or **Defender**) and difficulty from the dropdowns
2. Click **New Game** to start
3. Click a piece to select it — valid move destinations are highlighted in green
4. Click a highlighted square to move
5. The AI will respond automatically after your move

---

## License

This project is for educational purposes.
