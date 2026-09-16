from __future__ import annotations

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from src.config import DB_PATH, DB_DIR

logger = logging.getLogger(__name__)

class ScreeningDatabase:
    """Database module for screening history persistence."""

    def __init__(self, db_path: str = None) -> None:
        self.db_path = db_path if db_path is not None else DB_PATH
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Creates the table if not exists."""
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS screenings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        document_type TEXT,
                        document_name TEXT,
                        risk_score REAL,
                        risk_level TEXT,
                        recommendation TEXT,
                        findings TEXT,
                        file_hash TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
        except Exception as e:
            logger.error(f"Error initializing DB: {e}")

    def save_screening(self, result: dict[str, Any]) -> int:
        """Inserts a screening record, returns the auto-generated ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                findings = result.get('findings', {})
                findings_json = json.dumps(findings) if not isinstance(findings, str) else findings
                timestamp = result.get('timestamp') or datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO screenings (timestamp, document_type, document_name, risk_score, risk_level, recommendation, findings, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp,
                    result.get('document_type'),
                    result.get('document_name'),
                    result.get('risk_score'),
                    result.get('risk_level'),
                    result.get('recommendation'),
                    findings_json,
                    result.get('file_hash')
                ))
                return cursor.lastrowid or -1
        except Exception as e:
            logger.error(f"Error saving screening: {e}")
            return -1

    def get_screening(self, screening_id: int) -> Optional[dict[str, Any]]:
        """Returns a dict for the row, or None."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM screenings WHERE id = ?', (screening_id,))
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    if result.get('findings'):
                        try:
                            result['findings'] = json.loads(result['findings'])
                        except json.JSONDecodeError:
                            pass
                    return result
                return None
        except Exception as e:
            logger.error(f"Error getting screening {screening_id}: {e}")
            return None

    def get_all_screenings(self, limit: int = 50) -> list[dict[str, Any]]:
        """Returns most recent screenings, ordered by timestamp DESC."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT * FROM screenings ORDER BY timestamp DESC LIMIT ?', (limit,))
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result.get('findings'):
                        try:
                            result['findings'] = json.loads(result['findings'])
                        except json.JSONDecodeError:
                            pass
                    results.append(result)
                return results
        except Exception as e:
            logger.error(f"Error getting all screenings: {e}")
            return []

    def delete_screening(self, screening_id: int) -> bool:
        """Deletes by ID, returns True if a row was deleted."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('DELETE FROM screenings WHERE id = ?', (screening_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting screening {screening_id}: {e}")
            return False

    def get_screening_count(self) -> int:
        """Returns total count of screenings."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM screenings')
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error getting screening count: {e}")
            return 0
