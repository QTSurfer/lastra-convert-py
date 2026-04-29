"""Helpers for mapping foreign type systems (Arrow/Parquet/CSV) to Lastra
DataType + Codec. Default codec choices mirror the Java reference impl
(``ParquetToLastraConverter`` auto-detect path):

- ``LONG``   → ``DELTA_VARINT``
- ``DOUBLE`` → ``ALP``
- ``BINARY`` → ``VARLEN_ZSTD``
"""

from __future__ import annotations

from collections.abc import Iterable

from lastra import Codec, DataType

DEFAULT_CODEC: dict[DataType, Codec] = {
    DataType.LONG: Codec.DELTA_VARINT,
    DataType.DOUBLE: Codec.ALP,
    DataType.BINARY: Codec.VARLEN_ZSTD,
}


def parse_columns_arg(spec: str) -> list[tuple[str, DataType, Codec]]:
    """Parse the CLI ``--columns`` flag, format ``NAME:TYPE:CODEC,...``.

    Example::

        ts:long:delta_varint,close:double:alp,vol:double:pongo

    Raises ``ValueError`` on any malformed entry.
    """
    out: list[tuple[str, DataType, Codec]] = []
    for raw in (s.strip() for s in spec.split(",") if s.strip()):
        parts = raw.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"invalid column spec '{raw}', expected NAME:TYPE:CODEC"
            )
        name, type_s, codec_s = (p.strip() for p in parts)
        try:
            dtype = DataType[type_s.upper()]
        except KeyError as e:
            raise ValueError(
                f"unknown DataType '{type_s}' in '{raw}' "
                f"(valid: {[d.name.lower() for d in DataType]})"
            ) from e
        try:
            codec = Codec[codec_s.upper()]
        except KeyError as e:
            raise ValueError(
                f"unknown Codec '{codec_s}' in '{raw}' "
                f"(valid: {[c.name.lower() for c in Codec]})"
            ) from e
        out.append((name, dtype, codec))
    return out


def detect_arrow(arrow_type: object) -> DataType:
    """Map a ``pyarrow.DataType`` (or anything quack-like with ``id``/``str``)
    to the closest Lastra ``DataType``. Falls back to ``BINARY`` for anything
    not numeric — caller can downgrade further (e.g. for booleans).
    """
    s = str(arrow_type).lower()
    if s in {"int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64"}:
        return DataType.LONG
    if s in {"float", "float16", "float32", "float64", "double", "halffloat"}:
        return DataType.DOUBLE
    if "timestamp" in s or "duration" in s or "date" in s or "time" in s:
        # All time-ish types serialize through their underlying int64 via pyarrow.
        return DataType.LONG
    if "bool" in s:
        # Lastra has no boolean primitive — keep the int64 storage path.
        return DataType.LONG
    return DataType.BINARY


def detect_default_codec(dtype: DataType) -> Codec:
    return DEFAULT_CODEC[dtype]


def infer_csv_value_type(samples: Iterable[str]) -> DataType:
    """Pick a Lastra ``DataType`` from a handful of CSV string samples.

    Strategy: integer wins if every non-empty sample parses as ``int``; double
    wins if every non-empty sample parses as ``float`` (after the integer test
    failed); otherwise BINARY.
    """
    seen_any = False
    int_ok = True
    float_ok = True
    for s in samples:
        if s is None or s == "":
            continue
        seen_any = True
        if int_ok:
            try:
                int(s)
            except ValueError:
                int_ok = False
        if float_ok:
            try:
                float(s)
            except ValueError:
                float_ok = False
        if not int_ok and not float_ok:
            break
    if not seen_any:
        return DataType.BINARY
    if int_ok:
        return DataType.LONG
    if float_ok:
        return DataType.DOUBLE
    return DataType.BINARY
