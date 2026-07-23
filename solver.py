"""Expectimax solver for the 2048 bitboard. Imports board.py only."""
from __future__ import annotations

from board import (
    count_empty,
    empty_positions,
    evaluate,
    move,
    set_cell,
)

PROB_CUTOFF = 0.0001
DEPTH_SHALLOW = 3
DEPTH_MID = 4
DEPTH_DEEP = 5

_tt: dict[tuple[int, int], float] = {}


def _max_node(board: int, depth: int, cprob: float) -> float:
    best = None
    for d in range(4):
        new_board, _ = move(board, d)
        if new_board == board:
            continue
        v = _chance_node(new_board, depth, cprob)
        if best is None or v > best:
            best = v
    return 0.0 if best is None else best


def _chance_node(board: int, depth: int, cprob: float) -> float:
    key = (board, depth)
    if key in _tt:
        return _tt[key]

    if depth == 0 or cprob < PROB_CUTOFF:
        val = evaluate(board)
        _tt[key] = val
        return val

    cells = empty_positions(board)
    if not cells:
        val = evaluate(board)
        _tt[key] = val
        return val

    n = len(cells)
    total = 0.0
    for cell in cells:
        for rank, p in ((1, 0.9), (2, 0.1)):
            child = set_cell(board, cell, rank)
            total += p * _max_node(child, depth - 1, cprob * p / n)
    val = total / n
    _tt[key] = val
    return val


def best_move(board: int) -> int:
    global _tt
    _tt = {}

    empties = count_empty(board)
    if empties >= 8:
        depth = DEPTH_SHALLOW
    elif empties >= 4:
        depth = DEPTH_MID
    else:
        depth = DEPTH_DEEP

    best_d = -1
    best_v = None
    for d in range(4):
        new_board, _ = move(board, d)
        if new_board == board:
            continue
        v = _chance_node(new_board, depth, 1.0)
        if best_v is None or v > best_v:
            best_v = v
            best_d = d
    return best_d
