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
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import load_locale
from jira_timesheet.models.settings import Settings
from jira_timesheet.services import cache_service
from jira_timesheet.services.manual_entry_service import ManualEntryService

# Obergrenze fuer jedes Warten. Sie ist KEINE erwartete Dauer, sondern eine
# Reissleine: wird sie erreicht, haengt etwas, und der Test soll das melden
# statt die Suite anzuhalten.
_GEDULD_SECONDS = 10.0

# Dauer des Aufraeumens nach einem Abbruch. Ein abgebrochener HTTP-Aufruf ist
# nicht sofort verschwunden: httpx baut die Verbindung noch ab (TLS-Shutdown),
# und dieses Aufraeumen gibt die Kontrolle an den Event-Loop zurueck. Genau in
# diesem Fenster startet der Nachfolger und sah frueher das noch gesetzte
# Laufzeichen. Ohne diese Nachbildung ist der Test wertlos - er war zunaechst
# auch mit wieder eingebautem Guard gruen.
#
# Das ist die EINZIGE Stelle, an der noch echte Zeit steht, und sie ist KEINE
# Testwartezeit, sondern die Nachbildung eines Verhaltens. Sie darf deshalb
# nicht "der Schnelligkeit halber" verkleinert werden: mit 0.05 s war der
# Umbau vom 11.08.2026 zunaechst gruen, obwohl der alte Fehler wieder im Code
# stand - das Fenster war zu klein, als dass der Nachfolger noch hineingefallen
# waere. Die Gegenprobe hat es aufgedeckt.
_CLEANUP_SECONDS = 0.2


class FakeJiraClient:
    """Ersetzt den echten Client durch einen steuerbaren, mitzaehlenden Ersatz.

    Ein Abruf endet NICHT nach einer festen Frist, sondern erst wenn der Test
    ``release`` setzt. Vorher hing der Test an der Uhr: er wartete ein Viertel
    der Abrufdauer und nahm an, dass der Abruf dann noch laeuft. Unter Last
    stimmte das nicht - am 11.08.2026 war die Pause laenger als der Abruf, beide
    Laeufe kamen durch, und der Test meldete einen Fehler, den es nicht gab.
    """

    started: list[tuple[date, date]] = []
    completed: list[tuple[date, date]] = []
    # Wird beim Zuruecksetzen neu erzeugt, damit jeder Test seine eigene
    # Steuerung hat und kein Signal aus dem Vorgaenger uebrig bleibt.
    release: asyncio.Event = asyncio.Event()

    def __init__(self, **kwargs: Any) -> None:
        pass

    @classmethod
    def reset(cls) -> None:
        cls.started = []
        cls.completed = []
        cls.release = asyncio.Event()

    async def get_worklogs(self, date_from: date, date_to: date) -> list[Any]:
        FakeJiraClient.started.append((date_from, date_to))
        try:
            await FakeJiraClient.release.wait()
        except asyncio.CancelledError:
            # Verbindungsabbau nach dem Abbruch - siehe _CLEANUP_SECONDS.
            await asyncio.sleep(_CLEANUP_SECONDS)
            raise
        FakeJiraClient.completed.append((date_from, date_to))
        return []


async def _warte_bis(
    pilot: Any,
    bedingung: Callable[[], bool],
    was: str,
) -> None:
    """Wartet auf einen ZUSTAND statt auf eine Zeitspanne.

    Der entscheidende Unterschied zu ``pilot.pause(sekunden)``: eine Pause
    sagt nur, wie lange gewartet wurde, nicht was inzwischen passiert ist.
    Unter Last dauert sie laenger als gedacht, und der Test prueft einen
    Zwischenstand, den es nie gab.

    Args:
        pilot:
            Der Textual-Pilot der laufenden App.
        bedingung:
            Wird nach jedem Durchlauf des Event-Loops geprueft.
        was:
            Klartext fuer die Fehlermeldung, falls die Geduld reisst.

    Raises:
        AssertionError:
            Wenn die Bedingung binnen _GEDULD_SECONDS nicht eintritt. Das
            heisst: es haengt - und der Test soll das melden, nicht die Suite
            anhalten.
    """
    grenze = time.monotonic() + _GEDULD_SECONDS
    while not bedingung():
        if time.monotonic() > grenze:
            raise AssertionError(f"{was} - nach {_GEDULD_SECONDS} s nicht eingetreten")
        await pilot.pause()


async def _lauf_beruhigen(pilot: Any) -> None:
    """Gibt dem Event-Loop mehrere Durchlaeufe ohne jede Wartezeit.

    Fuer die Frage "kommt da noch etwas?" - etwa ob ein abgebrochener Abruf
    doch noch durchlaeuft. Ein einzelner Durchlauf genuegt dafuer nicht, eine
    feste Pause waere wieder eine Wette auf die Uhr.
    """
    for _ in range(20):
        await pilot.pause()


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
        await _warte_bis(
            pilot, lambda: len(FakeJiraClient.started) == 1, "erster Abruf laeuft an"
        )

        # Das ist der Zeitraumwechsel: zweiter Auslauf, waehrend der erste haengt.
        # Dass er wirklich haengt, ist hier keine Hoffnung mehr, sondern
        # zugesichert - er endet erst auf "release".
        app._generate(force_refresh=True)
        await _warte_bis(
            pilot, lambda: len(FakeJiraClient.started) == 2, "zweiter Abruf laeuft an"
        )

        FakeJiraClient.release.set()
        await _warte_bis(
            pilot, lambda: app._generating is False, "beide Laeufe kommen zur Ruhe"
        )
        await _lauf_beruhigen(pilot)

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
        await _warte_bis(
            pilot, lambda: len(FakeJiraClient.started) == 1, "erster Abruf laeuft an"
        )
        app._generate(force_refresh=True)
        await _warte_bis(
            pilot, lambda: len(FakeJiraClient.started) == 2, "zweiter Abruf laeuft an"
        )

        FakeJiraClient.release.set()
        await _warte_bis(
            pilot, lambda: app._generating is False, "Laufzeichen wird freigegeben"
        )
        await _lauf_beruhigen(pilot)

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

        # Der Entpreller arbeitet mit einem echten Timer - gewartet wird
        # trotzdem darauf, DASS er gefeuert hat, nicht eine geschaetzte Frist.
        await _warte_bis(
            pilot, lambda: len(FakeJiraClient.started) >= 1, "der Entpreller feuert"
        )
        # Und danach: kommt noch etwas nach? Genau das ist die Frage des Tests.
        await _lauf_beruhigen(pilot)
        FakeJiraClient.release.set()
        await _lauf_beruhigen(pilot)

        assert len(FakeJiraClient.started) == 1, (
            f"erwartet: 1 Abruf nach dem Blaettern, tatsaechlich "
            f"{len(FakeJiraClient.started)}"
        )
