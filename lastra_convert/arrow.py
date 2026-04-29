"""Arrow ↔ Lastra conversions.

Arrow side is the IPC ("Feather v2") file format — same byte stream
``pyarrow.ipc`` writes/reads. Lastra side reuses the helpers from ``parquet``
since the encoding step takes a generic ``pyarrow.Table``.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow.ipc as ipc

from .parquet import _encode_table_to_lastra, lastra_file_to_arrow_table


def arrow_to_lastra(
    arrow_path: str | Path,
    lastra_path: str | Path,
    *,
    columns: str | None = None,
) -> int:
    """Encode an Arrow IPC file's columns to Lastra series. Returns the row
    count written.
    """
    with open(arrow_path, "rb") as src:
        table = ipc.RecordBatchFileReader(src).read_all()
    return _encode_table_to_lastra(table, Path(lastra_path), columns_arg=columns)


def lastra_to_arrow(
    lastra_path: str | Path,
    arrow_path: str | Path,
) -> int:
    """Decode a Lastra file's series columns into an Arrow IPC file. Returns
    the row count written.
    """
    table = lastra_file_to_arrow_table(lastra_path)
    with open(arrow_path, "wb") as out:
        with ipc.RecordBatchFileWriter(out, table.schema) as writer:
            writer.write_table(table)
    return table.num_rows


