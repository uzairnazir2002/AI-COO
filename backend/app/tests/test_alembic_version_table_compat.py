from __future__ import annotations

import re
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
VERSIONS_DIR = MIGRATIONS_DIR / "versions"
ENV_PY = MIGRATIONS_DIR / "env.py"


def _revision_ids() -> list[str]:
    ids: list[str] = []
    pattern = re.compile(r"revision\s*:\s*str\s*=\s*\"([^\"]+)\"|revision\s*=\s*\"([^\"]+)\"")
    for path in VERSIONS_DIR.glob("*.py"):
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            ids.append(match.group(1) or match.group(2))
    return ids


def test_migration_revision_ids_fit_alembic_version_column() -> None:
    revision_ids = _revision_ids()
    assert revision_ids, "expected at least one migration revision id"
    assert all(len(revision_id) <= 128 for revision_id in revision_ids)
    # We currently use descriptive IDs longer than Alembic's default varchar(32).
    assert any(len(revision_id) > 32 for revision_id in revision_ids)


def test_env_hardens_alembic_version_column_length() -> None:
    text = ENV_PY.read_text(encoding="utf-8")
    assert "ALEMBIC_VERSION_LEN = 128" in text
    assert "ensure_alembic_version_capacity(connection)" in text
    assert "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR" in text
