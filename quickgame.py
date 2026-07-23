"""One offline game with search depth forced to 2. Does not edit solver.py."""
from __future__ import annotations

import random
import time

import solver
from board import is_game_over, max_tile, move, spawn_tile
from solver import best_move

solver.DEPTH_SHALLOW = 2
solver.DEPTH_MID = 2
solver.DEPTH_DEEP = 2

rng = random.Random(0)
board = 0
board = spawn_tile(board, rng)
board = spawn_tile(board, rng)
score = 0
moves = 0
t0 = time.perf_counter()

while True:
    d = best_move(board)
    if d == -1:
        break
    board, gained = move(board, d)
    score += gained
    moves += 1
    board = spawn_tile(board, rng)
    if moves % 100 == 0:
        print(f"moves={moves} score={score} max_tile={max_tile(board)}")
    if is_game_over(board):
        break

elapsed = time.perf_counter() - t0
mps = moves / elapsed if elapsed > 0 else 0.0
print(f"final score={score}")
print(f"max tile={max_tile(board)}")
print(f"total moves={moves}")
print(f"elapsed seconds={elapsed:.3f}")
print(f"moves per second={mps:.2f}")
