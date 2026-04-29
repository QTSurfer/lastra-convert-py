"""Parquet ↔ Lastra conversions.

The Lastra side uses ``LastraReader``/``LastraWriter`` from ``lastra-py``;
the Parquet side uses ``pyarrow.parquet`` for schema + row-group I/O.
Round-trip is value-lossless for LONG/DOUBLE; BINARY columns survive as
opaque bytes (no charset assumed).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from lastra import Codec, DataType, LastraReader, LastraWriter

from ._types import DEFAULT_CODEC, detect_arrow, parse_columns_arg


def parquet_to_lastra(
    parquet_path: str | Path,
    lastra_path: str | Path,
    *,
    columns: str | None = None,
) -> int:
    """Encode every column in ``parquet_path`` to Lastra series columns.

    ``columns``: optional CLI-style override
    (``"ts:long:delta_varint,close:double:alp"``). When omitted, every Parquet
    column is auto-detected to its closest Lastra ``DataType`` with the
    project-default codec (``DELTA_VARINT`` for LONG, ``ALP`` for DOUBLE,
    ``VARLEN_ZSTD`` for BINARY).

    Returns the row count written.
    """
    table: pa.Table = pq.read_table(str(parquet_path))
    return _encode_table_to_lastra(table, Path(lastra_path), columns_arg=columns)


def lastra_to_parquet(
    lastra_path: str | Path,
    parquet_path: str | Path,
    *,
    compression: str = "zstd",
) -> int:
    """Decode the series side of ``lastra_path`` into a Parquet file. Event
    columns (used by Lastra for sparse / bursty rows) are not emitted —
    Parquet has no native equivalent of that distinction. Returns the row
    count written.
    """
    table = lastra_file_to_arrow_table(lastra_path)
    pq.write_table(table, str(parquet_path), compression=compression)
    return table.num_rows


# ---------------------------------------------------------------------------
# Shared building blocks (reused by csv.py and arrow.py).
# ---------------------------------------------------------------------------


def _encode_table_to_lastra(
    table: pa.Table,
    lastra_path: Path,
    *,
    columns_arg: str | None,
) -> int:
    overrides: dict[str, tuple[DataType, Codec]] = {}
    if columns_arg:
        for name, dtype, codec in parse_columns_arg(columns_arg):
            overrides[name] = (dtype, codec)

    writer = LastraWriter()
    column_data: list[np.ndarray | list[bytes | None]] = []

    for field in table.schema:
        col = table.column(field.name)
        if field.name in overrides:
            dtype, codec = overrides[field.name]
        else:
            dtype = detect_arrow(field.type)
            codec = DEFAULT_CODEC[dtype]
        writer.add_series_column(field.name, dtype, codec)
        column_data.append(_arrow_column_to_lastra_payload(col, dtype))

    writer.write_series(table.num_rows, *column_data)
    with open(lastra_path, "wb") as out:
        writer.write_to(out)
    return table.num_rows


def lastra_file_to_arrow_table(lastra_path: str | Path) -> pa.Table:
    """Read every series column out of ``lastra_path`` into an Arrow table."""
    with open(lastra_path, "rb") as src:
        reader = LastraReader.from_stream(src)

    arrays: list[pa.Array] = []
    names: list[str] = []
    for col in reader.series_columns:
        names.append(col.name)
        if col.data_type == DataType.LONG:
            arrays.append(pa.array(reader.read_series_long(col.name)))
        elif col.data_type == DataType.DOUBLE:
            arrays.append(pa.array(reader.read_series_double(col.name)))
        else:
            arrays.append(pa.array(reader.read_series_binary(col.name)))
    return pa.table(arrays, names=names)


def _arrow_column_to_lastra_payload(
    col: pa.ChunkedArray,
    dtype: DataType,
) -> np.ndarray | list[bytes | None]:
    """Materialise a chunked Arrow column as the array shape Lastra's writer
    expects: ``np.int64`` for LONG, ``np.float64`` for DOUBLE, list[bytes|None]
    for BINARY.
    """
    if dtype == DataType.LONG:
        return col.combine_chunks().cast(pa.int64()).to_numpy(zero_copy_only=False)
    if dtype == DataType.DOUBLE:
        return col.combine_chunks().cast(pa.float64()).to_numpy(zero_copy_only=False)
    # BINARY — return list of bytes/None (Lastra writer accepts this).
    out: list[bytes | None] = []
    for v in col.combine_chunks().to_pylist():
        if v is None:
            out.append(None)
        elif isinstance(v, bytes):
            out.append(v)
        elif isinstance(v, str):
            out.append(v.encode("utf-8"))
        else:
            out.append(str(v).encode("utf-8"))
    return out
