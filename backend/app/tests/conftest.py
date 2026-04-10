"""Pytest fixtures and bootstrap.

`app.db.session` loads settings at import time. Set minimal env before any test module
imports application code so collection succeeds without a local `.env`.
"""
from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ai_coo:ai_coo@localhost:5432/ai_coo")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

from decimal import Decimal

import pytest


@pytest.fixture
def sample_monthly_aggregates():
    class M:
        def __init__(self, rev, exp):
            self.revenue_total = Decimal(rev)
            self.expense_total = Decimal(exp)

    return [M("1000", "1400"), M("1200", "1800"), M("900", "1500")]


@pytest.fixture
def sample_metrics():
    return {
        "kpis": {"revenue_mtd": "1200", "expenses_mtd": "900"},
        "alerts": [{"title": "Runway low", "severity": "HIGH"}],
    }
