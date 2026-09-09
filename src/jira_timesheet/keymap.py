"""Tastenbelegung dieser Anwendung.

Die Mechanik (Stile, Vim-Ebene, Anwenderkorrekturen, Pruefer) liegt in
`textual_widgets.keymap`. Hier steht nur, was diese Anwendung ausmacht: ihre
Aktionen im Bestandsstil, die Zuordnung zu den Beschriftungen aus dem
Sprachpaket und die Bruecke zu den Einstellungen.

Public API:
    - `CLASSIC` - die Belegung im Bestandsstil, so wie sie bis v1.21.0 galt.
    - `LABEL_KEYS` / `TOOLTIP_KEYS` - Aktion auf i18n-Schluessel.
    - `APP_FUNCTION_KEYS` / `FUNCTION_KEYS` - die F-Tasten dieser Anwendung.
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
    sort_for_footer,
)

CLASSIC: dict[str, KeyBinding] = {
    "quit": KeyBinding(("q", "Q")),
    "export": KeyBinding(("e", "E")),
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

LABEL_KEYS: dict[str, str] = {
    "quit": "binding.quit",
    "export": "binding.export",
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
    "export": "tooltip.export",
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
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f10": "F10",
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


APP_FUNCTION_KEYS: dict[str, KeyBinding] = {
    "ticket_report": KeyBinding(("f7", "b", "B")),
    "manual_entry": KeyBinding(("f8", "m", "M")),
    "toggle_anon": KeyBinding(("f9", "a", "A")),
    "export": KeyBinding(("f10", "e", "E")),
}
"""Die F-Tasten, die diese Anwendung selbst vergibt.

`f1` bis `f6` kommen aus der gemeinsamen Konvention. Ab `f7` haengt es davon
ab, was die Anwendung kann - hier die vier haeufigsten fachlichen Aktionen:
erst ansehen (Analyse), dann erfassen, dann anonymisieren, dann ausgeben.

`export` hatte bis dahin zwei Tasten, `f9` fuer Excel und `f10` fuer PDF.
Beide oeffneten denselben Dialog - das Format gehoert dort hinein und nicht
auf die Taste. Die frei gewordene `f9` bekommt `toggle_anon`: die Aktion wird
vor jedem Screenshot gebraucht, und genau dann sucht man keine Buchstabentaste.

Damit ist die Reihe f1..f10 voll. Ohne F-Taste bleiben bewusst:

- `tab` Ansicht wechseln und `q` Beenden - beide sind schon eindeutig und in
  allen Anwendungen gleich, eine F-Taste daneben braeuchte niemand.
- `r` Cache zuruecksetzen und `t` Theme - selten gebraucht.
- `f11` und `f12` bleiben frei: viele Terminals und Browser belegen sie selbst
  mit Vollbild.
"""

FUNCTION_KEYS: dict[str, KeyBinding] = {**COMMON_FUNCTION_KEYS, **APP_FUNCTION_KEYS}
"""Die gemeinsame Konvention plus die Ergaenzungen dieser Anwendung."""


def resolve(settings: Any) -> ResolvedKeymap:
    """Baut die fertige Belegung aus den Einstellungen.

    Im F-Tasten-Stil steht das Ergebnis in der Reihenfolge fuer den Footer:
    erst alles mit F-Taste, aufsteigend nach Nummer, danach der Rest. Ohne das
    stuende dort F2 vor F1, weil die Bestandstabelle die Reihenfolge vorgibt.

    Im Bestandsstil wird NICHT sortiert. Dort haette nur `refresh` eine
    F-Taste, und die allein nach vorn zu ziehen wuerde die gewohnte Reihenfolge
    aendern, ohne dass jemand etwas davon haette.

    Args:
        settings: Die geladenen Einstellungen.

    Returns:
        Die Belegung samt Beanstandungen. Die Beanstandungen gehoeren ins Log,
        nicht in einen Dialog - sie betreffen die Einstellungsdatei, nicht den
        laufenden Vorgang.
    """

    stil = style_from_settings(settings)
    overrides, probleme = parse_overrides(getattr(settings, "keymap_custom", None))
    ergebnis = resolve_keymap(
        stil,
        CLASSIC,
        function_keys=FUNCTION_KEYS,
        overrides=overrides,
        vim_navigation=bool(getattr(settings, "keymap_vim", False)),
    )
    if stil is not KeymapStyle.FUNCTION_KEYS:
        return ResolvedKeymap(bindings=ergebnis.bindings, problems=probleme + ergebnis.problems)
    return ResolvedKeymap(
        bindings=sort_for_footer(ergebnis.bindings),
        problems=probleme + ergebnis.problems,
    )
