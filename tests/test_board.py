import random

import pytest

from board import (
    count_empty,
    evaluate,
    from_grid,
    get_cell,
    is_game_over,
    move,
    naive_move,
    set_cell,
    to_grid,
    transpose,
)


def _pack_row_log(cells: list[int]) -> list[list[int]]:
    """Build a 4x4 log2 grid with the given first row (log2 values)."""
    return [cells[:], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]


def _board_from_log_grid(grid: list[list[int]]) -> int:
    b = 0
    for r in range(4):
        for c in range(4):
            b = set_cell(b, r * 4 + c, grid[r][c])
    return b


def _log_grid_from_board(board: int) -> list[list[int]]:
    return [[get_cell(board, r * 4 + c) for c in range(4)] for r in range(4)]


def test_merge_left_two_pairs():
    # tiles 2,2,2,2 -> log2 [1,1,1,1] left -> [2,2,0,0] score 8
    grid = _pack_row_log([1, 1, 1, 1])
    board = _board_from_log_grid(grid)
    nb, sc = move(board, 3)
    assert sc == 8
    assert _log_grid_from_board(nb)[0] == [2, 2, 0, 0]
    ng, nsc = naive_move(grid, 3)
    assert nsc == 8 and ng[0] == [2, 2, 0, 0]


def test_merge_left_partial():
    # [2,2,4,0] -> [1,1,2,0] left -> [2,2,0,0] score 4
    grid = _pack_row_log([1, 1, 2, 0])
    board = _board_from_log_grid(grid)
    nb, sc = move(board, 3)
    assert sc == 4
    assert _log_grid_from_board(nb)[0] == [2, 2, 0, 0]


def test_merge_right():
    # [4,4,2,2] -> [2,2,1,1] right -> [0,0,3,2] score 12
    grid = _pack_row_log([2, 2, 1, 1])
    board = _board_from_log_grid(grid)
    nb, sc = move(board, 1)
    assert sc == 12
    assert _log_grid_from_board(nb)[0] == [0, 0, 3, 2]


def test_merge_left_with_gap():
    # [2,0,0,2] -> [1,0,0,1] left -> [2,0,0,0] score 4
    grid = _pack_row_log([1, 0, 0, 1])
    board = _board_from_log_grid(grid)
    nb, sc = move(board, 3)
    assert sc == 4
    assert _log_grid_from_board(nb)[0] == [2, 0, 0, 0]


def test_from_grid_to_grid_roundtrip():
    rng = random.Random(1)
    for _ in range(200):
        b = 0
        for i in range(16):
            b = set_cell(b, i, rng.randrange(16))
        assert from_grid(to_grid(b)) == b


def test_transpose_involution():
    rng = random.Random(2)
    for _ in range(200):
        b = 0
        for i in range(16):
            b = set_cell(b, i, rng.randrange(16))
        assert transpose(transpose(b)) == b


def test_move_matches_naive():
    rng = random.Random(3)
    for _ in range(2000):
        b = 0
        # 0..14 so a merge stays within the 4-bit cell (max log2 15)
        for i in range(16):
            b = set_cell(b, i, rng.randrange(15))
        log_grid = _log_grid_from_board(b)
        for d in range(4):
            nb, sc = move(b, d)
            ng, nsc = naive_move(log_grid, d)
            assert sc == nsc
            assert _log_grid_from_board(nb) == ng


def test_game_over_false_with_empty():
    grid = [[2, 4, 8, 16], [32, 64, 128, 256], [512, 1024, 2048, 4096], [8192, 16384, 0, 2]]
    assert is_game_over(from_grid(grid)) is False


def test_game_over_true_no_moves():
    # no empties, no equal neighbors
    grid = [
        [2, 4, 8, 16],
        [32, 64, 128, 256],
        [512, 1024, 2048, 4096],
        [8192, 16384, 32768, 2],
    ]
    # last row has 2 at end; check neighbors - 32768 and 2 differ; col above is 4096
    # Wait 2 at (3,3) and nothing equal adjacent. (0,0)=2 and nothing else is 2 nearby...
    # (3,3)=2 only touches (2,3)=4096 and (3,2)=32768. Good.
    # But (0,0)=2 - only one 2? We have two 2s at (0,0) and (3,3) - not adjacent. OK.
    assert is_game_over(from_grid(grid)) is True


def test_game_over_false_with_merge():
    grid = [
        [2, 4, 8, 16],
        [32, 64, 128, 256],
        [512, 1024, 2048, 4096],
        [8192, 16384, 2, 2],
    ]
    assert is_game_over(from_grid(grid)) is False


def test_evaluate_deterministic():
    b = from_grid([[2, 4, 0, 0], [0, 0, 8, 0], [16, 0, 0, 2], [0, 0, 0, 0]])
    assert evaluate(b) == evaluate(b)


def test_evaluate_prefers_more_empty():
    sparse = _board_from_log_grid(
        [[1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    )
    dense = _board_from_log_grid(
        [[1, 2, 3, 4], [5, 1, 2, 3], [4, 5, 1, 2], [3, 4, 0, 0]]
    )
    assert count_empty(sparse) == 12
    assert count_empty(dense) == 2
    assert evaluate(sparse) > evaluate(dense)


def test_evaluate_prefers_monotonic_row():
    mono = _board_from_log_grid(_pack_row_log([8, 4, 2, 0]))
    scram = _board_from_log_grid(_pack_row_log([2, 8, 0, 4]))
    assert evaluate(mono) > evaluate(scram)


def test_evaluate_prefers_max_in_corner():
    corner = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    center = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    corner[0][0] = 10
    corner[0][1] = 5
    corner[1][0] = 4
    center[1][1] = 10
    center[0][1] = 5
    center[1][0] = 4
    assert evaluate(_board_from_log_grid(corner)) > evaluate(_board_from_log_grid(center))


def test_table_build_under_3_seconds():
    import importlib
    import time

    import board as board_mod

    start = time.perf_counter()
    importlib.reload(board_mod)
    assert time.perf_counter() - start < 3.0
