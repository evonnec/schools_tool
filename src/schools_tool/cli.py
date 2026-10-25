"""Command line: `schools-tool counts` and `schools-tool search`."""

import argparse
import sys
from pathlib import Path

from schools_tool.count_schools import print_counts, write_counts
from schools_tool.dataset import SCHOOL_DATA_CSV, load_schools, load_state_names
from schools_tool.school_search import RESULT_LIMIT, SchoolIndex, search_schools


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {number}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schools-tool",
        description="Count and search the NCES 2005-06 public school dataset.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=SCHOOL_DATA_CSV,
        help="school CSV in the NCES layout (default: the bundled 2005-06 file)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    counts = commands.add_parser("counts", help="print the Part 1 counts")
    counts.add_argument(
        "--output-dir", type=Path, help="also write the counts as CSV files here"
    )

    search = commands.add_parser(
        "search", help="search schools by name, city, and state"
    )
    search.add_argument(
        "query",
        nargs="*",
        help="search text; omit it to read one query per line from stdin",
    )
    search.add_argument("--limit", type=positive_int, default=RESULT_LIMIT)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        schools = load_schools(args.data)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.command == "counts":
        print_counts(schools)
        if args.output_dir:
            for path in write_counts(schools, args.output_dir):
                print(f"Wrote {path}", file=sys.stderr)
        return 0

    index = SchoolIndex(schools, load_state_names())
    if args.query:
        search_schools(" ".join(args.query), index=index, limit=args.limit)
        return 0
    for line in sys.stdin:
        if line.strip():
            search_schools(line.strip(), index=index, limit=args.limit)
    return 0
