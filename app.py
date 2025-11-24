from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import numpy as np
import random
import math

app = Flask(__name__)
CORS(app)

# ----------------------------
# 2048 MOVE LOGIC(FOR AI SIMULATION)
# ----------------------------

def move_left(board):
    """Return a new board after moving LEFT (no tile spawning, no score)."""
    new_board = np.zeros_like(board)
    for i in range(4):
        row = [x for x in board[i] if x != 0]
        result = []
        j = 0
        while j < len(row):
            if j + 1 < len(row) and row[j] == row[j + 1]:
                result.append(row[j] * 2)
                j += 2
            else:
                result.append(row[j])
                j += 1
        while len(result) < 4:
            result.append(0)
        new_board[i] = result
    return new_board

def rotate_board(b, k):
    return np.rot90(b, k)

def move_board(b, direction):
    """Simulate a move in given direction. No new tile is added."""
    if direction == "up":
        tmp = rotate_board(b, 1)
        moved = move_left(tmp)
        return rotate_board(moved, -1)
    elif direction == "down":
        tmp = rotate_board(b, -1)
        moved = move_left(tmp)
        return rotate_board(moved, 1)
    elif direction == "left":
        return move_left(b)
    elif direction == "right":
        return np.fliplr(move_left(np.fliplr(b)))
    else:
        return b.copy()

def simulate_after_move(b, direction):
    """Return board after move OR None if nothing changes (invalid move)."""
    before = b.copy()
    after = move_board(b.copy(), direction)
    moved = not np.array_equal(before, after)
    merged = np.any(after > before)
    if not moved and not merged:
        return None
    return after

# ----------------------------
# HEURISTIC EVALUATION
# ----------------------------

def count_empty(b):
    return int(np.sum(b == 0))

def max_tile(b):
    return int(np.max(b)) if np.any(b) else 0

def smoothness(b):
    s = 0
    for i in range(4):
        for j in range(3):
            s -= abs(int(b[i, j]) - int(b[i, j + 1]))
    for j in range(4):
        for i in range(3):
            s -= abs(int(b[i, j]) - int(b[i + 1, j]))
    return s

def monotonicity(b):
    sc = 0
    for row in b:
        sc += sum(1 for i in range(3) if row[i] >= row[i + 1])
    for col in b.T:
        sc += sum(1 for i in range(3) if col[i] >= col[i + 1])
    return sc

def evaluate_board(b):
    # Weights can be tuned
    w_empty = 2.7
    w_max = 1.5
    w_smooth = 0.08
    w_mono = 0.9

    e = count_empty(b)
    mx = max_tile(b) if max_tile(b) > 0 else 1
    sm = smoothness(b)
    mo = monotonicity(b)

    return float(w_empty * e + w_max * math.log2(mx) + w_smooth * sm + w_mono * mo)

# ----------------------------
# EXPECTIMAX
# ----------------------------

def expectimax(board, depth, is_player):
    if depth == 0 or not np.any(board == 0):
        return evaluate_board(board)

    if is_player:
        best = -float("inf")
        for mv in ["up", "down", "left", "right"]:
            nb = simulate_after_move(board, mv)
            if nb is None:
                continue
            val = expectimax(nb, depth - 1, False)
            if val > best:
                best = val
        return best if best != -float("inf") else evaluate_board(board)
    else:
        empties = list(zip(*np.where(board == 0)))
        if not empties:
            return evaluate_board(board)
        total = 0.0
        for (r, c) in empties:
            for val, p in [(2, 0.9), (4, 0.1)]:
                nb = board.copy()
                nb[r, c] = val
                total += p * expectimax(nb, depth - 1, True)
        return total / len(empties)

def get_move_with_explanation(board, depth=2):
    move_scores = {}
    details = {}

    for mv in ["up", "down", "left", "right"]:
        nb = simulate_after_move(board, mv)
        if nb is None:
            continue
        sc = expectimax(nb, depth - 1, False)
        move_scores[mv] = sc
        details[mv] = {
            "empty_after": count_empty(nb),
            "max_after": max_tile(nb),
            "smooth_after": smoothness(nb),
            "monotonicity_after": monotonicity(nb),
            "eval": evaluate_board(nb),
        }

    if not move_scores:
        return None, {}, "No valid moves available."

    best_move = max(move_scores, key=lambda m: move_scores[m])
    f = details[best_move]

    explanation = (
        f"Expected utility: {round(move_scores[best_move], 2)} | "
        f"Empty tiles after move: {f['empty_after']} | "
        f"Max tile after move: {f['max_after']} | "
        f"Monotonicity: {f['monotonicity_after']} | "
        "Reason: Chose the move with the highest expected heuristic score."
    )

    return best_move, move_scores, explanation

# ----------------------------
# INSIGHT GENERATION (NO MOVE)
# ----------------------------

def generate_insights(board, depth=2):
    insights = []

    empty = count_empty(board)
    mx = max_tile(board)
    mono = monotonicity(board)

    # General strategy hints
    if empty <= 6:
        insights.append("You should increase empty spaces; the board is getting crowded.")
    else:
        insights.append("Good job keeping enough empty spaces on the board.")

    if mx < 128:
        insights.append("Merging smaller tiles earlier will help you build higher tiles faster.")
    elif mx >= 512 and empty <= 4:
        insights.append("You should increase empty spaces before reaching larger tiles like 512+.")
    else:
        insights.append("Try to keep your highest tile in one corner to improve monotonicity.")

    if mono < 6:
        insights.append("Your board is not very monotonic; try to keep rows/columns in increasing or decreasing order.")
    else:
        insights.append("Good move! Your tile ordering is relatively monotonic.")

    # Bonus: best-move based insight without revealing the move
    best_move, move_scores, _ = get_move_with_explanation(board, depth)
    if best_move is not None and move_scores:
        insights.append("A more structured merging pattern would improve your long-term position.")

    return insights

# ----------------------------
# FLASK ROUTES
# ----------------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ai_suggest", methods=["POST"])
def ai_suggest():
    data = request.get_json()
    board_state = np.array(data.get("board", []), dtype=int)
    depth = int(data.get("depth", 2))

    player_move = data.get("playerMove")

    best_move, move_scores, explanation = get_move_with_explanation(board_state, depth)

# Coach Logic
    if player_move:
       if best_move == player_move:
          coach_msg = f"Good move! {player_move.upper()} was the optimal choice."
       else:
        coach_msg = f"A better alternative could have been {best_move.upper()}."
    else:
        coach_msg = ""

    return jsonify({
       "best_move": best_move,
       "scores": move_scores,
       "explanation": explanation,
       "coach_msg": coach_msg
    })


@app.route("/ai_insight", methods=["POST"])
def ai_insight():
    data = request.get_json()
    board_state = np.array(data.get("board", []), dtype=int)
    depth = int(data.get("depth", 2))

    insights = generate_insights(board_state, depth)
    return jsonify({"insights": insights})

if __name__ == "__main__":
    app.run(debug=True)
