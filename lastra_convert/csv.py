"""CSV ↔ Lastra conversions.

CSV path uses ``pandas`` for parsing (delimiter sniffing + null handling) and
delegates to the Parquet path's row-by-row encoder via an Arrow table to keep
the type-detection logic in one place.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pyarrow as pa
from lastra import DataType

from ._types import DEFAULT_CODEC, infer_csv_value_type, parse_columns_arg
from .parquet import (
    _arrow_column_to_lastra_payload,
    lastra_file_to_arrow_table,
)
from lastra import LastraWriter


def csv_to_lastra(
    csv_path: str | Path,
    lastra_path: str | Path,
    *,
    columns: str | None = None,
) -> int:
    """Encode CSV rows to a Lastra file.

    Delimiter is sniffed from the first 4KB (comma, tab, semicolon, pipe).
    Per-column types: integer if every non-empty cell parses as ``int``,
    double if every non-empty cell parses as ``float``, binary otherwise.
    Override with ``--columns`` (CLI) / ``columns=`` (API).

    Returns the row count written.
    """
    delim = _sniff_delimiter(Path(csv_path))
    df = pd.read_csv(csv_path, sep=delim, dtype=str, keep_default_na=False)
    overrides: dict[str, tuple[DataType, object]] = {}
    if columns:
        for name, dtype, codec in parse_columns_arg(columns):
            overrides[name] = (dtype, codec)

    writer = LastraWriter()
    column_data: list[object] = []

    for name in df.columns:
        cells = df[name].tolist()
        if name in overrides:
            dtype, codec = overrides[name]
        else:
            dtype = infer_csv_value_type(cells[: min(len(cells), 256)])
            codec = DEFAULT_CODEC[dtype]
        writer.add_series_column(name, dtype, codec)
        column_data.append(_csv_cells_to_payload(cells, dtype))

    writer.write_series(len(df), *column_data)
    with open(lastra_path, "wb") as out:
        writer.write_to(out)
    return len(df)


def lastra_to_csv(
    lastra_path: str | Path,
    csv_path: str | Path,
    *,
    delimiter: str = ",",
) -> int:
    """Decode the series side of a Lastra file into a CSV. BINARY columns are
    UTF-8-decoded if possible, hex-encoded otherwise. Returns the row count.
    """
    table = lastra_file_to_arrow_table(lastra_path)
    df = table.to_pandas()
    # Force binary columns to a printable form. pyarrow.binary() materialises
    # to ``bytes`` which pandas can't stringify cleanly without help.
    for name in df.columns:
        if df[name].dtype == object:
            df[name] = df[name].map(_bytes_to_csv_str)
    df.to_csv(csv_path, index=False, sep=delimiter)
    return len(df)


# ---------------------------------------------------------------------------


def _sniff_delimiter(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        sample = f.read(4096)
    if not sample:
        return ","
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        return ","


def _csv_cells_to_payload(cells: list[str], dtype: DataType):
    if dtype == DataType.LONG:
        # Empty cells map to 0 — Lastra has no row-level nulls in numeric series.
        return _np_int64([int(c) if c not in (None, "") else 0 for c in cells])
    if dtype == DataType.DOUBLE:
        return _np_float64([float(c) if c not in (None, "") else 0.0 for c in cells])
    return [c.encode("utf-8") if c not in (None, "") else None for c in cells]


def _np_int64(xs):
    import numpy as np

    return np.asarray(xs, dtype=np.int64)


def _np_float64(xs):
    import numpy as np

    return np.asarray(xs, dtype=np.float64)


def _bytes_to_csv_str(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8")
        except UnicodeDecodeError:
            return "0x" + v.hex()
    return str(v)


# Silence "unused import" while keeping the side-effect of importing pa for
# its side benefits in callers (e.g. type hints downstream).
_ = pa
