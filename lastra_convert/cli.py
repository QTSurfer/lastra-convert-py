"""CLI entry points. Six commands, one per direction:

- ``parquet2lastra`` / ``lastra2parquet``
- ``csv2lastra``     / ``lastra2csv``
- ``arrow2lastra``   / ``lastra2arrow``

Each accepts ``input output`` plus a small flag set. Run any of them with
``-h`` for the full options list.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from .arrow import arrow_to_lastra, lastra_to_arrow
from .csv import csv_to_lastra, lastra_to_csv
from .parquet import lastra_to_parquet, parquet_to_lastra


def _columns_help() -> str:
    return (
        "Optional column overrides as NAME:TYPE:CODEC,... — types: "
        "long|double|binary; codecs: raw|delta_varint|alp|varlen|varlen_zstd|"
        "varlen_gzip|gorilla|pongo. When omitted, every column auto-detects "
        "to its closest type with the project default codec."
    )


def _build_parser(prog: str, *, has_columns: bool, has_compression: bool) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=prog, allow_abbrev=False)
    p.add_argument("input", help="path to the input file")
    p.add_argument("output", help="path to the output file")
    if has_columns:
        p.add_argument("--columns", default=None, help=_columns_help())
    if has_compression:
        p.add_argument(
            "--compression",
            default="zstd",
            help="parquet compression (default: zstd; also: snappy, gzip, none)",
        )
    return p


def _emit(prog: str, rows: int, output: str) -> None:
    print(f"{prog}: wrote {rows} rows → {output}")


def _run(
    fn: Callable[..., int],
    prog: str,
    argv: list[str] | None,
    *,
    has_columns: bool = False,
    has_compression: bool = False,
) -> int:
    parser = _build_parser(prog, has_columns=has_columns, has_compression=has_compression)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    kwargs: dict[str, object] = {}
    if has_columns:
        kwargs["columns"] = args.columns
    if has_compression:
        kwargs["compression"] = args.compression
    rows = fn(args.input, args.output, **kwargs)
    _emit(prog, rows, args.output)
    return 0


# ---------------------------------------------------------------------------
# Entry points wired through pyproject.toml ``[project.scripts]``.
# ---------------------------------------------------------------------------


def parquet2lastra(argv: list[str] | None = None) -> int:
    return _run(parquet_to_lastra, "parquet2lastra", argv, has_columns=True)


def lastra2parquet(argv: list[str] | None = None) -> int:
    return _run(lastra_to_parquet, "lastra2parquet", argv, has_compression=True)


def csv2lastra(argv: list[str] | None = None) -> int:
    return _run(csv_to_lastra, "csv2lastra", argv, has_columns=True)


def lastra2csv(argv: list[str] | None = None) -> int:
    return _run(lastra_to_csv, "lastra2csv", argv)


def arrow2lastra(argv: list[str] | None = None) -> int:
    return _run(arrow_to_lastra, "arrow2lastra", argv, has_columns=True)


def lastra2arrow(argv: list[str] | None = None) -> int:
    return _run(lastra_to_arrow, "lastra2arrow", argv)
