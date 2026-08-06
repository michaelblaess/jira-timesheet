"""Shared Test Fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolierte_ablage(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt alles, was die Anwendung dauerhaft speichert, in einen Wegwerf-Ordner.

    Ohne das arbeiten die Tests auf der ECHTEN Ablage in
    ``~/.jira-timesheet``: Einstellungen mit Zugangsdaten, die SQLite der
    manuellen Zeiten, der Worklog-Cache und die Zustimmung zum
    Haftungshinweis. Belegt am 06.08.2026 - nach einem Testlauf standen
    frische ``manual-entries.db-wal``/``-shm`` neben Michaels echter
    Datenbank, weil jeder Test, der die App baut, den ManualEntryService
    oeffnet.

    Zwei Wirkungen auf einmal:

    1. Die echten Daten bleiben unberuehrt. In der Qt-Fassung hat genau
       dieser fehlende Schutz einmal E-Mail und Token in der echten Datei
       geleert (siehe Memory feedback_tests_isolate_real_config).
    2. Die Tests werden vom Zustand des Rechners unabhaengig. Lokal lag eine
       zugestimmte ``disclaimer.json``, auf dem CI-Runner nicht - dort schob
       sich der Haftungshinweis als Screen ueber die App, und
       ``check_action`` lieferte fuer jede Aktion None. Zwei Tests waren
       deshalb lokal gruen und in der CI rot.

    Die Pfade sind Modul- bzw. Klassenkonstanten und muessen einzeln
    umgehaengt werden - ``HOME`` umzubiegen wirkt hier nicht, weil sie beim
    Import festgezurrt werden.
    """
    import json

    from textual_widgets import DISCLAIMER_VERSION

    from jira_timesheet.models.settings import Settings
    from jira_timesheet.services import cache_service, manual_entry_service

    ablage = tmp_path_factory.mktemp("jira-timesheet-home")
    monkeypatch.setattr(Settings, "SETTINGS_DIR", ablage)
    monkeypatch.setattr(Settings, "SETTINGS_FILE", ablage / "settings.json")
    monkeypatch.setattr(manual_entry_service, "DB_DIR", ablage)
    monkeypatch.setattr(manual_entry_service, "DB_FILE", ablage / "manual-entries.db")
    monkeypatch.setattr(cache_service, "CACHE_DIR", ablage / "cache")

    # Zustimmung vorschreiben, damit sich die App wie im Normalbetrieb
    # verhaelt. Ohne sie liegt der Haftungshinweis als Screen obenauf und
    # blockiert jede Pruefung am Hauptfenster. Die Fassung kommt aus der
    # Bibliothek - eine fest eingetragene Zahl waere beim naechsten
    # Textwechsel still wirkungslos.
    (ablage / "disclaimer.json").write_text(
        json.dumps({"accepted_version": DISCLAIMER_VERSION}),
        encoding="utf-8",
    )
    return ablage


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
