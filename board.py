"""2048 bitboard: 64-bit int, 16 nibbles, (0,0)=MSB, row0=top, col0=left."""
from __future__ import annotations

ROW_LEFT: list[int] = [0] * 65536
ROW_RIGHT: list[int] = [0] * 65536
SCORE: list[int] = [0] * 65536


def _unpack(row: int) -> list[int]:
    return [(row >> 12) & 0xF, (row >> 8) & 0xF, (row >> 4) & 0xF, row & 0xF]


def _pack(cells: list[int]) -> int:
    return ((cells[0] & 0xF) << 12) | ((cells[1] & 0xF) << 8) | ((cells[2] & 0xF) << 4) | (cells[3] & 0xF)


def _slide_left(cells: list[int]) -> tuple[list[int], int]:
    tiles = [c for c in cells if c]
    out: list[int] = []
    score = 0
    i = 0
    while i < len(tiles):
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            v = tiles[i] + 1
            out.append(v)
            score += 1 << v
            i += 2
        else:
            out.append(tiles[i])
            i += 1
    out.extend([0] * (4 - len(out)))
    return out, score


def _build_tables() -> None:
    for i in range(65536):
        cells = _unpack(i)
        left, sc = _slide_left(cells)
        ROW_LEFT[i] = _pack(left)
        SCORE[i] = sc
        right, _ = _slide_left(cells[::-1])
        ROW_RIGHT[i] = _pack(right[::-1])


_build_tables()


def _row_shift(r: int) -> int:
    return 48 - r * 16


def _get_row(board: int, r: int) -> int:
    return (board >> _row_shift(r)) & 0xFFFF


def _set_row(board: int, r: int, row: int) -> int:
    s = _row_shift(r)
    return (board & ~(0xFFFF << s)) | ((row & 0xFFFF) << s)


def get_cell(board: int, index: int) -> int:
    return (board >> (60 - index * 4)) & 0xF


def set_cell(board: int, index: int, value: int) -> int:
    s = 60 - index * 4
    return (board & ~(0xF << s)) | ((value & 0xF) << s)


def transpose(board: int) -> int:
    out = 0
    for r in range(4):
        for c in range(4):
            out = set_cell(out, c * 4 + r, get_cell(board, r * 4 + c))
    return out


def move(board: int, direction: int) -> tuple[int, int]:
    if direction in (0, 2):  # up / down via transpose
        t = transpose(board)
        nt, sc = move(t, 3 if direction == 0 else 1)
        return transpose(nt), sc
    score = 0
    new_board = 0
    for r in range(4):
        row = _get_row(board, r)
        if direction == 3:  # left
            score += SCORE[row]
            new_board = _set_row(new_board, r, ROW_LEFT[row])
        else:  # right
            rev = _pack(_unpack(row)[::-1])
            score += SCORE[rev]
            new_board = _set_row(new_board, r, ROW_RIGHT[row])
    if new_board == board:
        return board, 0
    return new_board, score


def count_empty(board: int) -> int:
    n = 0
    for i in range(16):
        if get_cell(board, i) == 0:
            n += 1
    return n


def empty_positions(board: int) -> list[int]:
    return [i for i in range(16) if get_cell(board, i) == 0]


def spawn_tile(board: int, rng) -> int:
    empties = empty_positions(board)
    if not empties:
        return board
    idx = empties[rng.randrange(len(empties))]
    val = 1 if rng.random() < 0.9 else 2
    return set_cell(board, idx, val)


def is_game_over(board: int) -> bool:
    if count_empty(board):
        return False
    for d in range(4):
        nb, _ = move(board, d)
        if nb != board:
            return False
    return True


def max_tile(board: int) -> int:
    m = 0
    for i in range(16):
        v = get_cell(board, i)
        if v:
            m = max(m, 1 << v)
    return m


def from_grid(grid: list[list[int]]) -> int:
    board = 0
    for r in range(4):
        for c in range(4):
            raw = grid[r][c]
            log = 0 if raw == 0 else raw.bit_length() - 1
            board = set_cell(board, r * 4 + c, log)
    return board


def to_grid(board: int) -> list[list[int]]:
    grid = [[0] * 4 for _ in range(4)]
    for r in range(4):
        for c in range(4):
            v = get_cell(board, r * 4 + c)
            grid[r][c] = 0 if v == 0 else (1 << v)
    return grid


def to_string(board: int) -> str:
    lines = []
    for r in range(4):
        cells = []
        for c in range(4):
            v = get_cell(board, r * 4 + c)
            cells.append(f"{'.':>6}" if v == 0 else f"{(1 << v):6d}")
        lines.append("".join(cells))
    return "\n".join(lines)


def naive_move(grid: list[list[int]], direction: int) -> tuple[list[list[int]], int]:
    """grid is 4x4 of log2 values. direction: 0=up 1=right 2=down 3=left."""
    g = [row[:] for row in grid]

    def slide_line(line: list[int]) -> tuple[list[int], int]:
        tiles = [x for x in line if x]
        out: list[int] = []
        score = 0
        i = 0
        while i < len(tiles):
            if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
                v = tiles[i] + 1
                out.append(v)
                score += 1 << v
                i += 2
            else:
                out.append(tiles[i])
                i += 1
        out.extend([0] * (4 - len(out)))
        return out, score

    score = 0
    if direction == 3:  # left
        for r in range(4):
            g[r], sc = slide_line(g[r])
            score += sc
    elif direction == 1:  # right
        for r in range(4):
            line, sc = slide_line(g[r][::-1])
            g[r] = line[::-1]
            score += sc
    elif direction == 0:  # up
        for c in range(4):
            col = [g[r][c] for r in range(4)]
            col, sc = slide_line(col)
            score += sc
            for r in range(4):
                g[r][c] = col[r]
    else:  # down
        for c in range(4):
            col = [g[r][c] for r in range(4)]
            col, sc = slide_line(col[::-1])
            col = col[::-1]
            score += sc
            for r in range(4):
                g[r][c] = col[r]
    if g == grid:
        return grid, 0
    return g, score
