"""Local stand-in for a forge CLI: appends an issue record to issues.jsonl."""

import argparse
import json
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("title")
parser.add_argument("body", nargs="?", default="")
parser.add_argument("--label", action="append", default=[])
args = parser.parse_args()
queue = pathlib.Path(__file__).resolve().parent.parent / "issues.jsonl"
with queue.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({"title": args.title, "body": args.body, "labels": args.label}) + "\n")
print("queued locally")
