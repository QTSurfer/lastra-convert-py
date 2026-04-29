"""Roundtrip + helper tests for the six conversion entry points.

Each direction goes through the public API (``lastra_convert.*``); the CLI
wrappers in ``cli.py`` get a separate smoke pass below.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc
import pyarrow.parquet as pq
import pytest
from lastra import Codec, DataType, LastraReader

from lastra_convert import (
    arrow_to_lastra,
    csv_to_lastra,
    lastra_to_arrow,
    lastra_to_csv,
    lastra_to_parquet,
    parquet_to_lastra,
)
from lastra_convert._types import infer_csv_value_type, parse_columns_arg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_table() -> pa.Table:
    return pa.table(
        {
            "ts": pa.array(np.arange(1_700_000_000, 1_700_000_064, dtype=np.int64)),
            "close": pa.array(np.linspace(100.0, 100.063, 64, dtype=np.float64)),
            "volume": pa.array(np.linspace(1.0, 64.0, 64, dtype=np.float64)),
        }
    )


# ---------------------------------------------------------------------------
# Parquet ↔ Lastra
# ---------------------------------------------------------------------------


def test_parquet_to_lastra_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "in.parquet"
    lastra = tmp_path / "out.lastra"
    pq.write_table(_sample_table(), src)

    rows = parquet_to_lastra(src, lastra)
    assert rows == 64

    with open(lastra, "rb") as f:
        reader = LastraReader.from_stream(f)
    cols = {c.name: c for c in reader.series_columns}
    assert cols["ts"].data_type == DataType.LONG
    assert cols["ts"].codec == Codec.DELTA_VARINT
    assert cols["close"].data_type == DataType.DOUBLE
    assert cols["close"].codec == Codec.ALP

    ts = reader.read_series_long("ts")
    np.testing.assert_array_equal(ts, np.arange(1_700_000_000, 1_700_000_064))
    np.testing.assert_allclose(reader.read_series_double("close"), np.linspace(100.0, 100.063, 64))


def test_lastra_to_parquet_roundtrip(tmp_path: Path) -> None:
    lastra = tmp_path / "in.lastra"
    parquet = tmp_path / "out.parquet"
    table = _sample_table()
    pq.write_table(table, tmp_path / "src.parquet")
    parquet_to_lastra(tmp_path / "src.parquet", lastra)

    rows = lastra_to_parquet(lastra, parquet)
    assert rows == 64
    back = pq.read_table(parquet)
    assert back.num_rows == 64
    assert back.column_names == ["ts", "close", "volume"]
    np.testing.assert_array_equal(back.column("ts").to_numpy(), table.column("ts").to_numpy())
    np.testing.assert_allclose(
        back.column("close").to_numpy(),
        table.column("close").to_numpy(),
    )


def test_parquet_to_lastra_columns_override(tmp_path: Path) -> None:
    src = tmp_path / "in.parquet"
    lastra = tmp_path / "out.lastra"
    pq.write_table(_sample_table(), src)

    parquet_to_lastra(src, lastra, columns="ts:long:delta_varint,close:double:pongo")
    with open(lastra, "rb") as f:
        reader = LastraReader.from_stream(f)
    cols = {c.name: c for c in reader.series_columns}
    assert cols["close"].codec == Codec.PONGO
    # Unmentioned columns still auto-detect.
    assert cols["volume"].codec == Codec.ALP


# ---------------------------------------------------------------------------
# CSV ↔ Lastra
# ---------------------------------------------------------------------------


def test_csv_to_lastra_autodetects_types(tmp_path: Path) -> None:
    csv_path = tmp_path / "in.csv"
    lastra = tmp_path / "out.lastra"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "close", "tag"])
        for i in range(10):
            w.writerow([1_700_000_000 + i, 100.0 + i * 0.1, f"r{i}"])

    rows = csv_to_lastra(csv_path, lastra)
    assert rows == 10

    with open(lastra, "rb") as f:
        reader = LastraReader.from_stream(f)
    cols = {c.name: c for c in reader.series_columns}
    assert cols["ts"].data_type == DataType.LONG
    assert cols["close"].data_type == DataType.DOUBLE
    assert cols["tag"].data_type == DataType.BINARY


def test_csv_to_lastra_then_back(tmp_path: Path) -> None:
    csv_in = tmp_path / "in.csv"
    lastra = tmp_path / "mid.lastra"
    csv_out = tmp_path / "out.csv"
    rows = [["ts", "close"], ["1", "1.5"], ["2", "2.5"], ["3", "3.5"]]
    with open(csv_in, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    csv_to_lastra(csv_in, lastra)
    lastra_to_csv(lastra, csv_out)

    with open(csv_out) as f:
        out = list(csv.reader(f))
    assert out[0] == ["ts", "close"]
    # Numeric round-trip — values match (formatting may differ slightly for floats).
    assert [r[0] for r in out[1:]] == ["1", "2", "3"]
    assert [float(r[1]) for r in out[1:]] == [1.5, 2.5, 3.5]


def test_csv_sniffs_tab_delimiter(tmp_path: Path) -> None:
    csv_path = tmp_path / "in.tsv"
    lastra = tmp_path / "out.lastra"
    with open(csv_path, "w", newline="") as f:
        f.write("a\tb\n1\t2\n3\t4\n5\t6\n")

    csv_to_lastra(csv_path, lastra)
    with open(lastra, "rb") as f:
        reader = LastraReader.from_stream(f)
    assert reader.series_row_count == 3
    assert {c.name for c in reader.series_columns} == {"a", "b"}


# ---------------------------------------------------------------------------
# Arrow ↔ Lastra
# ---------------------------------------------------------------------------


def test_arrow_to_lastra_roundtrip(tmp_path: Path) -> None:
    src = tmp_path / "in.arrow"
    lastra = tmp_path / "out.lastra"
    table = _sample_table()
    with open(src, "wb") as f:
        with ipc.RecordBatchFileWriter(f, table.schema) as w:
            w.write_table(table)

    rows = arrow_to_lastra(src, lastra)
    assert rows == 64
    with open(lastra, "rb") as f:
        reader = LastraReader.from_stream(f)
    np.testing.assert_array_equal(reader.read_series_long("ts"), table.column("ts").to_numpy())


def test_lastra_to_arrow_roundtrip(tmp_path: Path) -> None:
    lastra = tmp_path / "in.lastra"
    arrow = tmp_path / "out.arrow"
    table = _sample_table()
    pq.write_table(table, tmp_path / "src.parquet")
    parquet_to_lastra(tmp_path / "src.parquet", lastra)

    rows = lastra_to_arrow(lastra, arrow)
    assert rows == 64
    with open(arrow, "rb") as f:
        back = ipc.RecordBatchFileReader(f).read_all()
    assert back.num_rows == 64
    assert back.column_names == ["ts", "close", "volume"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_parse_columns_arg() -> None:
    out = parse_columns_arg("ts:long:delta_varint,close:double:alp")
    assert out == [
        ("ts", DataType.LONG, Codec.DELTA_VARINT),
        ("close", DataType.DOUBLE, Codec.ALP),
    ]


def test_parse_columns_arg_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_columns_arg("just-a-name")
    with pytest.raises(ValueError):
        parse_columns_arg("ts:wat:delta_varint")
    with pytest.raises(ValueError):
        parse_columns_arg("ts:long:no_such_codec")


def test_infer_csv_value_type() -> None:
    assert infer_csv_value_type(["1", "2", "3"]) == DataType.LONG
    assert infer_csv_value_type(["1.5", "2", "3"]) == DataType.DOUBLE
    assert infer_csv_value_type(["x", "1", "2"]) == DataType.BINARY
    assert infer_csv_value_type([]) == DataType.BINARY
    assert infer_csv_value_type(["", "", ""]) == DataType.BINARY


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


def test_cli_parquet2lastra(tmp_path: Path) -> None:
    from lastra_convert.cli import parquet2lastra as cli

    src = tmp_path / "in.parquet"
    lastra = tmp_path / "out.lastra"
    pq.write_table(_sample_table(), src)
    rc = cli([str(src), str(lastra)])
    assert rc == 0
    assert lastra.stat().st_size > 0


def test_cli_lastra2parquet(tmp_path: Path) -> None:
    from lastra_convert.cli import lastra2parquet as cli

    src = tmp_path / "src.parquet"
    lastra = tmp_path / "mid.lastra"
    out = tmp_path / "out.parquet"
    pq.write_table(_sample_table(), src)
    parquet_to_lastra(src, lastra)
    rc = cli([str(lastra), str(out), "--compression", "snappy"])
    assert rc == 0
    assert out.stat().st_size > 0
