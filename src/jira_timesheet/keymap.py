"""Tastenbelegung dieser Anwendung.

Die Mechanik (Stile, Vim-Ebene, Anwenderkorrekturen, Pruefer) liegt in
`textual_widgets.keymap`. Hier steht nur, was diese Anwendung ausmacht: ihre
Aktionen im Bestandsstil, die Zuordnung zu den Beschriftungen aus dem
Sprachpaket und die Bruecke zu den Einstellungen.

Public API:
    - `CLASSIC` - die Belegung im Bestandsstil, so wie sie bis v1.21.0 galt.
    - `LABEL_KEYS` / `TOOLTIP_KEYS` - Aktion auf i18n-Schluessel.
    - `FOOTER_ORDER` - die Reihenfolge, in der die Tasten im Footer stehen.
    - `resolve(settings)` - die fertige Belegung aus den Einstellungen.
    - `style_from_settings(settings)` - der gewaehlte oder vorgeschlagene Stil.

Die Schluessel sind die Aktionsnamen, nicht die Beschriftungen - `t()` laeuft
erst beim Binden, damit ein Sprachwechsel ohne Neustart der Tabelle wirkt.
"""

from __future__ import annotations

from typing import Any

from textual_widgets.keymap import (
    COMMON_FUNCTION_KEYS,
    KeyBinding,
    KeymapStyle,
    ResolvedKeymap,
    default_style_for_platform,
    parse_overrides,
    resolve_keymap,
)

CLASSIC: dict[str, KeyBinding] = {
    "quit": KeyBinding(("q", "Q")),
    "export_excel": KeyBinding(("e", "E")),
    "export_pdf": KeyBinding(("p", "P")),
    "show_details": KeyBinding(("d", "D")),
    # copy_log: Shortcut bleibt, aber nicht im Footer - das Log-Kontextmenue
    # bietet "Log kopieren" ohnehin an.
    "copy_log": KeyBinding(("c", "C"), show=False),
    "show_settings": KeyBinding(("s", "S")),
    "show_about": KeyBinding(("i", "I")),
    "next_tab": KeyBinding(("tab",), priority=True),
    # Konvention: / fokussiert den Filter, die Lupe macht ihn sichtbar.
    "focus_filter": KeyBinding(("slash",), show=False),
    "ticket_report": KeyBinding(("b", "B")),
    # EINE Taste fuer alle Reiter. Vorher lud "g" den Stundenzettel und F5 die
    # Ticket-Ansichten - zwei Tasten fuer dieselbe Absicht.
    "refresh": KeyBinding(("f5",)),
    "toggle_anon": KeyBinding(("a", "A")),
    "reset_cache": KeyBinding(("r", "R")),
    "toggle_log": KeyBinding(("l", "L")),
    "cycle_theme": KeyBinding(("t", "T")),
    "manual_entry": KeyBinding(("m", "M")),
    # Loeschen bewusst auf DEL statt auf einen Buchstaben - destruktiv.
    "delete_manual": KeyBinding(("delete",)),
    # Monat-Navigation ist als Klick-Pfeile im ConfigPanel sichtbar, der
    # Shortcut bleibt funktional, im Footer aber ausgeblendet.
    "prev_month": KeyBinding(("comma",), show=False),
    "next_month": KeyBinding(("full_stop",), show=False),
    # Uebersicht der Belegung. "?" ist hier frei und in Terminals die
    # gelaeufige Taste dafuer - im Footer waere sie nur Ballast.
    "keymap_overview": KeyBinding(("question_mark",), show=False),
}
"""Der Bestandsstil - Stand v1.21.0, woertlich aus dem frueheren app.py."""

FOOTER_ORDER: tuple[str, ...] = tuple(CLASSIC)
"""Die Reihenfolge im Footer. Entspricht der Reihenfolge in `CLASSIC`."""

LABEL_KEYS: dict[str, str] = {
    "quit": "binding.quit",
    "export_excel": "binding.excel",
    "export_pdf": "binding.pdf",
    "show_details": "binding.details",
    "copy_log": "binding.copy_log",
    "show_settings": "binding.settings",
    "show_about": "binding.info",
    "next_tab": "binding.switch_view",
    "focus_filter": "binding.filter",
    "ticket_report": "binding.ticket_report",
    "refresh": "binding.refresh",
    "toggle_anon": "binding.anonymize",
    "reset_cache": "binding.reset_cache",
    "toggle_log": "binding.toggle_log",
    "cycle_theme": "binding.theme",
    "manual_entry": "binding.manual_entry",
    "delete_manual": "binding.delete_manual",
    "prev_month": "binding.month",
    "next_month": "binding.month",
    "keymap_overview": "binding.keymap_overview",
}
"""Aktion auf den i18n-Schluessel ihrer Footer-Beschriftung."""

TOOLTIP_KEYS: dict[str, str] = {
    "quit": "tooltip.quit",
    "refresh": "tooltip.refresh",
    "export_excel": "tooltip.excel",
    "export_pdf": "tooltip.pdf",
    "show_details": "tooltip.details",
    "show_settings": "tooltip.settings",
    "show_about": "tooltip.info",
    "next_tab": "tooltip.switch_view",
    "toggle_anon": "tooltip.anonymize",
    "reset_cache": "tooltip.reset_cache",
    "toggle_log": "tooltip.toggle_log",
    "cycle_theme": "tooltip.theme",
    "manual_entry": "tooltip.manual_entry",
    "delete_manual": "tooltip.delete_manual",
    "reload_board": "tooltip.tickets",
    "keymap_overview": "tooltip.keymap_overview",
}
"""Aktion auf den i18n-Schluessel ihres Footer-Tooltips."""

# Die Anzeige der Taste im Footer. Ohne das steht dort "full_stop" statt ">".
KEY_DISPLAY: dict[str, str] = {
    "slash": "/",
    "comma": "<",
    "full_stop": ">",
    "delete": "DEL",
    "question_mark": "?",
    "tab": "TAB",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
}


def key_display(key: str) -> str:
    """Uebersetzt einen Tastennamen in seine Anzeige im Footer.

    Args:
        key: Der Tastenname, so wie Textual ihn kennt.

    Returns:
        Der Text fuer den Footer.
    """

    return KEY_DISPLAY.get(key, key)


def style_from_settings(settings: Any) -> KeymapStyle:
    """Ermittelt den Stil aus den Einstellungen.

    Ein leerer Wert heisst "noch nicht entschieden" - dann entscheidet die
    Plattform, damit eine frische Installation auf dem Mac nicht mit F-Tasten
    startet, die das Betriebssystem abfaengt.

    Args:
        settings: Die geladenen Einstellungen.

    Returns:
        Der anzuwendende Stil.
    """

    gewaehlt = str(getattr(settings, "keymap_style", "") or "").strip().lower()
    for stil in KeymapStyle:
        if gewaehlt == stil.value:
            return stil
    return default_style_for_platform()


def resolve(settings: Any) -> ResolvedKeymap:
    """Baut die fertige Belegung aus den Einstellungen.

    Args:
        settings: Die geladenen Einstellungen.

    Returns:
        Die Belegung samt Beanstandungen. Die Beanstandungen gehoeren ins Log,
        nicht in einen Dialog - sie betreffen die Einstellungsdatei, nicht den
        laufenden Vorgang.
    """

    overrides, probleme = parse_overrides(getattr(settings, "keymap_custom", None))
    ergebnis = resolve_keymap(
        style_from_settings(settings),
        CLASSIC,
        function_keys=COMMON_FUNCTION_KEYS,
        overrides=overrides,
        vim_navigation=bool(getattr(settings, "keymap_vim", False)),
    )
    return ResolvedKeymap(bindings=ergebnis.bindings, problems=probleme + ergebnis.problems)
