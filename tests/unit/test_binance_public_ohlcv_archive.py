from __future__ import annotations

from datetime import date
import hashlib
import io
from pathlib import Path
import zipfile

import pytest

from core.binance_public_ohlcv_archive import (
    ArchiveDownloadError,
    ArchiveMonth,
    ArchiveSpec,
    CanonicalOHLCVRow,
    download_month,
    download_range_to_csv,
    iter_months,
    merge_rows,
    parse_checksum,
    parse_kline_zip,
    verify_sha256,
)


def _zip_csv(text: str, filename: str = "BTCUSDT-15m-2026-07.csv") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, text)
    return buffer.getvalue()


def test_archive_spec_uses_official_usdm_monthly_path():
    spec = ArchiveSpec("btcusdt", "15m", ArchiveMonth(2026, 7))
    assert spec.symbol == "BTCUSDT"
    assert spec.filename == "BTCUSDT-15m-2026-07.zip"
    assert spec.url == (
        "https://data.binance.vision/data/futures/um/monthly/klines/"
        "BTCUSDT/15m/BTCUSDT-15m-2026-07.zip"
    )
    assert spec.checksum_url == spec.url + ".CHECKSUM"


def test_iter_months_is_inclusive_across_year_boundary():
    assert [month.label for month in iter_months(
        date(2025, 11, 10), date(2026, 2, 2)
    )] == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_checksum_parser_requires_expected_filename():
    digest = "a" * 64
    assert parse_checksum(
        f"{digest}  BTCUSDT-15m-2026-07.zip\n".encode(),
        "BTCUSDT-15m-2026-07.zip",
    ) == digest
    with pytest.raises(ArchiveDownloadError, match="filename mismatch"):
        parse_checksum(
            f"{digest}  ETHUSDT-15m-2026-07.zip\n".encode(),
            "BTCUSDT-15m-2026-07.zip",
        )


def test_verify_sha256_fails_closed_on_mismatch():
    payload = b"abc"
    verify_sha256(payload, hashlib.sha256(payload).hexdigest())
    with pytest.raises(ArchiveDownloadError, match="SHA-256 mismatch"):
        verify_sha256(payload, "0" * 64)


def test_parse_kline_zip_supports_headerless_binance_rows():
    payload = _zip_csv(
        "1785456000000,100,105,99,104,123.5,1785456899999,0,0,0,0,0\n"
        "1785456900000,104,106,103,105,120,1785457799999,0,0,0,0,0\n"
    )
    rows = parse_kline_zip(payload)
    assert len(rows) == 2
    assert rows[0].timestamp == pytest.approx(1785456000.0)
    assert rows[0].open == 100.0
    assert rows[0].close == 104.0
    assert rows[0].volume == 123.5


def test_parse_kline_zip_supports_header_row():
    payload = _zip_csv(
        "open_time,open,high,low,close,volume,close_time,quote_volume,trades,taker_base,taker_quote,ignore\n"
        "1785456000000,100,105,99,104,123.5,1785456899999,0,0,0,0,0\n"
    )
    rows = parse_kline_zip(payload)
    assert len(rows) == 1
    assert rows[0].high == 105.0


def test_parse_kline_zip_rejects_multiple_payload_files():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.csv", "1,1,1,1,1,1\n")
        archive.writestr("b.csv", "1,1,1,1,1,1\n")
    with pytest.raises(ArchiveDownloadError, match="expected one CSV"):
        parse_kline_zip(buffer.getvalue())


def test_download_month_verifies_checksum_before_parsing():
    spec = ArchiveSpec("BTCUSDT", "15m", ArchiveMonth(2026, 7))
    zip_payload = _zip_csv(
        "1785456000000,100,105,99,104,123.5,1785456899999,0,0,0,0,0\n"
    )
    digest = hashlib.sha256(zip_payload).hexdigest()
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        if url.endswith(".CHECKSUM"):
            return f"{digest}  {spec.filename}\n".encode()
        return zip_payload

    rows = download_month(spec, fetch_bytes=fetch)
    assert len(rows) == 1
    assert calls == [spec.checksum_url, spec.url]


def test_merge_rows_deduplicates_identical_month_boundaries_and_sorts():
    first = CanonicalOHLCVRow(2.0, 100, 101, 99, 100, 1)
    duplicate = CanonicalOHLCVRow(2.0, 100, 101, 99, 100, 1)
    earlier = CanonicalOHLCVRow(1.0, 90, 91, 89, 90, 1)
    assert merge_rows([[first], [duplicate, earlier]]) == (earlier, first)


def test_merge_rows_rejects_conflicting_duplicate_timestamp():
    a = CanonicalOHLCVRow(1.0, 100, 101, 99, 100, 1)
    b = CanonicalOHLCVRow(1.0, 100, 102, 99, 101, 1)
    with pytest.raises(ArchiveDownloadError, match="conflicting OHLCV"):
        merge_rows([[a], [b]])


def test_download_range_writes_canonical_csv_without_committing_raw_zip(tmp_path: Path):
    # One month only; fake official objects remain entirely in memory.
    spec = ArchiveSpec("BTCUSDT", "15m", ArchiveMonth(2026, 7))
    zip_payload = _zip_csv(
        "1785456000000,100,105,99,104,123.5,1785456899999,0,0,0,0,0\n"
    )
    digest = hashlib.sha256(zip_payload).hexdigest()

    def fetch(url: str) -> bytes:
        if url.endswith(".CHECKSUM"):
            return f"{digest}  {spec.filename}\n".encode()
        return zip_payload

    output = tmp_path / "BTCUSDT_15m.csv"
    result = download_range_to_csv(
        symbol="BTCUSDT",
        interval="15m",
        start=date(2026, 7, 1),
        end=date(2026, 7, 31),
        output_path=output,
        fetch_bytes=fetch,
    )

    assert result["checksum_verified"] is True
    assert result["private_api_used"] is False
    assert result["orders_enabled"] is False
    lines = output.read_text().splitlines()
    assert lines[0] == "timestamp,open,high,low,close,volume"
    assert lines[1].startswith("1785456000,100,105,99,104,123.5")
