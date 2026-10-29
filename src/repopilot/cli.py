from __future__ import annotations

import argparse
import ipaddress
import json
import os

import uvicorn

from repopilot.indexer import index_repository
from repopilot.store import Store


def main() -> None:
    parser = argparse.ArgumentParser(prog="repopilot", description="Local-first repository intelligence.")
    sub = parser.add_subparsers(dest="command", required=True)
    index_parser = sub.add_parser("index", help="Index a local repository")
    index_parser.add_argument("path")
    search_parser = sub.add_parser("search", help="Search an indexed repository")
    search_parser.add_argument("repository_id")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)
    sub.add_parser("repos", help="List indexed repositories")
    serve_parser = sub.add_parser("serve", help="Run the API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    store = Store()
    if args.command == "index":
        print(json.dumps(store.index(index_repository(args.path, store.file_hashes(args.path))), indent=2))
    elif args.command == "search":
        print(json.dumps(store.search(args.repository_id, args.query, args.limit), indent=2))
    elif args.command == "repos":
        print(json.dumps(store.list_repositories(), indent=2))
    elif args.command == "serve":
        try:
            loopback = args.host.lower() == "localhost" or ipaddress.ip_address(args.host).is_loopback
        except ValueError:
            loopback = False
        if not loopback and not os.getenv("REP_PILOT_API_TOKEN", "").strip():
            parser.error(
                "refusing non-loopback bind without REP_PILOT_API_TOKEN; "
                "set a strong token or use --host 127.0.0.1"
            )
        uvicorn.run("repopilot.api:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
