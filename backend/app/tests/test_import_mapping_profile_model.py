from app.domain.models.import_mapping_profile import ImportMappingProfile


def test_import_mapping_profile_includes_updated_at_column():
    assert "updated_at" in ImportMappingProfile.__table__.columns.keys()
