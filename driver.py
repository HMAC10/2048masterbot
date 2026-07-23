"""Live driver: connect expectimax solver to 2048game.online."""
from __future__ import annotations

import argparse
import statistics
import time

import solver
from board import max_tile
from browser import Game
from solver import best_move


def play_one(game: Game, max_moves: int, quiet: bool, budget_ms: int) -> dict:
    game.reset()
    score = 0
    moves = 0
    stalls = 0
    depth_sum = 0
    final_board = 0
    t0 = time.perf_counter()

    while moves < max_moves:
        state = None
        for attempt in range(3):
            state = game.read()
            if state is not None:
                break
            print(f"warning: could not read state (attempt {attempt + 1}/3)")
            time.sleep(0.1)
        if state is None:
            print("abort: state unreadable after 3 retries")
            break

        final_board = state["board"]
        score = state["score"]

        if state["won"] and not state["keepPlaying"]:
            game.dismiss_win()

        d = best_move(state["board"], budget_ms=budget_ms)
        if d == -1:
            break
        depth_sum += solver.last_depth

        game.send(d)
        if not game.wait_for_change(state["board"]):
            game.send(d)
            if not game.wait_for_change(state["board"]):
                stalls += 1
                print(f"stall at move {moves}: board did not change after retry")
                break

        moves += 1
        if not quiet and moves % 50 == 0:
            cur = game.read()
            mt = max_tile(cur["board"]) if cur else max_tile(final_board)
            sc = cur["score"] if cur else score
            avg_d = depth_sum / moves
            print(f"moves={moves} score={sc} max_tile={mt} avg_depth={avg_d:.2f}")

    elapsed = time.perf_counter() - t0
    cur = game.read()
    if cur is not None:
        score = cur["score"]
        final_board = cur["board"]
    mt = max_tile(final_board)
    mps = moves / elapsed if elapsed > 0 else 0.0
    avg_depth = depth_sum / moves if moves else 0.0
    return {
        "score": score,
        "max_tile": mt,
        "moves": moves,
        "elapsed": elapsed,
        "moves_per_sec": mps,
        "stalls": stalls,
        "avg_depth": avg_depth,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Live 2048 expectimax driver")
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--max-moves", type=int, default=5000)
    parser.add_argument("--budget-ms", type=int, default=200)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    game = None
    results = []
    try:
        game = Game(headless=args.headless)
        for i in range(args.games):
            if not args.quiet:
                print(f"=== game {i + 1}/{args.games} ===")
            r = play_one(game, args.max_moves, args.quiet, args.budget_ms)
            results.append(r)
            print(
                f"final score={r['score']} max_tile={r['max_tile']} "
                f"moves={r['moves']} elapsed={r['elapsed']:.3f} "
                f"moves_per_sec={r['moves_per_sec']:.2f} stalls={r['stalls']} "
                f"avg_depth={r['avg_depth']:.2f}"
            )
    except KeyboardInterrupt:
        print("interrupted")
    finally:
        if game is not None:
            game.close()

    if not results:
        return

    scores = [r["score"] for r in results]
    max_tiles = [r["max_tile"] for r in results]
    dist: dict[int, int] = {}
    for t in max_tiles:
        dist[t] = dist.get(t, 0) + 1
    n = len(results)
    print("=== SUMMARY ===")
    print(f"games played: {n}")
    print("max tile distribution:")
    for tile in sorted(dist.keys(), reverse=True):
        count = dist[tile]
        print(f"  {tile}: {count} ({100.0 * count / n:.1f}%)")
    print(f"median score: {statistics.median(scores):.1f}")
    print(f"best score: {max(scores)}")
    avg_depths = [r["avg_depth"] for r in results]
    print(f"average depth reached: {statistics.mean(avg_depths):.2f}")


if __name__ == "__main__":
    main()
