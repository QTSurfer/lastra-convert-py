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

## Status

`0.8.0` — published, scaffold only. The CLI entry points listed below are reserved on PyPI; full implementation lands in 0.9.

## Install

```bash
pip install lastra-convert
```

## Usage (planned CLI)

```bash
# Lastra → Parquet
lastra2parquet ticks.lastra ticks.parquet

# Parquet → Lastra (auto-pick best codec per column)
parquet2lastra ticks.parquet ticks.lastra --best

# CSV → Lastra (with explicit schema)
csv2lastra ticks.csv ticks.lastra --schema "ts:long:delta_varint,close:double:alp"

# Lastra → Arrow IPC
lastra2arrow ticks.lastra ticks.arrow
```

## Library API (planned)

```python
from lastra_convert import lastra_to_parquet, parquet_to_lastra

lastra_to_parquet("ticks.lastra", "ticks.parquet")
parquet_to_lastra("ticks.parquet", "ticks.lastra", best=True)
```

## Reference implementation

This package mirrors [QTSurfer/lastra-convert](https://github.com/QTSurfer/lastra-convert) (Java, JVM CLI). Output is byte-equivalent for the same input + codec choices.

## License

Copyright 2026 Wualabs LTD. Apache License 2.0 — see [LICENSE](https://github.com/QTSurfer/lastra-convert-py/blob/main/LICENSE).
