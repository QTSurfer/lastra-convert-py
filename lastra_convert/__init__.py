"""Lastra ↔ Parquet/CSV/Arrow converter — Python port of QTSurfer/lastra-convert.

Public API::

    from lastra_convert import (
        parquet_to_lastra, lastra_to_parquet,
        csv_to_lastra,     lastra_to_csv,
        arrow_to_lastra,   lastra_to_arrow,
    )

CLI entry points (see ``pyproject.toml``)::

    parquet2lastra  /  lastra2parquet
    csv2lastra      /  lastra2csv
    arrow2lastra    /  lastra2arrow
"""

from .arrow import arrow_to_lastra, lastra_to_arrow
from .csv import csv_to_lastra, lastra_to_csv
from .parquet import lastra_to_parquet, parquet_to_lastra

__version__ = "1.0.0"

__all__ = [
    "parquet_to_lastra",
    "lastra_to_parquet",
    "csv_to_lastra",
    "lastra_to_csv",
    "arrow_to_lastra",
    "lastra_to_arrow",
    "__version__",
]
