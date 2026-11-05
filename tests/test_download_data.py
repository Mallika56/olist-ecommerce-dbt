"""Unit tests for scripts/download_data.py. No network or filesystem outside tmp_path."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import download_data as dd  # noqa: E402


def test_sha256_matches_known_digest(tmp_path):
    f = tmp_path / "sample.csv"
    f.write_bytes(b"hello olist")
    assert dd.sha256(f) == "559d4a51b51ac00548602892ee0ff3764e5407a8b700cc0b588feac2ded42048"


def test_verify_fails_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "RAW", tmp_path)
    monkeypatch.setattr(dd, "FILES", {"a.csv": ("erp", "deadbeef")})
    assert dd.verify() is False


def test_verify_fails_on_checksum_mismatch(tmp_path, monkeypatch):
    f = tmp_path / "a.csv"
    f.write_bytes(b"wrong content")
    monkeypatch.setattr(dd, "RAW", tmp_path)
    monkeypatch.setattr(dd, "FILES", {"a.csv": ("erp", "0" * 64)})
    assert dd.verify() is False


def test_verify_passes_when_checksum_matches(tmp_path, monkeypatch):
    f = tmp_path / "a.csv"
    f.write_bytes(b"hello olist")
    monkeypatch.setattr(dd, "RAW", tmp_path)
    monkeypatch.setattr(dd, "FILES", {"a.csv": ("erp", dd.sha256(f))})
    assert dd.verify() is True


def test_from_mirror_skips_file_already_matching(tmp_path, monkeypatch):
    f = tmp_path / "a.csv"
    f.write_bytes(b"hello olist")
    monkeypatch.setattr(dd, "RAW", tmp_path)
    monkeypatch.setattr(dd, "FILES", {"a.csv": ("erp", dd.sha256(f))})
    with patch.object(dd.urllib.request, "urlretrieve") as mock_get:
        dd.from_mirror()
    mock_get.assert_not_called()


def test_from_mirror_downloads_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "RAW", tmp_path)
    monkeypatch.setattr(dd, "FILES", {"a.csv": ("erp", "0" * 64)})
    with patch.object(dd.urllib.request, "urlretrieve") as mock_get:
        dd.from_mirror()
    mock_get.assert_called_once()
    called_url = mock_get.call_args[0][0]
    assert called_url == dd.MIRROR.format(folder="erp", name="a.csv")


def test_from_kaggle_invokes_expected_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "RAW", tmp_path)
    with patch.object(dd.subprocess, "run") as mock_run:
        dd.from_kaggle()
    mock_run.assert_called_once_with(
        ["kaggle", "datasets", "download", "-d", "olistbr/brazilian-ecommerce",
         "-p", str(tmp_path), "--unzip"],
        check=True,
    )


def test_main_exits_when_verification_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "RAW", tmp_path)
    monkeypatch.setattr(sys, "argv", ["download_data.py"])
    with patch.object(dd, "from_mirror"), patch.object(dd, "verify", return_value=False):
        with pytest.raises(SystemExit):
            dd.main()
