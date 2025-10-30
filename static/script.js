const boardSize = 4;
let board = [];
let score = 0;

function initBoard() {
  board = Array.from({ length: boardSize }, () => Array(boardSize).fill(0));
  score = 0;
  addNewTile();
  addNewTile();
  renderBoard();
}

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

function renderBoard(newTiles = [], mergedTiles = []) {
  const boardDiv = document.getElementById("board");
  boardDiv.innerHTML = "";

  board.forEach((row, r) => {
    row.forEach((value, c) => {
      const div = document.createElement("div");
      div.className = "tile";
      div.textContent = value === 0 ? "" : value;
      div.style.background = getColor(value);

      // Apply animation for new or merged tiles
      if (newTiles.some(([nr, nc]) => nr === r && nc === c)) {
        div.classList.add("new-tile");
      }
      if (mergedTiles.some(([mr, mc]) => mr === r && mc === c)) {
        div.classList.add("merged");
      }

      boardDiv.appendChild(div);
    });
  });

  document.getElementById("score").textContent = score;
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

function moveLeft(row) {
  let filtered = row.filter(v => v !== 0);
  for (let i = 0; i < filtered.length - 1; i++) {
    if (filtered[i] === filtered[i + 1]) {
      filtered[i] *= 2;
      score += filtered[i];
      filtered[i + 1] = 0;
    }
  }
  filtered = filtered.filter(v => v !== 0);
  while (filtered.length < boardSize) filtered.push(0);
  return filtered;
}

function rotateBoard(b) {
  return b[0].map((_, i) => b.map(row => row[i]));
}
function move(direction) {
  let moved = false;
  let newBoard = JSON.parse(JSON.stringify(board)); // deep copy
  const mergedTiles = [];
  const newTiles = [];

  const moveLeftOnce = (row, rowIndex) => {
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
  };

  const rotateClockwise = (b) => b[0].map((_, i) => b.map(row => row[i]).reverse());
  const rotateCounterClockwise = (b) =>
    b[0].map((_, i) => b.map(row => row[row.length - 1 - i]));

  if (direction === "up") {
    newBoard = rotateCounterClockwise(newBoard);
    newBoard = newBoard.map((row, i) => moveLeftOnce(row, i));
    newBoard = rotateClockwise(newBoard);
  } else if (direction === "down") {
    newBoard = rotateClockwise(newBoard);
    newBoard = newBoard.map((row, i) => moveLeftOnce(row, i));
    newBoard = rotateCounterClockwise(newBoard);
  } else if (direction === "left") {
    newBoard = newBoard.map((row, i) => moveLeftOnce(row, i));
  } else if (direction === "right") {
    newBoard = newBoard.map(row => row.reverse());
    newBoard = newBoard.map((row, i) => moveLeftOnce(row, i));
    newBoard = newBoard.map(row => row.reverse());
  }

  if (JSON.stringify(board) !== JSON.stringify(newBoard)) {
    board = newBoard;

    // Track where new tile is added
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

// Keyboard controls
document.addEventListener("keydown", (e) => {
  switch (e.key) {
    case "ArrowUp":
      move("up");
      break;
    case "ArrowDown":
      move("down");
      break;
    case "ArrowLeft":
      move("left");
      break;
    case "ArrowRight":
      move("right");
      break;
  }
});

initBoard();
