/* --------------------------
   GAME VARIABLES & INIT
---------------------------*/

const boardSize = 4;
let board = [];
let score = 0;
let aiMode = "suggestion";   // "suggestion" | "insight" | "coach"

function initBoard() {
  board = Array.from({ length: boardSize }, () => Array(boardSize).fill(0));
  score = 0;
  addNewTile();
  addNewTile();
  renderBoard();
}

/* --------------------------
   GAME FUNCTIONS
---------------------------*/

function addNewTile() {
  const emptyCells = [];
  for (let i = 0; i < boardSize; i++) {
    for (let j = 0; j < boardSize; j++) {
      if (board[i][j] === 0) emptyCells.push([i, j]);
    }
  }
  if (emptyCells.length > 0) {
    const [r, c] = emptyCells[Math.floor(Math.random() * emptyCells.length)];
    board[r][c] = Math.random() < 0.9 ? 2 : 4;
  }
}

function getColor(value) {
  const colors = {
    0: "#cdc1b4",
    2: "#eee4da",
    4: "#ede0c8",
    8: "#f2b179",
    16: "#f59563",
    32: "#f67c5f",
    64: "#f65e3b",
    128: "#edcf72",
    256: "#edcc61",
    512: "#edc850",
    1024: "#edc53f",
    2048: "#edc22e",
  };
  return colors[value] || "#3c3a32";
}

function renderBoard(newTiles = [], mergedTiles = []) {
  const boardDiv = document.getElementById("board");
  boardDiv.innerHTML = "";

  board.forEach((row, r) => {
    row.forEach((value, c) => {
      const div = document.createElement("div");
      div.className = "tile";
      div.textContent = value === 0 ? "" : value;
      div.style.background = getColor(value);

      if (newTiles.some(([nr, nc]) => nr === r && nc === c)) div.classList.add("new-tile");
      if (mergedTiles.some(([mr, mc]) => mr === r && mc === c)) div.classList.add("merged");

      boardDiv.appendChild(div);
    });
  });

  document.getElementById("score").textContent = score;
}

/* --------------------------
   MOVEMENT + MERGING LOGIC
---------------------------*/

function moveLeftOnce(row, rowIndex, mergedTiles) {
  let filtered = row.filter(v => v !== 0);
  let result = [];

  for (let i = 0; i < filtered.length; i++) {
    if (filtered[i] === filtered[i + 1]) {
      const mergedValue = filtered[i] * 2;
      score += mergedValue;
      result.push(mergedValue);
      mergedTiles.push([rowIndex, result.length - 1]);
      i++;
    } else {
      result.push(filtered[i]);
    }
  }
  while (result.length < boardSize) result.push(0);
  return result;
}

function move(direction) {
  let moved = false;
  let newBoard = JSON.parse(JSON.stringify(board));
  const mergedTiles = [];
  const newTiles = [];

  const rotateClockwise = b => b[0].map((_, i) => b.map(row => row[i]).reverse());
  const rotateCounterClockwise = b =>
    b[0].map((_, i) => b.map(row => row[row.length - 1 - i]));

  if (direction === "up") {
    newBoard = rotateCounterClockwise(newBoard).map((row, i) =>
      moveLeftOnce(row, i, mergedTiles)
    );
    newBoard = rotateClockwise(newBoard);
  } else if (direction === "down") {
    newBoard = rotateClockwise(newBoard).map((row, i) =>
      moveLeftOnce(row, i, mergedTiles)
    );
    newBoard = rotateCounterClockwise(newBoard);
  } else if (direction === "left") {
    newBoard = newBoard.map((row, i) => moveLeftOnce(row, i, mergedTiles));
  } else if (direction === "right") {
    newBoard = newBoard.map(row => row.reverse());
    newBoard = newBoard.map((row, i) => moveLeftOnce(row, i, mergedTiles));
    newBoard = newBoard.map(row => row.reverse());
  }

  if (JSON.stringify(board) !== JSON.stringify(newBoard)) {
    board = newBoard;

    const beforeAdd = JSON.parse(JSON.stringify(board));
    addNewTile();
    for (let r = 0; r < boardSize; r++) {
      for (let c = 0; c < boardSize; c++) {
        if (beforeAdd[r][c] === 0 && board[r][c] !== 0) {
          newTiles.push([r, c]);
        }
      }
    }

    renderBoard(newTiles, mergedTiles);
    moved = true;
  }

  // 🔹 Trigger coach feedback after a valid move
  if (moved && aiMode === "coach") {
    requestAICoaching(direction);
  }

  if (moved && isGameOver()) {
    setTimeout(() => alert("Game Over!"), 200);
  }
}

function isGameOver() {
  for (let i = 0; i < boardSize; i++) {
    for (let j = 0; j < boardSize; j++) {
      if (board[i][j] === 0) return false;
      if (i < boardSize - 1 && board[i][j] === board[i + 1][j]) return false;
      if (j < boardSize - 1 && board[i][j] === board[i][j + 1]) return false;
    }
  }
  return true;
}

function resetGame() {
  initBoard();
}

/* --------------------------
   AI HELPERS
---------------------------*/

function getCurrentBoard() {
  return board.map(row => row.slice());
}

/* --------------------------
   MODE SWITCHING
---------------------------*/

function setMode(mode) {
  aiMode = mode;
  const insightEl = document.getElementById("ai-insight");
  insightEl.innerText = "AI Mode switched to: " + mode.toUpperCase();
}

/* --------------------------
   AI SUGGESTION MODE
---------------------------*/

async function requestAISuggestion() {
  if (aiMode !== "suggestion") return;

  const depth = parseInt(document.getElementById("ai-depth").value) || 2;
  const boardState = getCurrentBoard();

  const res = await fetch("/ai_suggest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ board: boardState, depth })
  });

  const data = await res.json();

  document.querySelector("#ai-best .move-text").textContent =
    data.best_move ? data.best_move.toUpperCase() : "-";

  const tbody = document.querySelector("#ai-scores tbody");
  tbody.innerHTML = "";

  for (const [move, score] of Object.entries(data.scores)) {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${move.toUpperCase()}</td><td>${score.toFixed(2)}</td>`;
    tbody.appendChild(row);
  }

  document.getElementById("ai-expl").textContent = data.explanation;
}

/* --------------------------
   INSIGHT-ONLY MODE
---------------------------*/

async function requestAIInsight() {
  const depth = parseInt(document.getElementById("ai-depth").value) || 2;
  const boardState = getCurrentBoard();

  const res = await fetch("/ai_insight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ board: boardState, depth })
  });

  const data = await res.json();
  const insightEl = document.getElementById("ai-insight");
  insightEl.innerText = "Insights:\n- " + data.insights.join("\n- ");
}

/* --------------------------
   COACH MODE
---------------------------*/

async function requestAICoaching(playerMove) {
  const depth = 2;

  const res = await fetch("/ai_suggest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      board: getCurrentBoard(),
      depth,
      playerMove
    })
  });

  const data = await res.json();

  // Expect backend to send something like { coach_msg: "...", best_move: "left" }
  const msg = data.coach_msg
    ? data.coach_msg
    : (data.best_move
        ? `Coach says: A better alternative could have been ${data.best_move.toUpperCase()}.`
        : "Coach says: No clearly better alternative from this position.");

  document.getElementById("ai-insight").innerText = msg;
}

/* --------------------------
   EVENT LISTENERS
---------------------------*/

document.getElementById("get-ai").addEventListener("click", () => {
  if (aiMode === "suggestion") {
    requestAISuggestion();
  } else if (aiMode === "insight") {
    requestAIInsight();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "ArrowUp") move("up");
  if (e.key === "ArrowDown") move("down");
  if (e.key === "ArrowLeft") move("left");
  if (e.key === "ArrowRight") move("right");
});

/* --------------------------
   START GAME
---------------------------*/

initBoard();
