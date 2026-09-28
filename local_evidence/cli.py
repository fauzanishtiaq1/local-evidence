"""JSON CLI for the local-evidence offline retrieval engine."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import core


class UserError(Exception):
    """Invalid command-line or user data."""


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="local-evidence", description="Build and query a local citation index.")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="index UTF-8 text files")
    b.add_argument("source_dir", metavar="SOURCE_DIR")
    b.add_argument("index_dir", metavar="INDEX_DIR")
    b.add_argument("--extensions", nargs="+", default=[".md", ".txt", ".rst"])
    b.add_argument("--chunk-lines", type=int, default=40)
    b.add_argument("--overlap-lines", type=int, default=5)
    s = sub.add_parser("search", help="search an index")
    s.add_argument("index_dir", metavar="INDEX_DIR")
    s.add_argument("query", metavar="QUERY")
    s.add_argument("--top-k", type=int, default=5)
    s.add_argument("--min-score", type=float, default=0.0)
    i = sub.add_parser("inspect", help="read an indexed source span")
    i.add_argument("index_dir", metavar="INDEX_DIR")
    i.add_argument("path", metavar="PATH")
    i.add_argument("--start-line", required=True, type=int)
    i.add_argument("--end-line", required=True, type=int)
    t = sub.add_parser("stats", help="show index statistics")
    t.add_argument("index_dir", metavar="INDEX_DIR")
    return p


def _json(value: Any) -> None:
    try:
        text = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"result is not valid JSON: {exc}") from exc
    sys.stdout.write(text + "\n")


def _run(args: argparse.Namespace) -> Any:
    if args.command == "build":
        if any(not isinstance(x, str) or not x.startswith(".") for x in args.extensions):
            raise UserError("extensions must start with '.'")
        return core.build_index(args.source_dir, args.index_dir, extensions=args.extensions,
                                chunk_lines=args.chunk_lines, overlap_lines=args.overlap_lines)
    if args.command == "search":
        return core.search_index(args.index_dir, args.query, top_k=args.top_k, min_score=args.min_score)
    if args.command == "inspect":
        return core.inspect_document(args.index_dir, args.path, start_line=args.start_line, end_line=args.end_line)
    return core.index_stats(args.index_dir)


def main(argv: list[str] | None = None) -> int:
    # Windows console defaults can be a legacy code page; JSON must remain UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    try:
        args = _parser().parse_args(argv)
        _json(_run(args))
        return 0
    except core.SourceChangedError as exc:
        print(f"source changed or unavailable: {exc}; rebuild the index", file=sys.stderr)
        return 1
    except core.InvalidIndexError as exc:
        print(f"invalid index: {exc}; rebuild the index", file=sys.stderr)
        return 1
    except (UserError, ValueError, TypeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # defensive process boundary
        print(f"internal error: {exc}", file=sys.stderr)
        return 1
