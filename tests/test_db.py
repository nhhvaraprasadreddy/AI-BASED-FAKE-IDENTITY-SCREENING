"""Tests for src.database.db — ScreeningDatabase."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.database.db import ScreeningDatabase


@pytest.fixture
def sample_screening() -> dict:
    """Minimal valid screening record."""
    return {
        "timestamp": "2026-08-29T12:00:00",
        "document_type": "aadhaar",
        "document_name": "Aadhaar Card",
        "risk_score": 0.25,
        "risk_level": "LOW",
        "recommendation": "No significant indicators detected.",
        "findings": {
            "validation": {"checks": [], "valid_count": 0, "total_count": 0},
            "tampering": {"checks": [], "suspicion_score": 0.0},
        },
        "file_hash": "abc123def456",
    }


@pytest.fixture
def db(tmp_path: Path) -> ScreeningDatabase:
    """Fresh database in a temp directory."""
    db_file = tmp_path / "test_screenings.db"
    return ScreeningDatabase(db_path=str(db_file))


class TestScreeningDatabase:
    """Suite for ScreeningDatabase CRUD operations."""

    def test_initialization_creates_file(self, tmp_path: Path) -> None:
        db_file = tmp_path / "init_test.db"
        ScreeningDatabase(db_path=str(db_file))
        assert db_file.exists()

    def test_save_returns_positive_id(self, db: ScreeningDatabase, sample_screening: dict) -> None:
        sid = db.save_screening(sample_screening)
        assert isinstance(sid, int)
        assert sid > 0

    def test_save_and_retrieve(self, db: ScreeningDatabase, sample_screening: dict) -> None:
        sid = db.save_screening(sample_screening)
        row = db.get_screening(sid)
        assert row is not None
        assert row["document_type"] == "aadhaar"
        assert row["risk_level"] == "LOW"
        assert row["risk_score"] == pytest.approx(0.25)
        # findings should be deserialized from JSON
        assert isinstance(row["findings"], dict)
        assert "validation" in row["findings"]

    def test_get_nonexistent_returns_none(self, db: ScreeningDatabase) -> None:
        assert db.get_screening(9999) is None

    def test_get_all_screenings(self, db: ScreeningDatabase, sample_screening: dict) -> None:
        for i in range(3):
            s = sample_screening.copy()
            s["risk_score"] = 0.1 * (i + 1)
            db.save_screening(s)

        results = db.get_all_screenings()
        assert isinstance(results, list)
        assert len(results) == 3

    def test_get_all_screenings_respects_limit(self, db: ScreeningDatabase, sample_screening: dict) -> None:
        for _ in range(5):
            db.save_screening(sample_screening)
        results = db.get_all_screenings(limit=2)
        assert len(results) == 2

    def test_delete_screening(self, db: ScreeningDatabase, sample_screening: dict) -> None:
        sid = db.save_screening(sample_screening)
        assert db.delete_screening(sid) is True
        assert db.get_screening(sid) is None

    def test_delete_nonexistent_returns_false(self, db: ScreeningDatabase) -> None:
        assert db.delete_screening(9999) is False

    def test_get_screening_count(self, db: ScreeningDatabase, sample_screening: dict) -> None:
        assert db.get_screening_count() == 0
        db.save_screening(sample_screening)
        db.save_screening(sample_screening)
        assert db.get_screening_count() == 2

    def test_findings_json_roundtrip(self, db: ScreeningDatabase, sample_screening: dict) -> None:
        """Verify findings survive JSON serialization → deserialization."""
        sid = db.save_screening(sample_screening)
        row = db.get_screening(sid)
        assert row["findings"] == sample_screening["findings"]


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: Hardening tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDBHardening:
    """Phase 7 hardening tests for database edge cases."""

    def test_save_empty_record(self, db: ScreeningDatabase) -> None:
        """Empty dict should not crash — returns -1 or valid ID."""
        sid = db.save_screening({})
        # Should handle gracefully (may return -1 or succeed with defaults)
        assert isinstance(sid, int)

    def test_save_none_findings(self, db: ScreeningDatabase) -> None:
        """Record with None findings should save and retrieve."""
        record = {
            "timestamp": "2026-01-01T00:00:00",
            "document_type": "aadhaar",
            "risk_score": 0.0,
            "risk_level": "LOW",
            "findings": None,
            "file_hash": "test",
        }
        sid = db.save_screening(record)
        assert sid > 0
        row = db.get_screening(sid)
        assert row is not None

    def test_get_all_empty_db(self, db: ScreeningDatabase) -> None:
        """Empty database should return empty list, not crash."""
        results = db.get_all_screenings()
        assert results == []
        assert db.get_screening_count() == 0

    def test_nested_findings_roundtrip(self, db: ScreeningDatabase) -> None:
        """Complex nested findings should survive JSON roundtrip."""
        complex_findings = {
            "validation": {"checks": [{"passed": True, "message": "OK"}], "valid_count": 1},
            "tampering": {"checks": [{"name": "ELA", "suspicious": False}], "score": 0.1},
            "risk": {"factors": [{"category": "validation", "name": "test"}]},
            "consistency": {"status": "success", "consistent": True},
        }
        record = {
            "timestamp": "2026-01-01T00:00:00",
            "document_type": "pan",
            "risk_score": 0.15,
            "risk_level": "LOW",
            "findings": complex_findings,
            "file_hash": "nested_test",
        }
        sid = db.save_screening(record)
        row = db.get_screening(sid)
        assert row["findings"]["validation"]["checks"][0]["passed"] is True
        assert row["findings"]["risk"]["factors"][0]["category"] == "validation"

    def test_new_db_dir_creation(self, tmp_path: Path) -> None:
        """DB should create nested directories if they don't exist."""
        db_path = tmp_path / "a" / "b" / "c" / "test.db"
        db = ScreeningDatabase(db_path=str(db_path))
        assert db_path.exists()
        assert db.get_screening_count() == 0
