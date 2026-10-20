"""Test A: Robots.txt-vs-Terms consistency.

Are declared Terms clauses aligned with actual robots.txt blocking?
- Paper-only forbidders: strong anti-scraping Terms, zero AI bots blocked in robots.txt
- Silent enforcers: no Terms clauses, but blocks AI bots in robots.txt
- Aligned strict: both high
- Aligned lax: both low
"""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(parents=True, exist_ok=True)


def load_scores():
    rows = []
    with open(DATA / "scores.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "company": r["company"],
                "domain": r["domain"],
                "forbid_score": float(r["forbid_score"]),
                "take_score": float(r["take_score"]),
                "hypocrisy_index": float(r["hypocrisy_index"]),
            })
    return rows


def load_robots_blocks():
    """Return {domain: n_ai_bots_blocked} for Tier-A companies."""
    m = {}
    with open(DATA / "robots_matrix.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[r["domain"]] = int(r.get("blocks_ai_training_bots_count") or 0)
    return m


def main():
    scores = load_scores()
    robots = load_robots_blocks()

    # Join
    joined = []
    for s in scores:
        joined.append({
            **s,
            "n_ai_blocked": robots.get(s["domain"], 0),
        })

    # Buckets by median forbid_score (2.5) and any robots block (>=1)
    forbid_high = 2.5  # threshold: median-ish; 2.5 is where score jumps meaningfully
    robots_high = 1    # blocks at least 1 AI training crawler

    paper_only, silent, aligned_strict, aligned_lax = [], [], [], []
    for r in joined:
        f = r["forbid_score"] >= forbid_high
        b = r["n_ai_blocked"] >= robots_high
        if f and not b:
            paper_only.append(r)
        elif not f and b:
            silent.append(r)
        elif f and b:
            aligned_strict.append(r)
        else:
            aligned_lax.append(r)

    print("=" * 70)
    print(f"Test A: Robots.txt vs Terms consistency ({len(joined)} companies)")
    print("=" * 70)
    print(f"Threshold: forbid_score >= {forbid_high}, robots blocks >= {robots_high}")
    print()

    def show(label, rows):
        print(f"### {label}  ({len(rows)})")
        for r in sorted(rows, key=lambda x: -x["forbid_score"]):
            print(f"  {r['company']:20} forbid={r['forbid_score']:.1f}  robots={r['n_ai_blocked']:2}  index={r['hypocrisy_index']:.2f}")
        print()

    show("PAPER-ONLY FORBIDDERS (Terms strict, robots.txt permissive)", paper_only)
    show("SILENT ENFORCERS (Terms permissive, robots.txt blocks)", silent)
    show("ALIGNED STRICT (both block)", aligned_strict)
    show("ALIGNED LAX (both permissive)", aligned_lax)

    # Save
    import json
    result = {
        "n_companies": len(joined),
        "thresholds": {"forbid_score": forbid_high, "robots_blocks": robots_high},
        "paper_only": [{"company": r["company"], "domain": r["domain"], "forbid_score": r["forbid_score"], "n_ai_blocked": r["n_ai_blocked"], "hypocrisy_index": r["hypocrisy_index"]} for r in paper_only],
        "silent_enforcers": [{"company": r["company"], "domain": r["domain"], "forbid_score": r["forbid_score"], "n_ai_blocked": r["n_ai_blocked"], "hypocrisy_index": r["hypocrisy_index"]} for r in silent],
        "aligned_strict": [{"company": r["company"], "domain": r["domain"], "forbid_score": r["forbid_score"], "n_ai_blocked": r["n_ai_blocked"], "hypocrisy_index": r["hypocrisy_index"]} for r in aligned_strict],
        "aligned_lax": [{"company": r["company"], "domain": r["domain"], "forbid_score": r["forbid_score"], "n_ai_blocked": r["n_ai_blocked"], "hypocrisy_index": r["hypocrisy_index"]} for r in aligned_lax],
    }
    (OUT / "test_a_robots_vs_terms.json").write_text(json.dumps(result, indent=2))
    print(f"Saved: {OUT / 'test_a_robots_vs_terms.json'}")


if __name__ == "__main__":
    main()
