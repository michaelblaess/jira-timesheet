"""Tests fuer den Umfang von F5.

Michael hat am 04.09.2026 gemeldet: wer in "Meine Tickets" aktualisiert und
danach auf den Stundenzettel wechselt, sieht dort den alten Stand und muss ein
zweites Mal F5 druecken. Der Stundenzettel ist der Zweck der Anwendung - er
darf nie alt sein, nur weil gerade eine Ticketliste im Vordergrund stand.

Seither gilt: F5 laedt die sichtbare Ansicht UND immer den Stundenzettel, und
vermerkt alle uebrigen Ansichten als veraltet. Die laden beim naechsten
Hinwechseln von selbst nach - sofort mitzuziehen waere teuer und meist umsonst.

Die Tests halten beide Haelften fest, dazu die zwei Dinge, die ein Abruf im
Hintergrund NICHT anfassen darf: die Kennzahlen-Leiste der sichtbaren Ansicht
und eine eingeschaltete Anonymisierung.
"""

from __future__ import annotations

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
from jira_timesheet.services.ticket_board import Board, Group, Role, Ticket
from jira_timesheet.services.ticket_board_loader import MODE_ASSIGNED, MODE_RELEVANT
from jira_timesheet.widgets.summary_panel import SummaryPanel

# Reissleine, keine erwartete Dauer: wird sie erreicht, haengt etwas.
_GEDULD_SECONDS = 10.0


class FakeJiraClient:
    """Zaehlt die Monatsabrufe mit und liefert sofort eine leere Antwort."""

    calls: list[tuple[date, date]] = []

    def __init__(self, **kwargs: Any) -> None:
        pass

    @classmethod
    def reset(cls) -> None:
        cls.calls = []

    async def get_worklogs(self, date_from: date, date_to: date) -> list[Any]:
        FakeJiraClient.calls.append((date_from, date_to))
        return []


def _board() -> Board:
    """Ein Board mit genau einem Ticket - mehr braucht es hier nicht."""
    ticket = Ticket(key="PROJ-1", summary="Irgendein Titel", status="In Arbeit")
    gruppe = Group(role=Role.ACTIVE, tickets=[ticket])
    return Board(groups=[gruppe], tickets=[ticket])


async def _warte_bis(pilot: Any, bedingung: Callable[[], bool], was: str) -> None:
    """Wartet auf einen ZUSTAND statt auf eine Zeitspanne."""
    grenze = time.monotonic() + _GEDULD_SECONDS
    while not bedingung():
        if time.monotonic() > grenze:
            raise AssertionError(f"{was} - nach {_GEDULD_SECONDS} s nicht eingetreten")
        await pilot.pause()


async def _beruhigen(pilot: Any) -> None:
    """Mehrere Durchlaeufe ohne Wartezeit - fuer "kommt da noch etwas?"."""
    for _ in range(20):
        await pilot.pause()


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt Einstellungen, Cache und Datenbank nach tmp_path."""
    load_locale("de")
    monkeypatch.setattr(Settings, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(Settings, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(cache_service, "CACHE_DIR", tmp_path / "cache")
    FakeJiraClient.reset()
    return tmp_path


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> JiraTimesheetApp:
    """Startklare App mit vorgetaeuschtem Jira-Zugang und Ticket-Abruf."""
    monkeypatch.setattr("jira_timesheet.app.JiraClient", FakeJiraClient)
    monkeypatch.setattr(JiraTimesheetApp, "_ask_disclaimer", lambda self: None)

    async def fake_load_board(*args: Any, **kwargs: Any) -> Board:
        return _board()

    monkeypatch.setattr("jira_timesheet.app.load_board", fake_load_board)

    instance = JiraTimesheetApp()
    instance._settings.jira_host = "https://example.atlassian.net"
    instance._settings.email = "test@example.com"
    instance._settings.jira_token = "geheim"
    return instance


async def _bis_zum_ticket_reiter(app: JiraTimesheetApp, pilot: Any) -> None:
    """Startabruf abwarten, auf "Meine Tickets" wechseln, Zaehler leeren.

    Das Beruhigen VOR dem Wechsel ist Pflicht: solange der Aufbau laeuft,
    stellt Textual den ersten Reiter wieder in den Vordergrund. Gemessen -
    der Wechsel wirkte, und nach dem naechsten Durchlauf stand wieder
    "tab-list" vorn. Der Test haette dann geprueft, was auf dem
    Stundenzettel passiert, und geglaubt, er stehe in der Ticketliste.
    """
    await _warte_bis(pilot, lambda: len(FakeJiraClient.calls) >= 1, "der Startabruf laeuft")
    await _beruhigen(pilot)
    app.query_one("#view-tabs").active = "tab-assigned"
    await _warte_bis(
        pilot,
        lambda: app._board_widget(MODE_ASSIGNED).board is not None,
        "die Ticketliste ist geladen",
    )
    assert app._active_tab() == "tab-assigned", "der Reiter steht nicht vorn"
    FakeJiraClient.calls.clear()


class TestUmfangVonF5:
    """F5 laedt die sichtbare Ansicht und immer den Stundenzettel."""

    async def test_auf_der_ticketliste_wird_der_stundenzettel_mitgeladen(
        self, app: JiraTimesheetApp
    ) -> None:
        """Der gemeldete Fall: sonst steht auf dem Stundenzettel der alte Stand."""
        async with app.run_test() as pilot:
            await _bis_zum_ticket_reiter(app, pilot)

            app.action_refresh()
            await _warte_bis(
                pilot,
                lambda: len(FakeJiraClient.calls) >= 1,
                "der Stundenzettel wird im Hintergrund abgerufen",
            )

    async def test_die_uebrigen_ansichten_gelten_danach_als_veraltet(
        self, app: JiraTimesheetApp
    ) -> None:
        """Sie laden beim naechsten Hinwechseln - nicht sofort, das kostet Minuten."""
        async with app.run_test() as pilot:
            await _bis_zum_ticket_reiter(app, pilot)
            app._year_loaded_for = 2026

            app.action_refresh()
            await _beruhigen(pilot)

            # Die sichtbare Ansicht wurde geladen, die anderen nur vermerkt.
            assert app._board_loaded[MODE_ASSIGNED] is True
            assert app._board_loaded[MODE_RELEVANT] is False
            assert app._year_loaded_for is None

    async def test_auf_dem_stundenzettel_wird_er_nur_einmal_geladen(
        self, app: JiraTimesheetApp
    ) -> None:
        """Steht er im Vordergrund, ist er die aktive Ansicht - kein zweiter Abruf."""
        async with app.run_test() as pilot:
            await _warte_bis(
                pilot, lambda: len(FakeJiraClient.calls) >= 1, "der Startabruf laeuft"
            )
            FakeJiraClient.calls.clear()

            app.action_refresh()
            await _beruhigen(pilot)

            assert len(FakeJiraClient.calls) == 1


class TestHintergrundlaufHaeltSichZurueck:
    """Ein Abruf im Hintergrund darf die sichtbare Ansicht nicht anfassen."""

    async def test_die_kennzahlen_der_ticketliste_bleiben_stehen(
        self, app: JiraTimesheetApp
    ) -> None:
        """Sonst zucken dem Anwender die Zahlen unter den Haenden weg."""
        async with app.run_test() as pilot:
            await _bis_zum_ticket_reiter(app, pilot)
            panel = app.query_one("#summary-panel", SummaryPanel)
            vorher = list(panel._items)

            app.action_refresh()
            await _beruhigen(pilot)

            assert list(panel._items) == vorher

    async def test_die_anonymisierung_bleibt_eingeschaltet(
        self, app: JiraTimesheetApp
    ) -> None:
        """Sie hinter dem Ruecken abzuschalten waere ein Leck: die Ansicht bliebe
        zensiert gezeichnet, das Kennzeichen stuende auf "echt", und der naechste
        Neuaufbau zeigte die echten Werte."""
        async with app.run_test() as pilot:
            await _bis_zum_ticket_reiter(app, pilot)
            app.action_toggle_anon()
            assert app._anonymized is True

            app.action_refresh()
            await _warte_bis(
                pilot, lambda: len(FakeJiraClient.calls) >= 1, "der Abruf laeuft an"
            )
            await _beruhigen(pilot)

            assert app._anonymized is True
