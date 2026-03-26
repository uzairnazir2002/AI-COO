from __future__ import annotations

import os
import subprocess
import sys


os.environ.setdefault("SECRET_KEY", "migration-safety-local")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ai_coo:ai_coo@localhost:5432/ai_coo")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


def _run(*args: str) -> str:
    cmd = [sys.executable, "-m", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        detail = "\n".join(part for part in [stdout, stderr] if part)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{detail}")
    return stdout


def _head_revisions() -> list[str]:
    out = _run("alembic", "heads")
    heads: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        token = line.split(" ", 1)[0]
        heads.append(token)
    return heads


def _assert_single_head() -> str:
    heads = _head_revisions()
    if len(heads) != 1:
        raise RuntimeError(f"Expected exactly one alembic head revision, found {len(heads)}: {heads}")
    return heads[0]


def main() -> int:
    _assert_single_head()
    _run("alembic", "upgrade", "head")

    # Full reset from clean DB state and re-apply all migrations.
    _run("alembic", "downgrade", "base")
    _run("alembic", "upgrade", "head")

    # One-step downgrade/upgrade smoke for latest revision reversibility.
    _run("alembic", "downgrade", "-1")
    _run("alembic", "upgrade", "head")

    print("migration_safety_check: ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
