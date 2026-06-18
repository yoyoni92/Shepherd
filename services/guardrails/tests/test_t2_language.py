"""T2 - Language rail (config-driven from system_config.allowed_languages)."""
from app.deterministic import language

ALLOWED = ["he", "en"]


def test_hebrew_passes():
    result = language("עדכן קילומטראז לרכב מספר 1234", ALLOWED)
    assert result["pass"] is True


def test_english_passes():
    result = language("Update mileage for vehicle 1234 to 50000 km", ALLOWED)
    assert result["pass"] is True


def test_french_fails():
    result = language("Je dois mettre a jour le kilometrage du vehicule", ALLOWED)
    assert result["pass"] is False
    assert "fr" in result["reason"]


def test_mixed_he_en_passes():
    # Hebrew-dominant bilingual text is common in Israeli fleet management
    result = language("נהג עדכן קילומטראז לרכב מספר 1234 km updated", ALLOWED)
    assert result["pass"] is True


def test_empty_text_fails_gracefully():
    result = language("", ALLOWED)
    # langdetect raises on empty text; we return a clean failure
    assert result["pass"] is False
