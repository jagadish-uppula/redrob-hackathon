#!/usr/bin/env python3
"""
Redrob Candidate Ranker — Main Entry Point

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv
    python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv
    python rank.py  # Uses default paths

This script:
1. Reads the candidate pool (JSONL or gzipped JSONL)
2. Extracts features for each candidate
3. Scores and ranks all candidates
4. Selects the top 100
5. Generates reasoning for each
6. Writes the submission CSV

Constraints satisfied:
- CPU only, no GPU
- No external API calls
- < 5 minutes runtime on 100K candidates
- < 16 GB RAM
- Pure Python stdlib (no ML frameworks)
"""

import argparse
import csv
import gzip
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.features import extract_features
from src.scorer import compute_score
from src.reasoning import generate_reasoning


def load_candidates(filepath: str) -> list:
    """Load candidates from JSONL or gzipped JSONL file.

    Supports both .jsonl and .jsonl.gz formats.
    """
    filepath = Path(filepath)
    candidates = []

    if filepath.suffix == ".gz" or str(filepath).endswith(".jsonl.gz"):
        opener = gzip.open
        mode = "rt"
    else:
        opener = open
        mode = "r"

    print(f"Loading candidates from {filepath}...")
    with opener(filepath, mode, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
                candidates.append(candidate)
            except json.JSONDecodeError as e:
                print(f"  WARNING: Skipping line {line_num}: {e}", file=sys.stderr)

            if line_num % 10000 == 0:
                print(f"  Loaded {line_num} candidates...")

    print(f"  Total loaded: {len(candidates)} candidates")
    return candidates


def rank_candidates(candidates: list, top_n: int = 100) -> list:
    """Score, rank, and select top N candidates.

    Returns a list of (candidate, features, score_result, rank) tuples
    sorted by final score descending.
    """
    print(f"\nScoring {len(candidates)} candidates...")
    scored = []
    t0 = time.time()

    for i, candidate in enumerate(candidates):
        # Extract features
        features = extract_features(candidate)

        # Compute score
        score_result = compute_score(candidate, features)

        scored.append((candidate, features, score_result))

        if (i + 1) % 10000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            remaining = (len(candidates) - i - 1) / rate
            print(
                f"  Scored {i+1}/{len(candidates)} "
                f"({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)"
            )

    elapsed = time.time() - t0
    print(f"  Scoring complete in {elapsed:.1f}s")

    # Sort by final score descending
    scored.sort(key=lambda x: x[2]["final_score"], reverse=True)

    # Select top N and assign ranks
    top_candidates = []
    for rank, (candidate, features, score_result) in enumerate(scored[:top_n], 1):
        top_candidates.append((candidate, features, score_result, rank))

    return top_candidates


def write_submission(
    ranked: list,
    output_path: str,
    verbose: bool = False,
) -> None:
    """Write the submission CSV.

    Format: candidate_id, rank, score, reasoning
    """
    print(f"\nGenerating reasoning and writing to {output_path}...")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for candidate, features, score_result, rank in ranked:
            cid = candidate["candidate_id"]
            score = score_result["final_score"]
            reasoning = generate_reasoning(candidate, features, score_result, rank)

            # Ensure score is non-increasing (should already be sorted)
            writer.writerow([cid, rank, f"{score:.4f}", reasoning])

            if verbose or rank <= 10:
                profile = candidate["profile"]
                print(
                    f"  Rank {rank:3d}: {cid} | "
                    f"{profile['current_title']:35s} | "
                    f"{profile['years_of_experience']:5.1f}y | "
                    f"Score: {score:.4f} | "
                    f"{profile.get('country', 'N/A')}"
                )

    print(f"  Written {len(ranked)} rows to {output_path}")


def print_diagnostics(ranked: list) -> None:
    """Print diagnostic information about the ranking."""
    print("\n" + "=" * 70)
    print("RANKING DIAGNOSTICS")
    print("=" * 70)

    # Title distribution in top 100
    from collections import Counter
    titles = Counter()
    countries = Counter()
    penalties_count = 0

    for candidate, features, score_result, rank in ranked:
        title = candidate["profile"]["current_title"]
        country = candidate["profile"]["country"]
        titles[title] += 1
        countries[country] += 1
        if score_result.get("penalties"):
            penalties_count += 1

    print("\nTitle distribution in top 100:")
    for title, count in titles.most_common():
        print(f"  {title}: {count}")

    print(f"\nCountry distribution in top 100:")
    for country, count in countries.most_common():
        print(f"  {country}: {count}")

    # Score range
    scores = [sr["final_score"] for _, _, sr, _ in ranked]
    print(f"\nScore range: {min(scores):.4f} — {max(scores):.4f}")
    print(f"Candidates with penalties: {penalties_count}")

    # Check for non-tech titles (should be zero or very low)
    non_tech = ["HR Manager", "Accountant", "Marketing Manager", "Operations Manager",
                "Sales Executive", "Content Writer", "Graphic Designer",
                "Civil Engineer", "Mechanical Engineer", "Customer Support"]
    trap_count = sum(titles.get(t, 0) for t in non_tech)
    print(f"\nNon-tech titles in top 100: {trap_count} (should be 0)")
    if trap_count > 0:
        print("  WARNING: Non-tech candidates in top 100 — review scoring!")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Redrob Candidate Ranker — ranks candidates for a job description"
    )
    parser.add_argument(
        "--candidates",
        default="candidates.jsonl",
        help="Path to candidates JSONL file (default: candidates.jsonl)",
    )
    parser.add_argument(
        "--out",
        default="submission.csv",
        help="Output CSV path (default: submission.csv)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="Number of top candidates to rank (default: 100)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print all ranked candidates (not just top 10)",
    )
    args = parser.parse_args()

    # Check input file exists
    if not Path(args.candidates).exists():
        # Try .gz version
        gz_path = args.candidates + ".gz"
        if Path(gz_path).exists():
            args.candidates = gz_path
        else:
            print(f"ERROR: Cannot find {args.candidates} or {gz_path}")
            sys.exit(1)

    total_start = time.time()

    # Load
    candidates = load_candidates(args.candidates)

    # Rank
    ranked = rank_candidates(candidates, top_n=args.top_n)

    # Write
    write_submission(ranked, args.out, verbose=args.verbose)

    # Diagnostics
    print_diagnostics(ranked)

    total_elapsed = time.time() - total_start
    print(f"\nTotal time: {total_elapsed:.1f}s")
    if total_elapsed > 300:
        print("WARNING: Exceeded 5-minute time limit!")
    else:
        print(f"Within time budget ({total_elapsed:.0f}s / 300s)")


if __name__ == "__main__":
    main()
