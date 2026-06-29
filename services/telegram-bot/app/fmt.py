"""RTL-safe Telegram message formatter (pure, no I/O).

Hebrew (RTL) text mixed with Latin/numbers causes Telegram to jumble the
order. Wrapping LTR content in Unicode LRI/PDI isolates (U+2066/U+2069)
fixes the rendering inside RTL text.

Telegram HTML accepts only b/i/u/s/code/pre/a - no div, no dir attribute.
"""

from __future__ import annotations

import html as _html

# Unicode LRI (Left-to-Right Isolate) U+2066 and PDI (Pop Directional Isolate) U+2069
_LRI = "⁦"
_PDI = "⁩"


def val(x: object) -> str:
    """Wrap a value in a Unicode LTR isolate so it renders correctly in RTL text."""
    return f"{_LRI}{x}{_PDI}"


def kv(label: str, value: object) -> str:
    """One metric line: 'label: ⁦value⁩'."""
    return f"{label}: {val(value)}"


def section(title: str, lines: list[str]) -> str:
    """A labeled block: '▸ title' then each line indented 3 spaces."""
    body = "\n".join(f"   {line}" for line in lines)
    return f"▸ {title}\n{body}"


def card(title: str, body: str) -> str:
    """Bold HTML title (html-escaped) followed by body."""
    return f"<b>{_html.escape(title)}</b>\n{body}"


def bool_chip(ok: bool, on: str, off: str) -> str:
    """'✅ on' if ok else '⛔️ off'."""
    return f"✅ {on}" if ok else f"⛔️ {off}"
