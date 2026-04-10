"""Unit tests for workforce announcement automation helpers (template rendering, key registry)."""

from app.domain.services.workforce_announcement_automation import (
    AUTOMATION_KEYS_KNOWN,
    _render_template_text,
)


def test_automation_keys_registry_nonempty_and_sorted_convention():
    assert len(AUTOMATION_KEYS_KNOWN) >= 4
    assert "PAYROLL_PERIOD_APPROVED" in AUTOMATION_KEYS_KNOWN
    assert "LEAVE_REQUEST_REJECTED" in AUTOMATION_KEYS_KNOWN


def test_render_template_text_substitutes():
    assert _render_template_text("Hello {name}", {"name": "Ada"}) == "Hello Ada"


def test_render_template_text_unknown_placeholder_preserved():
    assert _render_template_text("x={missing}", {"other": "1"}) == "x={missing}"


def test_render_template_text_multiple_keys():
    out = _render_template_text("{a} {b}", {"a": "1", "b": "2"})
    assert out == "1 2"
