<p align="center">
  <img src="https://raw.githubusercontent.com/QTSurfer/lastra-convert-py/main/logo.svg" alt="Lastra" width="420">
</p>

<p align="center">
  <a href="https://github.com/QTSurfer/lastra-convert-py/actions/workflows/ci.yml"><img src="https://github.com/QTSurfer/lastra-convert-py/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/lastra-convert/"><img src="https://img.shields.io/pypi/v/lastra-convert" alt="PyPI"></a>
  <a href="https://github.com/QTSurfer/lastra-convert-py/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
</p>

<p align="center">
  Python CLI to convert between <a href="https://github.com/QTSurfer/lastra-py">Lastra</a> and Parquet / CSV / Arrow.<br>
  Mirror of the Java <a href="https://github.com/QTSurfer/lastra-convert">lastra-convert</a> tool.
</p>

---

## Install

```bash
pip install lastra-convert
```

## CLI

Six commands, one per direction. Each takes `input output` plus a small flag set; run any with `-h` for the full list.

```bash
# Parquet ↔ Lastra
parquet2lastra ticks.parquet ticks.lastra
parquet2lastra ticks.parquet ticks.lastra --columns "ts:long:delta_varint,close:double:pongo"
lastra2parquet ticks.lastra  ticks.parquet --compression zstd

# CSV ↔ Lastra (delimiter auto-detected: comma / tab / semicolon / pipe)
csv2lastra     ticks.csv     ticks.lastra
lastra2csv     ticks.lastra  ticks.csv

# Arrow IPC ↔ Lastra
arrow2lastra   ticks.arrow   ticks.lastra
lastra2arrow   ticks.lastra  ticks.arrow
```

Type / codec auto-detection (override with `--columns`):

| Source type             | Lastra DataType | Default codec |
|-------------------------|-----------------|---------------|
| int8…int64 / uint*      | LONG            | DELTA_VARINT  |
| float32 / float64       | DOUBLE          | ALP           |
| timestamp / date / bool | LONG            | DELTA_VARINT  |
| binary / string / other | BINARY          | VARLEN_ZSTD   |

CSV column types are inferred per-column from up to the first 256 cells:
integer if every non-empty cell parses as `int`; double if every non-empty
cell parses as `float`; binary otherwise.

## Library API

```python
from lastra_convert import (
    parquet_to_lastra, lastra_to_parquet,
    csv_to_lastra,     lastra_to_csv,
    arrow_to_lastra,   lastra_to_arrow,
)

# Auto-detect every column's type + default codec.
parquet_to_lastra("ticks.parquet", "ticks.lastra")

# Per-column override.
parquet_to_lastra(
    "ticks.parquet", "ticks.lastra",
    columns="ts:long:delta_varint,close:double:pongo",
)

# Decode every series column back into a Parquet (ZSTD by default).
lastra_to_parquet("ticks.lastra", "ticks.parquet", compression="zstd")
```

Each function returns the row count written.

## Reference implementation

This package mirrors [QTSurfer/lastra-convert](https://github.com/QTSurfer/lastra-convert) (Java, JVM CLI). Output is byte-equivalent for the same input + codec choices.

## License

Copyright 2026 Wualabs LTD. Apache License 2.0 — see [LICENSE](https://github.com/QTSurfer/lastra-convert-py/blob/main/LICENSE).
