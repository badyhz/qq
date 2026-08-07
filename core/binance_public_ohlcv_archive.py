"""Verified Binance Data Vision USD-M futures OHLCV archive utilities.

Public market data only. No API keys, accounts, orders, Testnet, Live or private
endpoints are used.

Authority:
- monthly USD-M futures kline archives mirror ``GET /fapi/v1/klines`` data;
- every ZIP has a sibling ``.CHECKSUM`` SHA-256 file;
- downloaded data is normalized to the repository's canonical six-column CSV:
  ``timestamp,open,high,low,close,volume`` with timestamp in epoch seconds.

The module is dependency-free so historical research does not depend on a
third-party Binance SDK. Network I/O is isolated behind ``fetch_bytes`` and can
be fully replaced in unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import hashlib
import io
from pathlib import Path
import re
from typing import Callable, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile


BASE_URL = "https://data.binance.vision"
MARKET_PATH = "data/futures/um/monthly/klines"
CANONICAL_HEADER = ("timestamp", "open", "high", "low", "close", "volume")
_SUPPORTED_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M", "1mo",
}
_SYMBOL_RE = re.compile(r"^[A-Z0-9_]{3,30}$")


class ArchiveDownloadError(RuntimeError):
    """Raised when an official archive cannot be fetched or verified."""


@dataclass(frozen=True, order=True)
class ArchiveMonth:
    year: int
    month: int

    def __post_init__(self) -> None:
        if self.year < 2010 or not 1 <= self.month <= 12:
            raise ValueError("invalid archive month")

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


@dataclass(frozen=True)
class ArchiveSpec:
    symbol: str
    interval: str
    month: ArchiveMonth

    def __post_init__(self) -> None:
        symbol = self.symbol.upper()
        if not _SYMBOL_RE.fullmatch(symbol):
            raise ValueError("invalid Binance symbol")
        if self.interval not in _SUPPORTED_INTERVALS:
            raise ValueError(f"unsupported interval: {self.interval}")
        object.__setattr__(self, "symbol", symbol)

    @property
    def filename(self) -> str:
        return f"{self.symbol}-{self.interval}-{self.month.label}.zip"

    @property
    def url(self) -> str:
        return (
            f"{BASE_URL}/{MARKET_PATH}/{self.symbol}/{self.interval}/"
            f"{self.filename}"
        )

    @property
    def checksum_url(self) -> str:
        return f"{self.url}.CHECKSUM"


@dataclass(frozen=True)
class CanonicalOHLCVRow:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("invalid OHLC high")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("invalid OHLC low")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")

    def as_csv_row(self) -> tuple[str, ...]:
        return (
            _format_number(self.timestamp),
            _format_number(self.open),
            _format_number(self.high),
            _format_number(self.low),
            _format_number(self.close),
            _format_number(self.volume),
        )


FetchBytes = Callable[[str], bytes]


def default_fetch_bytes(url: str, timeout_seconds: float = 30.0) -> bytes:
    """Fetch one public archive object with a stable user agent."""
    request = Request(
        url,
        headers={"User-Agent": "qq-offline-backtest/indicator-composite-v1"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except HTTPError as exc:
        raise ArchiveDownloadError(f"HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise ArchiveDownloadError(f"network error for {url}: {exc.reason}") from exc


def iter_months(start: date, end: date) -> tuple[ArchiveMonth, ...]:
    """Return inclusive calendar months intersecting ``start..end``."""
    if end < start:
        raise ValueError("end must be >= start")
    year, month = start.year, start.month
    output: list[ArchiveMonth] = []
    while (year, month) <= (end.year, end.month):
        output.append(ArchiveMonth(year, month))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return tuple(output)


def parse_checksum(payload: bytes, expected_filename: str) -> str:
    """Parse Binance ``.CHECKSUM`` contents and return lowercase SHA-256."""
    text = payload.decode("utf-8", errors="strict").strip()
    parts = text.split()
    if len(parts) < 2:
        raise ArchiveDownloadError("malformed checksum file")
    digest = parts[0].lower()
    filename = parts[-1].lstrip("*")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ArchiveDownloadError("checksum is not SHA-256")
    if filename != expected_filename:
        raise ArchiveDownloadError(
            f"checksum filename mismatch: expected {expected_filename}, got {filename}"
        )
    return digest


def verify_sha256(payload: bytes, expected_digest: str) -> None:
    actual = hashlib.sha256(payload).hexdigest()
    if actual.lower() != expected_digest.lower():
        raise ArchiveDownloadError(
            f"SHA-256 mismatch: expected {expected_digest}, got {actual}"
        )


def _looks_like_header(row: Sequence[str]) -> bool:
    if not row:
        return False
    first = str(row[0]).strip().lower()
    return first in {"open_time", "timestamp", "open time"} or not first.isdigit()


def _timestamp_ms_to_seconds(raw: str) -> float:
    value = float(raw)
    # USD-M futures Binance Vision kline timestamps are milliseconds. Keep a
    # defensive branch for unexpectedly higher precision without silently
    # producing century-scale epoch values.
    if value >= 1e14:
        value /= 1_000_000.0
    else:
        value /= 1_000.0
    return value


def parse_kline_zip(payload: bytes) -> tuple[CanonicalOHLCVRow, ...]:
    """Extract and normalize one official Binance monthly kline ZIP."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if len(names) != 1:
                raise ArchiveDownloadError(
                    f"expected one CSV in ZIP, found {len(names)} files"
                )
            raw_csv = archive.read(names[0]).decode("utf-8-sig")
    except (zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise ArchiveDownloadError("invalid Binance kline ZIP") from exc

    reader = csv.reader(io.StringIO(raw_csv))
    output: list[CanonicalOHLCVRow] = []
    for row_number, row in enumerate(reader, start=1):
        if not row:
            continue
        if row_number == 1 and _looks_like_header(row):
            continue
        if len(row) < 6:
            raise ArchiveDownloadError(
                f"kline row {row_number} has fewer than six columns"
            )
        try:
            output.append(CanonicalOHLCVRow(
                timestamp=_timestamp_ms_to_seconds(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            ))
        except (TypeError, ValueError) as exc:
            raise ArchiveDownloadError(
                f"invalid OHLCV at kline row {row_number}"
            ) from exc

    if not output:
        raise ArchiveDownloadError("archive contains no OHLCV rows")
    return tuple(output)


def download_month(
    spec: ArchiveSpec,
    *,
    fetch_bytes: FetchBytes = default_fetch_bytes,
) -> tuple[CanonicalOHLCVRow, ...]:
    """Fetch checksum + ZIP, verify integrity, then normalize its rows."""
    checksum_payload = fetch_bytes(spec.checksum_url)
    expected_digest = parse_checksum(checksum_payload, spec.filename)
    zip_payload = fetch_bytes(spec.url)
    verify_sha256(zip_payload, expected_digest)
    return parse_kline_zip(zip_payload)


def merge_rows(
    monthly_rows: Iterable[Sequence[CanonicalOHLCVRow]],
    *,
    start: date | None = None,
    end: date | None = None,
) -> tuple[CanonicalOHLCVRow, ...]:
    """Merge, sort and de-duplicate monthly rows by open timestamp."""
    by_timestamp: dict[float, CanonicalOHLCVRow] = {}
    for rows in monthly_rows:
        for row in rows:
            existing = by_timestamp.get(row.timestamp)
            if existing is not None and existing != row:
                raise ArchiveDownloadError(
                    f"conflicting OHLCV rows at timestamp {row.timestamp}"
                )
            by_timestamp[row.timestamp] = row

    ordered = [by_timestamp[key] for key in sorted(by_timestamp)]
    if start is None and end is None:
        return tuple(ordered)

    from datetime import datetime, timezone

    start_epoch = (
        datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp()
        if start is not None else float("-inf")
    )
    end_epoch = (
        datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp() + 86400.0
        if end is not None else float("inf")
    )
    return tuple(row for row in ordered if start_epoch <= row.timestamp < end_epoch)


def write_canonical_csv(path: str | Path, rows: Sequence[CanonicalOHLCVRow]) -> Path:
    """Atomically write canonical six-column OHLCV CSV for existing readers."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CANONICAL_HEADER)
        for row in rows:
            writer.writerow(row.as_csv_row())
    temporary.replace(destination)
    return destination


def download_range_to_csv(
    *,
    symbol: str,
    interval: str,
    start: date,
    end: date,
    output_path: str | Path,
    fetch_bytes: FetchBytes = default_fetch_bytes,
) -> dict:
    """Download verified monthly archives and write one canonical CSV."""
    specs = [ArchiveSpec(symbol, interval, month) for month in iter_months(start, end)]
    monthly = [download_month(spec, fetch_bytes=fetch_bytes) for spec in specs]
    rows = merge_rows(monthly, start=start, end=end)
    if not rows:
        raise ArchiveDownloadError("downloaded range contains no rows")
    path = write_canonical_csv(output_path, rows)
    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "archive_count": len(specs),
        "row_count": len(rows),
        "first_timestamp": rows[0].timestamp,
        "last_timestamp": rows[-1].timestamp,
        "output_path": str(path),
        "source": "binance_data_vision_usdm_monthly_klines",
        "checksum_verified": True,
        "private_api_used": False,
        "orders_enabled": False,
    }


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return format(float(value), ".15g")
