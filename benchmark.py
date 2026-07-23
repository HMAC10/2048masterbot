"""Offline expectimax game benchmark. No browser."""
from __future__ import annotations

import argparse
import random
import statistics
import time

import solver
from board import is_game_over, max_tile, move, spawn_tile
from solver import best_move


def play_one_game(seed: int, budget_ms: int) -> dict:
    rng = random.Random(seed)
    board = 0
    board = spawn_tile(board, rng)
    board = spawn_tile(board, rng)
    score = 0
    moves = 0
    depth_sum = 0
    t0 = time.perf_counter()
    while True:
        d = best_move(board, budget_ms=budget_ms)
        if d == -1:
            break
        depth_sum += solver.last_depth
        board, gained = move(board, d)
        score += gained
        moves += 1
        board = spawn_tile(board, rng)
        if is_game_over(board):
            break
    elapsed = time.perf_counter() - t0
    return {
        "seed": seed,
        "score": score,
        "max_tile": max_tile(board),
        "moves": moves,
        "elapsed_seconds": elapsed,
        "avg_depth": depth_sum / moves if moves else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline 2048 expectimax benchmark")
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--budget-ms", type=int, default=200)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    results = []
    for i in range(args.games):
        r = play_one_game(args.seed + i, args.budget_ms)
        results.append(r)
        if not args.quiet:
            mps = r["moves"] / r["elapsed_seconds"] if r["elapsed_seconds"] > 0 else 0.0
            print(
                f"seed={r['seed']} score={r['score']} max_tile={r['max_tile']} "
                f"moves={r['moves']} seconds={r['elapsed_seconds']:.3f} "
                f"moves_per_sec={mps:.2f} avg_depth={r['avg_depth']:.2f}"
            )

    scores = [r["score"] for r in results]
    max_tiles = [r["max_tile"] for r in results]
    total_moves = sum(r["moves"] for r in results)
    total_time = sum(r["elapsed_seconds"] for r in results)

    dist: dict[int, int] = {}
    for t in max_tiles:
        dist[t] = dist.get(t, 0) + 1
    n = len(results)
    reach_2048 = sum(1 for t in max_tiles if t >= 2048)

    print("=== SUMMARY ===")
    print(f"games played: {n}")
    print("max tile distribution:")
    for tile in sorted(dist.keys(), reverse=True):
        count = dist[tile]
        pct = 100.0 * count / n
        print(f"  {tile}: {count} ({pct:.1f}%)")
    print(f"pct reaching 2048+: {100.0 * reach_2048 / n:.1f}%")
    print(f"median score: {statistics.median(scores):.1f}")
    print(f"mean score: {statistics.mean(scores):.1f}")
    print(f"best score: {max(scores)}")
    print(f"total moves: {total_moves}")
    overall_mps = total_moves / total_time if total_time > 0 else 0.0
    print(f"overall moves per second: {overall_mps:.2f}")
    # average depth across all moves (move-weighted)
    if total_moves:
        weighted = sum(r["avg_depth"] * r["moves"] for r in results) / total_moves
    else:
        weighted = 0.0
    print(f"average depth reached: {weighted:.2f}")


if __name__ == "__main__":
    main()
