"""Test C: Alternative weighting of the Index.

The composite Index is defined as (forbid × take) / 10. This test recomputes
rankings under alternative weightings to check how robust the top-10 is:
- Sum: (forbid + take) / 2
- Product without liquidated damages (drop AS5 from forbid)
- Forbid-only ranking
- Take-only ranking
- Product-of-normalized: (forbid/10 * take/10) * 10
"""
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(parents=True, exist_ok=True)


def load_scores():
    rows = []
    with open(DATA / "scores.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = {
                "company": r["company"],
                "domain": r["domain"],
                "forbid_score": float(r["forbid_score"]),
                "take_score": float(r["take_score"]),
                "hypocrisy_index": float(r["hypocrisy_index"]),
                # anti-scraping components
                "forbid_AS1": float(r["forbid_AS1"] or 0),
                "forbid_AS2": float(r["forbid_AS2"] or 0),
                "forbid_AS3": float(r["forbid_AS3"] or 0),
                "forbid_AS4": float(r["forbid_AS4"] or 0),
                "forbid_AS5": float(r["forbid_AS5"] or 0),
                "forbid_AS6": float(r["forbid_AS6"] or 0),
                "forbid_AS7": float(r["forbid_AS7"] or 0),
            }
            rows.append(row)
    return rows


def rank_by(rows, key):
    sorted_rows = sorted(rows, key=lambda r: -r[key])
    return [(i + 1, r) for i, r in enumerate(sorted_rows)]


def main():
    rows = load_scores()

    # Compute alt scores per row
    for r in rows:
        # 1. Sum (equal-weight)
        r["alt_sum"] = (r["forbid_score"] + r["take_score"]) / 2
        # 2. Product without AS5 (liquidated damages removed)
        forbid_no_as5 = r["forbid_score"] - r["forbid_AS5"]
        forbid_no_as5 = max(0, forbid_no_as5)
        r["alt_no_as5"] = (forbid_no_as5 * r["take_score"]) / 10
        # 3. Forbid-only
        r["alt_forbid_only"] = r["forbid_score"]
        # 4. Take-only
        r["alt_take_only"] = r["take_score"]

    # Baseline rank
    baseline = {r["company"]: i + 1 for i, r in enumerate(sorted(rows, key=lambda r: -r["hypocrisy_index"]))}

    def rank_map(key):
        return {r["company"]: i + 1 for i, r in enumerate(sorted(rows, key=lambda r: -r[key]))}

    ranks_by_scheme = {
        "baseline (product)": baseline,
        "equal-weight sum": rank_map("alt_sum"),
        "no liquidated damages": rank_map("alt_no_as5"),
        "forbid-only": rank_map("alt_forbid_only"),
        "take-only": rank_map("alt_take_only"),
    }

    # Print top-10 under each scheme
    print("=" * 100)
    print("Top-10 under each scoring scheme")
    print("=" * 100)
    schemes = [
        ("baseline (product)", "hypocrisy_index"),
        ("equal-weight sum", "alt_sum"),
        ("no liquidated damages", "alt_no_as5"),
        ("forbid-only", "alt_forbid_only"),
        ("take-only", "alt_take_only"),
    ]
    for label, key in schemes:
        top = sorted(rows, key=lambda r: -r[key])[:10]
        print(f"\n### {label}")
        for i, r in enumerate(top, 1):
            b = baseline[r["company"]]
            delta = b - i
            arrow = f"(+{delta})" if delta > 0 else (f"({delta})" if delta < 0 else "")
            print(f"  {i:2}. {r['company']:20}  score={r[key]:.2f}  vs baseline #{b:2}  {arrow}")

    # Cross-scheme robustness: who's in top-5 across all schemes?
    top5_by_scheme = {label: [r["company"] for r in sorted(rows, key=lambda x: -x[key])[:5]] for label, key in schemes}
    all_top5 = set.intersection(*[set(v) for v in top5_by_scheme.values()])
    top10_by_scheme = {label: [r["company"] for r in sorted(rows, key=lambda x: -x[key])[:10]] for label, key in schemes}
    all_top10 = set.intersection(*[set(v) for v in top10_by_scheme.values()])

    print("\n" + "=" * 100)
    print("ROBUSTNESS")
    print("=" * 100)
    print(f"In top-5 under ALL 5 schemes: {sorted(all_top5)}")
    print(f"In top-10 under ALL 5 schemes: {sorted(all_top10)}")

    result = {
        "n_companies": len(rows),
        "schemes": [label for label, _ in schemes],
        "top10_by_scheme": {label: [{"rank": i + 1, "company": r["company"], "score": round(r[key], 3), "baseline_rank": baseline[r["company"]]} for i, r in enumerate(sorted(rows, key=lambda x: -x[key])[:10])] for label, key in schemes},
        "robust_top5_all_schemes": sorted(all_top5),
        "robust_top10_all_schemes": sorted(all_top10),
    }
    (OUT / "test_c_alt_weights.json").write_text(json.dumps(result, indent=2))
    print(f"\nSaved: {OUT / 'test_c_alt_weights.json'}")


if __name__ == "__main__":
    main()
