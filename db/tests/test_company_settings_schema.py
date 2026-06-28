from shepherd_db.models import CompanySettings


def test_company_settings_has_schema_name_column():
    col = CompanySettings.__table__.columns["schema_name"]
    assert col.nullable is False
