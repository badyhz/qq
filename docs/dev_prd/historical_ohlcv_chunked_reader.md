# Historical OHLCV Chunked Reader — Design Document

## Purpose

Read large OHLCV CSV files without loading the entire file into memory.
Uses stdlib `csv.reader` in fixed-size chunk batches.

## Chunk Size Selection

Default: 500 bars per chunk.

Rationale:
- 500 rows of OHLCV data ~ 40KB in memory
- Allows streaming through multi-million row files
- Each chunk yields `List[HistoricalBar]` for downstream processing

Configurable via `chunk_size` parameter. Minimum: 1.

## Memory Model

```
CSV File (on disk, any size)
    │
    ▼ csv.reader (streaming)
    │
    ├── chunk[0] → List[HistoricalBar] (500 items)
    ├── chunk[1] → List[HistoricalBar] (500 items)
    ├── chunk[2] → List[HistoricalBar] (500 items)
    │   ...
    └── chunk[n] → List[HistoricalBar] (remainder)
```

Peak memory: O(chunk_size) bars at any time.
The generator pattern ensures previous chunks are garbage-collected
when the consumer moves to the next chunk.

## Column Mapping

`OHLCVColumnMapping` dataclass maps CSV column names to fields:
- `timestamp_col` → bar.timestamp
- `open_col` → bar.open
- `high_col` → bar.high
- `low_col` → bar.low
- `close_col` → bar.close
- `volume_col` → bar.volume

Supports arbitrary column names (e.g., "Date", "Open", "Volume").

## Gap Detection

Two strategies:

### 1. Intra-chunk detection (fast)
For each consecutive pair of bars in a chunk, check if the timestamp
delta exceeds `1.5 * expected_interval_seconds`.

### 2. Cross-chunk detection (via summarize_dataset)
Accumulates all timestamps across chunks, sorts once at the end,
then scans for gaps. More accurate but requires storing timestamps.

Gap threshold: `1.5 * expected_interval_seconds` (default 300s for 5m bars).

## Dedup Strategy

`deduplicate_bars(bars)` keeps the first occurrence of each timestamp.
Uses a `set` for O(1) lookup per bar.

In `summarize_dataset`, duplicates are detected across the full file:
- First occurrence → counted as valid
- Subsequent occurrences → counted as duplicate, added to issues

## Validation

`validate_ohlcv_chunk(bars)` checks each bar for:
- **Zero range**: open == high == low == close (WARNING)
- **Negative volume**: volume < 0 (ERROR)

Invalid bars from `HistoricalBar.__post_init__` are skipped during
CSV parsing (caught by try/except in the reader loop).

## Quality Report

`summarize_dataset()` produces a `HistoricalDataQualityReport`:
- `total_rows`: all parsed rows
- `valid_rows`: non-duplicate rows
- `duplicate_count`: duplicate timestamps
- `gap_count`: missing bar intervals
- `invalid_ohlcv_count`: zero-range + negative-volume bars
- `is_clean`: True iff all counts are 0
- `issues`: tuple of `HistoricalDataIssue` descriptors

## File Format Support

- Standard CSV with header row
- Comma-separated values
- Timestamps: epoch seconds (float) or ISO 8601 strings
- Numeric fields: standard float parsing

## Error Handling

- Missing CSV file → `FileNotFoundError`
- Missing columns → `ValueError` with column names
- Unparseable rows → silently skipped (logged in quality report)
- Invalid bar data (high < low) → skipped via HistoricalBar validation
