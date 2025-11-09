# app.py
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import numpy as np, random, math

app = Flask(__name__)
CORS(app)

# ----------------------------
# Game state
# ----------------------------
board = np.zeros((4, 4), dtype=int)
score = 0

# ----------------------------
# Tile mechanics
# ----------------------------
def add_new_tile(b):
    empties = list(zip(*np.where(b == 0)))
    if empties:
        r, c = random.choice(empties)
        b[r][c] = 2 if random.random() < 0.9 else 4


def move_left(b):
    global score
    new = np.zeros_like(b)
    for i in range(4):
        row = [x for x in b[i] if x != 0]
        merged = []
        j = 0
        while j < len(row):
            if j + 1 < len(row) and row[j] == row[j + 1]:
                val = row[j] * 2
                score += val
                merged.append(val)
                j += 2
            else:
                merged.append(row[j])
                j += 1
        merged += [0] * (4 - len(merged))
        new[i] = merged
    return new


def rotate_board(b, k):
    return np.rot90(b, k)


def move_board(b, direction, add_tile_flag=True):
    prev = b.copy()
    if direction == 'up':
        temp = rotate_board(b, 1)
        temp = move_left(temp)
        new = rotate_board(temp, -1)
    elif direction == 'down':
        temp = rotate_board(b, -1)
        temp = move_left(temp)
        new = rotate_board(temp, 1)
    elif direction == 'right':
        new = np.fliplr(move_left(np.fliplr(b)))
    elif direction == 'left':
        new = move_left(b)
    else:
        return b.copy()

    if add_tile_flag and not np.array_equal(prev, new):
        add_new_tile(new)
    return new


# ----------------------------
# Evaluation Heuristics
# ----------------------------
def count_empty(b):
    return int(np.sum(b == 0))

def max_tile(b):
    return int(np.max(b))

def smoothness(b):
    s = 0
    for i in range(4):
        for j in range(3):
            s -= abs(int(b[i,j]) - int(b[i,j+1]))
    for j in range(4):
        for i in range(3):
            s -= abs(int(b[i,j]) - int(b[i+1,j]))
    return s

def monotonicity(b):
    sc = 0
    for row in b:
        sc += sum([1 if row[i] >= row[i+1] else 0 for i in range(3)])
    for col in b.T:
        sc += sum([1 if col[i] >= col[i+1] else 0 for i in range(3)])
    return sc

def evaluate_board(b):
    w_empty = 2.7
    w_max = 1.5
    w_smooth = 0.08
    w_mono = 0.9
    e = count_empty(b)
    mx = max_tile(b) if np.any(b) else 1
    sm = smoothness(b)
    mo = monotonicity(b)
    return float((w_empty * e) + (w_max * math.log2(mx)) + (w_smooth * sm) + (w_mono * mo))


# ----------------------------
# Expectimax Algorithm
# ----------------------------
def simulate_after_move(b, move_dir):
    before = b.copy()
    after = move_board(b.copy(), move_dir, add_tile_flag=False)
    moved = not np.array_equal(before, after)
    merged = np.any(after > before)
    if not moved and not merged:
        return None
    return after


def expectimax(b, depth, is_player):
    if depth == 0 or not np.any(b == 0):
        return evaluate_board(b)

    if is_player:
        best = -float('inf')
        for mv in ['up','down','left','right']:
            nb = simulate_after_move(b, mv)
            if nb is None:
                continue
            val = expectimax(nb, depth - 1, False)
            best = max(best, val)
        return best if best != -float('inf') else evaluate_board(b)
    else:
        empties = list(zip(*np.where(b == 0)))
        if not empties:
            return evaluate_board(b)
        total = 0
        for (r,c) in empties:
            for val, p in [(2,0.9),(4,0.1)]:
                nb = b.copy()
                nb[r,c] = val
                total += p * expectimax(nb, depth - 1, True)
        return total / len(empties)


def get_move_with_explanation(b, depth=2):
    move_scores, details = {}, {}
    for mv in ['up','down','left','right']:
        nb = simulate_after_move(b, mv)
        if nb is None:
            continue
        sc = expectimax(nb, depth - 1, False)
        move_scores[mv] = sc
        details[mv] = {
            "empty_after": count_empty(nb),
            "max_after": max_tile(nb),
            "smooth_after": smoothness(nb),
            "monotonicity_after": monotonicity(nb),
            "eval": evaluate_board(nb)
        }

    if not move_scores:
        return None, {}, "No valid moves available."

    best = max(move_scores, key=lambda k: move_scores[k])
    f = details[best]
    explanation = (
        f"🤖 Expected utility: {round(move_scores[best], 2)} | "
        f"Empty tiles after move: {f['empty_after']} | "
        f"Max tile after move: {f['max_after']} | "
        f"Monotonicity: {f['monotonicity_after']} | "
        f"Reason: Chose move with highest expected utility."
    )
    return best, move_scores, explanation


# ----------------------------
# Helper
# ----------------------------
def has_valid_move(b):
    for mv in ['up','down','left','right']:
        if simulate_after_move(b, mv) is not None:
            return True
    return False


# ----------------------------
# Flask Routes
# ----------------------------
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/get_board')
def get_board():
    return jsonify({"board": board.tolist(), "score": score})


@app.route('/move/<direction>')
def move_direction(direction):
    global board
    board[:] = move_board(board, direction)
    game_over = not has_valid_move(board)
    return jsonify({"board": board.tolist(), "score": score, "game_over": game_over})


@app.route('/ai_suggest', methods=['POST'])
def ai_suggest():
    data = request.get_json()
    b = np.array(data.get("board", []))
    depth = int(data.get("depth", 2))

    best_move, move_scores, explanation = get_move_with_explanation(b, depth)
    return jsonify({
        "best_move": best_move,
        "scores": move_scores,
        "explanation": explanation
    })


# ----------------------------
# Run
# ----------------------------
if __name__ == '__main__':
    add_new_tile(board)
    add_new_tile(board)
    app.run(debug=True)
