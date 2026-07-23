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

W_EMPTY = 270.0
W_MERGES = 700.0
W_SUM = 11.0
W_MONO = 47.0
P_SUM = 3.5
P_MONO = 4.0
BASE = 200000.0

HEUR: list[float] = [0.0] * 65536


def _heur_for_line(line: list[int]) -> float:
    h = BASE
    h += W_EMPTY * sum(1 for rank in line if rank == 0)

    counter = 0
    merges = 0
    prev = 0
    for rank in line:
        if rank != 0:
            if prev == rank:
                counter += 1
            elif counter > 0:
                merges += 1 + counter
                counter = 0
            prev = rank
    if counter > 0:
        merges += 1 + counter
    h += W_MERGES * merges

    # 0 ** P_SUM is 0.0; empty cells add nothing to SUM
    h -= W_SUM * sum(rank ** P_SUM for rank in line)

    mono_left = 0.0
    mono_right = 0.0
    for i in range(1, 4):
        a = line[i - 1] ** P_MONO
        b = line[i] ** P_MONO
        if line[i - 1] > line[i]:
            mono_left += a - b
        else:
            mono_right += b - a
    h -= W_MONO * min(mono_left, mono_right)
    return h


def _build_heur() -> None:
    for i in range(65536):
        HEUR[i] = _heur_for_line(_unpack(i))


_build_heur()


def evaluate(board: int) -> float:
    heur = HEUR
    total = 0.0
    total += heur[(board >> 48) & 0xFFFF]
    total += heur[(board >> 32) & 0xFFFF]
    total += heur[(board >> 16) & 0xFFFF]
    total += heur[board & 0xFFFF]
    t = transpose(board)
    total += heur[(t >> 48) & 0xFFFF]
    total += heur[(t >> 32) & 0xFFFF]
    total += heur[(t >> 16) & 0xFFFF]
    total += heur[t & 0xFFFF]
    return total


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
    # Bit-parallel nibble transpose for layout (r,c) at bit 60-(r*16+c*4).
    a1 = board & 0xF0F00F0FF0F00F0F
    a2 = board & 0x0000F0F00000F0F0
    a3 = board & 0x0F0F00000F0F0000
    a = a1 | (a2 << 12) | (a3 >> 12)
    b1 = a & 0xFF00FF0000FF00FF
    b2 = a & 0x00FF00FF00000000
    b3 = a & 0x00000000FF00FF00
    return b1 | (b2 >> 24) | (b3 << 24)


def move(board: int, direction: int) -> tuple[int, int]:
    if direction in (0, 2):  # up / down via transpose
        t = transpose(board)
        nt, sc = move(t, 3 if direction == 0 else 1)
        return transpose(nt), sc
    score = 0
    new_board = 0
    rl = ROW_LEFT
    rr = ROW_RIGHT
    sc_t = SCORE
    pack = _pack
    unpack = _unpack
    if direction == 3:  # left
        for s in (48, 32, 16, 0):
            row = (board >> s) & 0xFFFF
            score += sc_t[row]
            new_board |= rl[row] << s
    else:  # right
        for s in (48, 32, 16, 0):
            row = (board >> s) & 0xFFFF
            rev = pack(unpack(row)[::-1])
            score += sc_t[rev]
            new_board |= rr[row] << s
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
