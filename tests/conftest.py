"""Shared Test Fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def blockierte_browser_aufrufe(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Haelt jeden Test davon ab, einen echten Browser zu oeffnen.

    Belegt am 06.08.2026 in der Qt-Fassung: der Test des Ticket-Berichts hat
    die geschriebene Datei jedes Mal wirklich aufgemacht - bei jedem Testlauf
    ging ein Browser-Tab auf eine Datei im pytest-Temp-Verzeichnis auf. Hier
    steht derselbe Aufruf (app.py, _do_write_ticket_report), also dieselbe
    Sperre.

    Die Sperre liegt bewusst in der conftest und nicht im einzelnen Test: ein
    neuer Test, der wieder ueber webbrowser geht, ist damit von vornherein
    abgedeckt. Wer den Aufruf pruefen will, laesst sich die Fixture geben -
    sie sammelt die Ziele.
    """
    import webbrowser

    ziele: list[str] = []

    def _merken(target: object, *_args: object, **_kwargs: object) -> bool:
        ziele.append(str(target))
        return True

    monkeypatch.setattr(webbrowser, "open", _merken)
    return ziele
