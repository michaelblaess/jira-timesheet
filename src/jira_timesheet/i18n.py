"""Internationalisierung ueber JSON-Sprachpakete.

Public API:
    - `load_locale(lang)` — laedt ein Sprachpaket (muss vor App-Import laufen).
    - `t(key, **kwargs)` — uebersetzt einen Schluessel, optional mit Platzhaltern.
    - `current_language()` — gibt die aktuell geladene Sprache zurueck.
    - `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE` — Konstanten.

Die Sprachpakete liegen als flache JSON-Dateien mit Punkt-Notation-Keys unter
`locale/`. `load_locale()` MUSS vor dem Import der App-Klasse aufgerufen werden,
damit `t()`-Aufrufe auf Modul-Ebene (z.B. Wochentags-Listen) bereits Strings
liefern.
"""

from __future__ import annotations

import json
import logging
from importlib import resources

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "de"

_strings: dict[str, str] = {}
_current_lang: str = DEFAULT_LANGUAGE


def load_locale(lang: str) -> None:
    """Laedt ein Sprachpaket.

    Args:
        lang:
            Sprachkuerzel ('de' oder 'en'). Unbekannte Sprachen fallen auf
            `DEFAULT_LANGUAGE` zurueck.
    """
    global _strings, _current_lang

    if lang not in SUPPORTED_LANGUAGES:
        logger.warning("Sprache '%s' nicht unterstuetzt, verwende '%s'", lang, DEFAULT_LANGUAGE)
        lang = DEFAULT_LANGUAGE

    try:
        raw = (resources.files("jira_timesheet") / "locale" / f"{lang}.json").read_text(encoding="utf-8")
        _strings = json.loads(raw)
        _current_lang = lang
    except Exception:
        logger.exception("Fehler beim Laden der Sprachdatei '%s'", lang)
        _strings = {}
        _current_lang = lang


def current_language() -> str:
    """Gibt die aktuell geladene Sprache zurueck."""
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """Uebersetzt einen Schluessel.

    Args:
        key:
            Der Uebersetzungs-Schluessel (Punkt-Notation).
        **kwargs:
            Optionale Platzhalter-Werte fuer `str.format`.

    Returns:
        Den uebersetzten Text. Fehlt der Schluessel, wird der Schluessel selbst
        zurueckgegeben.
    """
    template = _strings.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template
    return template
