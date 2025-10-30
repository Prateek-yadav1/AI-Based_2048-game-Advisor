from flask import Flask, render_template, jsonify, request
import numpy as np
import random

app = Flask(__name__)

# Global game state (single-player local server)
board = np.zeros((4, 4), dtype=int)
score = 0
game_over = False

# -------------------------
# Helper functions
# -------------------------
def add_new_tile(b):
    empty = list(zip(*np.where(b == 0)))
    if not empty:
        r, c = random.choice(empty)
        b[r, c] = 4 if random.random() < 0.1 else 2
        return (r, c, int(b[r, c]))
    return None

def compress_row(row):
    """Move all non-zero to left, keep order."""
    new = [x for x in row if x != 0]
    new += [0] * (4 - len(new))
    return new

def merge_row(row):
    """Merge a single row (left) and return new row and gained score."""
    gained = 0
    row = compress_row(row)
    for i in range(3):
        if row[i] != 0 and row[i] == row[i+1]:
            row[i] *= 2
            gained += row[i]
            row[i+1] = 0
    row = compress_row(row)
    return row, gained

def move_left_board(b):
    """Return (new_board, gained_score, merged_positions) without mutating input."""
    new = np.zeros_like(b)
    gained = 0
    merged_positions = []  # (r, c) positions where merges happened (target cell)
    for r in range(4):
        row = list(b[r])
        new_row, g = merge_row(row)
        gained += g
        new[r] = new_row
        # To detect merged positions: compare merged effect
        # A simple way: if a cell in new_row equals sum of two equal adjacent in original,
        # and that pair existed, mark the target index.
        # We'll iterate original to detect merges:
        j = 0
        orig_nonzero = [x for x in row if x != 0]
        k = 0
        while k < len(orig_nonzero):
            if k + 1 < len(orig_nonzero) and orig_nonzero[k] == orig_nonzero[k+1]:
                # merged into column j
                merged_positions.append((r, j))
                j += 1
                k += 2
            else:
                j += 1
                k += 1
    return new, gained, merged_positions

def rotate_board(b, k):
    return np.rot90(b, k)

def apply_move(direction, add_tile=True):
    """Apply move and return dict with board, moved flag, gained, added tile info, merged positions."""
    global board, score, game_over
    prev = board.copy()
    if direction == 'left':
        new_board, gained, merged = move_left_board(prev)
    elif direction == 'right':
        # rotate twice (180) to reuse left logic
        rotated = rotate_board(prev, 2)
        moved_board, gained, merged_rel = move_left_board(rotated)
        new_board = rotate_board(moved_board, 2)
        # map merged_rel coords: rotated 180 maps (r,c) -> (3-r,3-c)
        merged = [(3 - r, 3 - c) for (r, c) in merged_rel]
    elif direction == 'up':
        rotated = rotate_board(prev, 1)  # 90 ccw
        moved_board, gained, merged_rel = move_left_board(rotated)
        new_board = rotate_board(moved_board, -1)
        # mapping from rotated coords (r,c) to original: (r,c) -> (c, 3-r)
        merged = [(c, 3 - r) for (r, c) in merged_rel]
    elif direction == 'down':
        rotated = rotate_board(prev, -1)  # 90 cw
        moved_board, gained, merged_rel = move_left_board(rotated)
        new_board = rotate_board(moved_board, 1)
        # mapping from rotated coords (r,c) to original: (r,c) -> (3-c, r)
        merged = [(3 - c, r) for (r, c) in merged_rel]
    else:
        return {"board": prev, "moved": False, "gained": 0, "added": None, "merged": []}

    moved = not np.array_equal(prev, new_board)
    added_info = None
    if moved:
        score += gained
        board[:] = new_board
        if add_tile:
            added = add_new_tile(board)
            added_info = added
        # detect game over
        if not can_move(board):
            game_over = True
    return {"board": board.copy(), "moved": moved, "gained": int(gained), "added": added_info, "merged": merged if moved else []}

def can_move(b):
    # if any zero -> can move
    if np.any(b == 0):
        return True
    # check horizontal merges
    for r in range(4):
        for c in range(3):
            if b[r, c] == b[r, c+1]:
                return True
    # check vertical merges
    for c in range(4):
        for r in range(3):
            if b[r, c] == b[r+1, c]:
                return True
    return False

def reset_game():
    global board, score, game_over
    board = np.zeros((4, 4), dtype=int)
    score = 0
    game_over = False
    add_new_tile(board)
    add_new_tile(board)

# -------------------------
# Routes
# -------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_board')
def get_board():
    return jsonify({"board": board.tolist(), "score": int(score), "game_over": bool(game_over)})

@app.route('/reset', methods=['GET'])
def reset_route():
    reset_game()
    return jsonify({"board": board.tolist(), "score": int(score), "game_over": bool(game_over)})

@app.route('/move', methods=['POST'])
def move_route():
    if not request.is_json:
        return jsonify({"error": "expected json"}), 400
    data = request.get_json()
    direction = data.get("direction")
    if direction not in ("left", "right", "up", "down"):
        return jsonify({"error": "invalid direction"}), 400
    result = apply_move(direction, add_tile=True)
    response = {
        "board": result["board"].tolist(),
        "moved": bool(result["moved"]),
        "gained": int(result["gained"]),
        "added": result["added"],   # either None or (r,c,value)
        "merged": result["merged"],
        "score": int(score),
        "game_over": bool(game_over)
    }
    return jsonify(response)

# Initialize once on start
reset_game()

from flask import Flask, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
