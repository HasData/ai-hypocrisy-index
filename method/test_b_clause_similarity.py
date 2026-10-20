"""Test B: Clause language similarity.

Do companies copy each other's anti-scraping boilerplate? Compute pairwise
text similarity across all anti-scraping quotes and find pairs / clusters
with unusually similar phrasing.

Method: TF-IDF character n-grams + cosine similarity (no external deps beyond stdlib).
"""
import csv
import json
import re
from collections import defaultdict
from math import sqrt
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

ANTI_SCRAPING_PREFIX = ("AS1_", "AS2_", "AS3_", "AS4_", "AS5_", "AS6_", "AS7_")


def normalize(s):
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def char_ngrams(s, n=4):
    s = normalize(s)
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def tfidf_vectors(docs, n=4):
    """Return list of {ngram: tfidf} dicts."""
    ngram_lists = [char_ngrams(d, n) for d in docs]
    df = defaultdict(int)
    for ngrams in ngram_lists:
        for g in set(ngrams):
            df[g] += 1
    N = len(docs)
    from math import log
    idf = {g: log((N + 1) / (df[g] + 1)) + 1 for g in df}

    vectors = []
    for ngrams in ngram_lists:
        tf = defaultdict(int)
        for g in ngrams:
            tf[g] += 1
        vec = {g: tf[g] * idf[g] for g in tf}
        # L2 normalize
        norm = sqrt(sum(v * v for v in vec.values())) or 1
        vec = {g: v / norm for g, v in vec.items()}
        vectors.append(vec)
    return vectors


def cosine(a, b):
    # Both are L2-normalized, so cosine = dot product
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0) for k, v in a.items())


def main():
    # Load all anti-scraping verified quotes from evidence.csv (Tier A + Tier B)
    clauses = []
    with open(DATA / "evidence.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["clause_type"].startswith(ANTI_SCRAPING_PREFIX):
                q = r["verbatim_quote"].strip()
                if len(q) >= 20:
                    clauses.append({
                        "company": r["company"],
                        "domain": r["domain"],
                        "clause_type": r["clause_type"].split("_")[0],
                        "quote": q,
                    })

    print(f"Loaded {len(clauses)} anti-scraping quotes across {len({c['company'] for c in clauses})} companies")

    quotes = [c["quote"] for c in clauses]
    vecs = tfidf_vectors(quotes, n=4)

    # Compute pairwise similarity
    pairs = []
    for i in range(len(clauses)):
        for j in range(i + 1, len(clauses)):
            if clauses[i]["company"] == clauses[j]["company"]:
                continue
            sim = cosine(vecs[i], vecs[j])
            if sim >= 0.30:
                pairs.append((sim, i, j))
    pairs.sort(reverse=True)

    print(f"\nHigh-similarity cross-company pairs (>=0.30 cosine): {len(pairs)}")
    print("=" * 90)
    print(f"{'Sim':>5}  {'Company A':<20} {'Clause':<5}  {'Company B':<20} {'Clause':<5}")
    print("-" * 90)
    for sim, i, j in pairs[:40]:
        a, b = clauses[i], clauses[j]
        print(f"{sim:.3f}  {a['company']:<20} {a['clause_type']:<5}  {b['company']:<20} {b['clause_type']:<5}")

    # Cluster: connected components at sim>=0.35
    threshold = 0.35
    parent = list(range(len(clauses)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for sim, i, j in pairs:
        if sim >= threshold:
            union(i, j)

    clusters = defaultdict(list)
    for i, c in enumerate(clauses):
        clusters[find(i)].append(i)

    non_trivial = {r: idxs for r, idxs in clusters.items() if len({clauses[i]["company"] for i in idxs}) > 1}
    print(f"\n\nClusters at sim>=0.35 with 2+ distinct companies: {len(non_trivial)}")
    print("=" * 90)
    for root, idxs in sorted(non_trivial.items(), key=lambda x: -len(x[1])):
        companies = {clauses[i]["company"] for i in idxs}
        types = {clauses[i]["clause_type"] for i in idxs}
        print(f"\n### Cluster ({len(idxs)} quotes, {len(companies)} companies)")
        print(f"  Clause types: {sorted(types)}")
        print(f"  Companies: {sorted(companies)}")
        # Show up to 3 example quotes
        seen = set()
        shown = 0
        for i in idxs:
            if clauses[i]["company"] in seen:
                continue
            seen.add(clauses[i]["company"])
            q = clauses[i]["quote"][:180].replace("\n", " ")
            print(f'    {clauses[i]["company"]:20} [{clauses[i]["clause_type"]}]  "{q}"')
            shown += 1
            if shown >= 4:
                break

    result = {
        "n_clauses": len(clauses),
        "n_companies_with_anti_scraping": len({c["company"] for c in clauses}),
        "high_sim_pairs": [
            {
                "sim": round(sim, 3),
                "company_a": clauses[i]["company"],
                "clause_type_a": clauses[i]["clause_type"],
                "quote_a": clauses[i]["quote"],
                "company_b": clauses[j]["company"],
                "clause_type_b": clauses[j]["clause_type"],
                "quote_b": clauses[j]["quote"],
            }
            for sim, i, j in pairs[:50]
        ],
        "clusters_at_035": [
            {
                "n_quotes": len(idxs),
                "companies": sorted({clauses[i]["company"] for i in idxs}),
                "clause_types": sorted({clauses[i]["clause_type"] for i in idxs}),
                "example_quotes": [{"company": clauses[i]["company"], "quote": clauses[i]["quote"][:200]} for i in idxs[:5]],
            }
            for idxs in sorted(non_trivial.values(), key=lambda x: -len(x))
        ],
    }
    (OUT / "test_b_clause_similarity.json").write_text(json.dumps(result, indent=2))
    print(f"\nSaved: {OUT / 'test_b_clause_similarity.json'}")


if __name__ == "__main__":
    main()
