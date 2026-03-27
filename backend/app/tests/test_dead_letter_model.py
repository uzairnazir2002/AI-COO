from app.domain.models.dead_letter_event import DeadLetterEvent


def test_dead_letter_event_has_updated_at_column():
    assert hasattr(DeadLetterEvent, "updated_at")
