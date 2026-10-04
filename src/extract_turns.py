"""Extract only the analysis window from authenticated Parquet copies.

Requires DuckDB installed locally in .deps (pip install --target .deps duckdb==1.3.2).
The raw model messages are deliberately omitted; action/output/error are retained.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".deps"))
import duckdb  # type: ignore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/window_turns.jsonl"))
    parser.add_argument("--require-shards", type=int, default=10)
    args = parser.parse_args()
    shards = sorted(args.raw.glob("turns-????.parquet"))
    if len(shards) != args.require_shards:
        parser.error(f"need {args.require_shards} shards, found {len(shards)}")
    con = duckdb.connect()
    paths = "[" + ",".join("'" + str(p).replace("'", "''") + "'" for p in shards) + "]"
    query = f"""
        SELECT id, session_id, created_at, agent_action, output, error,
               screenshot_is_redacted, has_redaction_been_overruled,
               filename AS source_shard
        FROM read_parquet({paths}, filename=true)
        WHERE created_at >= '2026-05-04 00:00:00'
          AND created_at < '2026-05-09 00:00:00'
        ORDER BY created_at, id
    """
    cur = con.execute(query)
    names = [x[0] for x in cur.description]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.output.open("w", encoding="utf-8") as fh:
        while batch := cur.fetchmany(500):
            for values in batch:
                record = dict(zip(names, values))
                if isinstance(record["agent_action"], str):
                    record["agent_action"] = json.loads(record["agent_action"])
                record["source_shard"] = Path(record["source_shard"]).name
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    print(json.dumps({"shards": len(shards), "window_turns_with_leadin": count,
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
