"""Unit tests for app.fmt (RTL-safe formatter)."""

from __future__ import annotations

from app import fmt


def test_val_wraps_with_lri_pdi():
    result = fmt.val(5)
    assert result == "⁦5⁩"


def test_val_wraps_string():
    assert fmt.val("hello") == "⁦hello⁩"


def test_val_wraps_zero():
    assert fmt.val(0) == "⁦0⁩"


def test_kv_builds_label_colon_val():
    assert fmt.kv("count", 3) == "count: ⁦3⁩"


def test_kv_uses_val_for_value():
    result = fmt.kv("label", "text")
    assert result.startswith("label: ")
    assert "⁦text⁩" in result


def test_section_title_and_indented_lines():
    s = fmt.section("צי", ["line1", "line2"])
    assert s == "▸ צי\n   line1\n   line2"


def test_section_single_line():
    assert fmt.section("h", ["only"]) == "▸ h\n   only"


def test_card_bold_title_html_escaped():
    assert fmt.card("A & B", "body") == "<b>A &amp; B</b>\nbody"


def test_card_plain_title():
    assert fmt.card("Acme", "some body") == "<b>Acme</b>\nsome body"


def test_bool_chip_true():
    assert fmt.bool_chip(True, "on", "off") == "✅ on"


def test_bool_chip_false():
    assert fmt.bool_chip(False, "on", "off") == "⛔️ off"
