"""Profile 40 best_move calls on a mid-game board (depth forced to 2)."""
from __future__ import annotations

import cProfile
import pstats
import random
from io import StringIO

import solver
from board import is_game_over, move, spawn_tile
from solver import best_move

solver.DEPTH_SHALLOW = 2
solver.DEPTH_MID = 2
solver.DEPTH_DEEP = 2

rng = random.Random(1)
board = 0
board = spawn_tile(board, rng)
board = spawn_tile(board, rng)

for _ in range(150):
    d = best_move(board)
    if d == -1:
        break
    board, _ = move(board, d)
    board = spawn_tile(board, rng)
    if is_game_over(board):
        break

profiler = cProfile.Profile()
profiler.enable()
for _ in range(40):
    best_move(board)
profiler.disable()

buf = StringIO()
stats = pstats.Stats(profiler, stream=buf)
print("=== TOP 15 BY CUMULATIVE TIME ===")
stats.sort_stats("cumulative").print_stats(15)
print(buf.getvalue())

buf = StringIO()
stats = pstats.Stats(profiler, stream=buf)
print("=== TOP 15 BY TOTAL TIME (tottime) ===")
stats.sort_stats("tottime").print_stats(15)
print(buf.getvalue())
