import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ALLOWED_KEYS = {"script_id", "market", "phone_line_condition", "hazard_class", "turns"}
TURN_KEYS = {"speaker", "text", "escalation_label", "intent_label"}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def normalized(script):
    text = " ".join(turn["text"] for turn in script["turns"]).lower()
    text = re.sub(r"l4-\d+|07700 900\d{3}|flat \d+|\b\d+\b", "#", text)
    return re.sub(r"\s+", " ", text).strip()


def scan(shards):
    counts = Counter()
    ids = set()
    exact = set()
    normalized_texts = set()
    schema_errors = []
    pii_hits = []
    rows = []
    total = 0
    for shard in shards:
        shard_count = 0
        shard_markets = Counter()
        with gzip.open(shard, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                total += 1
                shard_count += 1
                script = json.loads(line)
                if set(script) != ALLOWED_KEYS or not script["turns"] or any(set(turn) != TURN_KEYS for turn in script["turns"]):
                    schema_errors.append(f"{shard.name}:{line_number}")
                script_id = script["script_id"]
                text = " ".join(turn["text"] for turn in script["turns"])
                ids.add(script_id)
                exact.add(text)
                normalized_texts.add(normalized(script))
                market = script["market"]
                shard_markets[market] += 1
                counts[f"market:{market}"] += 1
                counts[f"condition:{script['phone_line_condition']}"] += 1
                counts[f"hazard:{script['hazard_class']}"] += 1
                for phone in re.findall(r"0\d[\d ]{8,12}", text):
                    if not phone.replace(" ", "").startswith(("07700900", "0800111999")):
                        pii_hits.append(f"{script_id}:phone:{phone}")
                if re.search(r"\b(?!TE\d \dZZ\b)[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}\b", text):
                    pii_hits.append(f"{script_id}:postcode")
        rows.append({"shard": str(shard.relative_to(shard.parents[1])), "count": shard_count, "market": dict(shard_markets), "sha256": digest(shard)})
    return {"total": total, "counts": counts, "unique_ids": len(ids), "unique_exact": len(exact), "unique_normalized": len(normalized_texts), "schema_errors": schema_errors, "pii_hits": pii_hits, "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    shards = sorted(args.shards.glob("*.jsonl.gz"))
    result = scan(shards)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for row in result["rows"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    with (args.output / "MANIFEST.sha256").open("w", encoding="utf-8") as handle:
        for row in result["rows"]:
            handle.write(f"{row['sha256']}  {row['shard']}\n")
    near_duplicate_rate = 1 - result["unique_normalized"] / result["total"]
    lines = ["# QA", "", f"- Total scripts: {result['total']}", f"- Schema valid: {result['total'] - len(result['schema_errors'])}/{result['total']}", f"- Unique IDs: {result['unique_ids']}", f"- Exact unique texts: {result['unique_exact']}", f"- Normalized unique texts: {result['unique_normalized']}", f"- Near-duplicate rate after masking variable fictional details: {near_duplicate_rate:.4%}", f"- PII-pattern scan hits: {len(result['pii_hits'])}", "", "## Counts"]
    lines.extend(f"- {key}: {value}" for key, value in sorted(result["counts"].items()))
    (args.output / "QA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if result["total"] != 50000 or result["unique_ids"] != 50000 or result["unique_exact"] < 49000 or result["schema_errors"] or result["pii_hits"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
