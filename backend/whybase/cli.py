"""Command-line entry points for seed, ask, arena and sentinel."""
from __future__ import annotations

import argparse
import json

from .agents.analyst import ask
from .arena import run
from .seed.load import seed
from .agents.sentinel import scan


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    ask_parser = sub.add_parser("ask")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--tenant", default="northwind")
    sub.add_parser("arena")
    sentinel = sub.add_parser("sentinel")
    sentinel.add_argument("--tenant", default="northwind")
    args = parser.parse_args()
    if args.command == "seed":
        seed()
    elif args.command == "ask":
        print(json.dumps(ask(args.tenant, args.question), indent=2))
    elif args.command == "arena":
        print(json.dumps(run(), indent=2))
    else:
        print(json.dumps(scan(args.tenant), indent=2))


if __name__ == "__main__":
    main()
