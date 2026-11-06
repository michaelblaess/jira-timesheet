"""Gemeinsame Darstellung von Mehrarbeit fuer Kalender und Jahresansicht.

Ist gegen Soll wird in beiden Ansichten gleich gezeigt: bis zum Soll in der
Ampelfarbe, was darueber liegt, in der Warnfarbe des Themes. Vorbild ist der
Balken der Qt-Fassung (``paint_hours_bar`` in jira-timesheet-qt).
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from jira_timesheet.i18n import format_number

# Toleranz fuer Rundungsrauschen: 8,00 h gegen 8 h ist keine Mehrarbeit.
_EPSILON = 0.005

# Rueckfall, wenn kein laufendes App-Objekt da ist (Tests, Render ohne App).
_FALLBACK_OVER = "dark_orange"

BAR_MARKER = "│"


def is_over(actual: float, target: float) -> bool:
    """Prueft, ob die gebuchten Stunden ueber dem Soll liegen."""
    return actual > target + _EPSILON


def format_delta(actual: float, target: float, decimals: int = 2) -> str:
    """Abweichung vom Soll mit Vorzeichen, z.B. '+7,75h'."""
    delta = actual - target
    sign = "+" if delta >= 0 else "-"
    return f"{sign}{format_number(abs(delta), decimals)}h"


def over_color(widget: Widget) -> str:
    """Warnfarbe des aktiven Themes als Rich-Farbe, wie das Orange der Qt-Fassung.

    In ``render()`` gibt es keine CSS-Variablen, deshalb kommt die Farbe aus
    dem Theme-Objekt. Ohne App (Tests) faellt sie auf eine feste Farbe zurueck.
    """
    try:
        theme = widget.app.current_theme
        return str(theme.warning or _FALLBACK_OVER)
    except Exception:
        return _FALLBACK_OVER


def hours_bar(
    actual: float,
    target: float,
    length: int,
    fill_style: str,
    over_style: str,
) -> Text:
    """Balken Ist gegen Soll samt Mehrarbeit.

    Die Schiene reicht bis zum groesseren von Ist und Soll. Bis zum Soll wird in
    ``fill_style`` gefuellt, bei Mehrarbeit folgt eine Marke am Soll und danach
    der Ueberhang in ``over_style``.

    Args:
        actual: Gebuchte Stunden.
        target: Sollstunden.
        length: Breite des Balkens in Zeichen.
        fill_style: Stil des Anteils bis zum Soll.
        over_style: Stil des Ueberhangs.

    Returns:
        Der Balken als Rich-Text, immer genau ``length`` Zeichen breit.
    """
    text = Text()
    if target <= 0 or actual <= 0:
        text.append("░" * length, style="dim")
        return text

    if not is_over(actual, target):
        filled = min(length, int(actual / target * length))
        text.append("█" * filled, style=fill_style)
        text.append("░" * (length - filled), style="dim")
        return text

    # Marke und mindestens ein Zeichen Ueberhang muessen immer sichtbar bleiben.
    regular = min(length - 2, max(1, round(target / actual * length)))
    over = length - regular - 1
    text.append("█" * regular, style=fill_style)
    text.append(BAR_MARKER, style="bold")
    text.append("█" * over, style=over_style)
    return text
