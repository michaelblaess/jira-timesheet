"""Tests fuer den Zeitraum-Wechsel waehrend eines laufenden Abrufs.

Hintergrund (gemeldet 04.08.2026, macOS, langsame Verbindung): Wer den Monat
wechselt, waehrend noch abgerufen wird, bekam eine Oberflaeche, die auf nichts
mehr reagierte - das Protokoll endete mitten im Abruf, die Tabelle blieb leer,
und auch ein erneutes Generieren tat nichts mehr.

Ursache war das Zusammenspiel zweier Mechanismen: @work(exclusive=True) bricht
den laufenden Worker ab, der Abbruch wirkt in asyncio aber erst verzoegert.
Ein zusaetzlicher Guard auf einem selbst gepflegten "laeuft gerade"-Flag hat
deshalb den NEUEN Lauf verworfen, waehrend der alte noch aufraeumte: Der alte
Abruf war abgebrochen, ein neuer nie gestartet. Kam der Abbruch bei haengender
Verbindung gar nicht durch, blieb das Flag stehen und sperrte jeden weiteren
Versuch dauerhaft.

Die Tests halten fest, dass ein zweiter Auslauf tatsaechlich startet, dass das
Flag nicht haengen bleibt und dass schnelles Blaettern nur einen Abruf ausloest.
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import load_locale
from jira_timesheet.models.settings import Settings
from jira_timesheet.services import cache_service
from jira_timesheet.services.manual_entry_service import ManualEntryService

# Laufzeit eines vorgetaeuschten Abrufs. Lang genug, dass ein zweiter Auslauf
# zuverlaessig mitten hinein faellt, kurz genug fuer eine flotte Testsuite.
_FETCH_SECONDS = 0.4

# Dauer des Aufraeumens nach einem Abbruch. Ein abgebrochener HTTP-Aufruf ist
# nicht sofort verschwunden: httpx baut die Verbindung noch ab (TLS-Shutdown),
# und dieses Aufraeumen gibt die Kontrolle an den Event-Loop zurueck. Genau in
# diesem Fenster startet der Nachfolger und sah frueher das noch gesetzte
# Laufzeichen. Ohne diese Nachbildung ist der Test wertlos - er war zunaechst
# auch mit wieder eingebautem Guard gruen.
_CLEANUP_SECONDS = 0.2


class FakeJiraClient:
    """Ersetzt den echten Client durch einen langsamen, mitzaehlenden Ersatz."""

    started: list[tuple[date, date]] = []
    completed: list[tuple[date, date]] = []

    def __init__(self, **kwargs: Any) -> None:
        pass

    @classmethod
    def reset(cls) -> None:
        cls.started = []
        cls.completed = []

    async def get_worklogs(self, date_from: date, date_to: date) -> list[Any]:
        FakeJiraClient.started.append((date_from, date_to))
        try:
            await asyncio.sleep(_FETCH_SECONDS)
        except asyncio.CancelledError:
            # Verbindungsabbau nach dem Abbruch - siehe _CLEANUP_SECONDS.
            await asyncio.sleep(_CLEANUP_SECONDS)
            raise
        FakeJiraClient.completed.append((date_from, date_to))
        return []


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt Einstellungen, Cache und Datenbank nach tmp_path.

    Ohne das schreiben die Tests in die echte ~/.jira-timesheet - inklusive
    Cache-Dateien und Zugangsdaten des Entwicklers.
    """
    load_locale("de")
    monkeypatch.setattr(Settings, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(Settings, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(ManualEntryService, "db_path", tmp_path / "manual-entries.db")
    monkeypatch.setattr(cache_service, "CACHE_DIR", tmp_path / "cache")
    FakeJiraClient.reset()
    return tmp_path


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> JiraTimesheetApp:
    """Eine startklare App mit vorgetaeuschtem Jira-Zugang."""
    monkeypatch.setattr("jira_timesheet.app.JiraClient", FakeJiraClient)
    # Der Haftungshinweis wuerde den Start blockieren - hier nicht das Thema.
    monkeypatch.setattr(JiraTimesheetApp, "_ask_disclaimer", lambda self: None)

    instance = JiraTimesheetApp()
    instance._settings.jira_host = "https://example.atlassian.net"
    instance._settings.email = "test@example.com"
    instance._settings.jira_token = "geheim"
    return instance


async def test_second_run_starts_while_first_is_still_fetching(
    app: JiraTimesheetApp,
) -> None:
    """Der Kernfall: ein Zeitraumwechsel mitten im Abruf startet wirklich neu.

    Vor dem Fix prallte der zweite Lauf am Guard ab - der erste war zu diesem
    Zeitpunkt bereits abgebrochen. Ergebnis: gar kein laufender Abruf mehr.
    """
    async with app.run_test() as pilot:
        await pilot.pause()

        app._generate(force_refresh=True)
        await pilot.pause(_FETCH_SECONDS / 4)
        assert len(FakeJiraClient.started) == 1, "erster Abruf laeuft nicht an"

        # Das ist der Zeitraumwechsel: zweiter Auslauf, waehrend der erste haengt.
        app._generate(force_refresh=True)
        await pilot.pause(_FETCH_SECONDS * 2)

        assert len(FakeJiraClient.started) == 2, (
            "der zweite Abruf wurde verworfen - der Anwender sieht eine App, "
            "die auf den Zeitraumwechsel nicht mehr reagiert"
        )
        assert len(FakeJiraClient.completed) == 1, (
            "genau ein Abruf darf durchlaufen - der abgebrochene nicht"
        )


async def test_running_flag_is_released_after_cancellation(
    app: JiraTimesheetApp,
) -> None:
    """Nach Abbruch und Nachfolger darf das Laufzeichen nicht haengen bleiben.

    Bleibt es stehen, sperrt es jeden weiteren Abruf - genau das machte die
    Anwendung auf dem Rechner der Kollegin unbenutzbar.
    """
    async with app.run_test() as pilot:
        await pilot.pause()

        app._generate(force_refresh=True)
        await pilot.pause(_FETCH_SECONDS / 4)
        app._generate(force_refresh=True)
        await pilot.pause(_FETCH_SECONDS * 2)

        assert app._generating is False, "Laufzeichen haengt - Abrufe bleiben gesperrt"


async def test_fast_month_navigation_triggers_only_one_fetch(
    app: JiraTimesheetApp,
) -> None:
    """Drei Tastendruecke am Stueck ergeben einen Abruf, nicht drei."""
    async with app.run_test() as pilot:
        await pilot.pause()

        app.action_prev_month()
        app.action_prev_month()
        app.action_prev_month()
        await pilot.pause(_FETCH_SECONDS * 3)

        assert len(FakeJiraClient.started) == 1, (
            f"erwartet: 1 Abruf nach dem Blaettern, tatsaechlich "
            f"{len(FakeJiraClient.started)}"
        )
