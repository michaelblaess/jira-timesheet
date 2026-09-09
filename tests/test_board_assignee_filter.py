"""Tests fuer den Bearbeiterfilter in "Meine Aktivitaeten".

Die Ansicht zeigt Tickets, an denen man beteiligt ist - bearbeitet werden sie
oft von jemand anderem. Ohne Filter ueber die Bearbeiter-Spalte laesst sich
daraus nicht herausloesen, was bei einer bestimmten Person liegt.

Alle Zeitpunkte sind fest verdrahtet, damit die Tests nicht am Kalender
haengen.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from textual.app import App, ComposeResult
from textual.pilot import Pilot
from textual.widgets import DataTable, Select

from jira_timesheet.i18n import load_locale, t
from jira_timesheet.services.ticket_board import Board, BoardConfig, build_board
from jira_timesheet.services.ticket_board_loader import MODE_ASSIGNED, MODE_RELEVANT, MODE_TEAM
from jira_timesheet.widgets.ticket_board_table import TicketBoardTable

NOW = dt.datetime(2026, 9, 9, 10, 0, tzinfo=dt.UTC)
ACCOUNT = "ich-selbst"

CONFIG = BoardConfig(
    active_status=("In Arbeit",),
    backlog_status=("Bereit",),
    handback_status=("Warten",),
    acceptance_status=("Abnahme",),
    closing_status=("Abschluss",),
)


@pytest.fixture(autouse=True)
def _german_labels() -> None:
    """Echte Beschriftungen laden - sonst stehen die i18n-Schluessel im Filter."""
    load_locale("de")


def _stamp(moment: dt.datetime) -> str:
    """Formatiert einen Zeitpunkt so, wie Jira ihn liefert."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000%z")


def _issue(key: str, bearbeiter: str | None) -> dict[str, Any]:
    """Baut eine Suchantwort-Zeile mit dem gewuenschten Bearbeiter.

    Args:
        key: Der Ticketschluessel.
        bearbeiter: Der angezeigte Name, oder None fuer ein Ticket ohne Bearbeiter.

    Returns:
        Die Zeile, wie Jira sie in der Suche liefert.
    """

    zuweisung = None if bearbeiter is None else {"accountId": bearbeiter, "displayName": bearbeiter}
    return {
        "key": key,
        "fields": {
            "summary": f"Titel zu {key}",
            "status": {"name": "In Arbeit", "statusCategory": {"key": "indeterminate"}},
            "priority": {"name": "Mittel"},
            "issuetype": {"name": "Story"},
            "reporter": {"accountId": ACCOUNT, "displayName": "Ich Selbst"},
            "assignee": zuweisung,
            "created": _stamp(NOW - dt.timedelta(days=400)),
            "updated": _stamp(NOW - dt.timedelta(days=2)),
            "issuelinks": [],
        },
    }


def _board() -> Board:
    """Ein Board mit drei Bearbeitern und einem Ticket ohne Bearbeiter."""
    return build_board(
        [
            _issue("PROJ-1", "Platzhalter, Paula"),
            _issue("PROJ-2", "Platzhalter, Paula"),
            _issue("PROJ-3", "Beispiel, Bruno"),
            _issue("PROJ-4", None),
        ],
        CONFIG,
        NOW,
        account_id=ACCOUNT,
        browse_base="https://beispiel.atlassian.net",
    )


class _BoardApp(App[None]):
    """Minimal-App, die nur die Ticket-Tabelle einer Ansicht zeigt."""

    def __init__(self, mode: str = MODE_RELEVANT) -> None:
        super().__init__()
        self._mode = mode

    def compose(self) -> ComposeResult:
        yield TicketBoardTable(
            self._mode,
            jira_host="https://beispiel.atlassian.net",
            id=f"board-{self._mode}",
        )


def _sichtbare_tickets(app: _BoardApp, mode: str = MODE_RELEVANT) -> list[str]:
    """Liest die Ticketschluessel der sichtbaren Zeilen, ohne Gruppenzeilen.

    Args:
        app: Die laufende Traegeranwendung.
        mode: Die Ansicht, deren Tabelle gelesen wird.

    Returns:
        Die Ticketschluessel in der Reihenfolge der Anzeige.
    """

    table: DataTable[Any] = app.query_one(f"#board-data-{mode}", DataTable)
    schluessel = []
    for index in range(table.row_count):
        erste = str(table.get_row_at(index)[0])
        if "PROJ-" in erste:
            schluessel.append(erste.strip())
    return schluessel


async def _filter_setzen(pilot: Pilot[None], wert: str) -> None:
    """Stellt den Bearbeiterfilter auf einen Wert und laesst die Tabelle neu bauen.

    Args:
        pilot: Der Pilot der laufenden Traegeranwendung.
        wert: Der Wert des Filtereintrags.
    """

    auswahl: Select[Any] = pilot.app.query_one(f"#board-assignee-{MODE_RELEVANT}", Select)
    auswahl.value = wert
    await pilot.pause()


async def test_filter_erscheint_nur_in_meine_aktivitaeten() -> None:
    for mode, erwartet in ((MODE_RELEVANT, 1), (MODE_ASSIGNED, 0), (MODE_TEAM, 0)):
        app = _BoardApp(mode)
        async with app.run_test() as pilot:
            await pilot.pause()
            gefunden = len(app.query(f"#board-assignee-{mode}"))
            assert gefunden == erwartet, f"{mode}: {gefunden} Bearbeiterfilter"


async def test_optionen_kommen_aus_den_tatsaechlichen_tickets() -> None:
    app = _BoardApp()
    async with app.run_test() as pilot:
        app.query_one(TicketBoardTable).set_board(_board())
        await pilot.pause()

        auswahl: Select[Any] = app.query_one(f"#board-assignee-{MODE_RELEVANT}", Select)
        beschriftungen = [str(label) for label, _wert in auswahl._options]
        # Die Namen stehen alphabetisch, "alle" davor und "ohne Bearbeiter"
        # dahinter - beide sind keine Namen und gehoeren nicht in die Sortierung.
        assert beschriftungen == [
            t("board.filter.all"),
            "Beispiel, Bruno",
            "Platzhalter, Paula",
            t("board.filter.no_assignee"),
        ]


async def test_ohne_unzugewiesene_tickets_fehlt_der_eintrag() -> None:
    # Ein Filtereintrag, der garantiert nichts findet, hilft niemandem.
    app = _BoardApp()
    async with app.run_test() as pilot:
        board = build_board(
            [_issue("PROJ-1", "Platzhalter, Paula")],
            CONFIG,
            NOW,
            account_id=ACCOUNT,
            browse_base="https://beispiel.atlassian.net",
        )
        app.query_one(TicketBoardTable).set_board(board)
        await pilot.pause()

        auswahl: Select[Any] = app.query_one(f"#board-assignee-{MODE_RELEVANT}", Select)
        beschriftungen = [str(label) for label, _wert in auswahl._options]
        assert t("board.filter.no_assignee") not in beschriftungen


async def test_auswahl_einer_person_blendet_die_anderen_aus() -> None:
    app = _BoardApp()
    async with app.run_test() as pilot:
        app.query_one(TicketBoardTable).set_board(_board())
        await pilot.pause()
        assert _sichtbare_tickets(app) == ["PROJ-1", "PROJ-2", "PROJ-3", "PROJ-4"]

        await _filter_setzen(pilot, "Platzhalter, Paula")
        assert _sichtbare_tickets(app) == ["PROJ-1", "PROJ-2"]

        await _filter_setzen(pilot, "Beispiel, Bruno")
        assert _sichtbare_tickets(app) == ["PROJ-3"]


async def test_ohne_bearbeiter_findet_genau_die_unzugewiesenen() -> None:
    app = _BoardApp()
    async with app.run_test() as pilot:
        app.query_one(TicketBoardTable).set_board(_board())
        await pilot.pause()

        auswahl: Select[Any] = app.query_one(f"#board-assignee-{MODE_RELEVANT}", Select)
        ohne = [wert for label, wert in auswahl._options if str(label) == t("board.filter.no_assignee")]
        await _filter_setzen(pilot, str(ohne[0]))
        assert _sichtbare_tickets(app) == ["PROJ-4"]


async def test_zurueck_auf_alle_zeigt_wieder_alles() -> None:
    app = _BoardApp()
    async with app.run_test() as pilot:
        app.query_one(TicketBoardTable).set_board(_board())
        await pilot.pause()
        await _filter_setzen(pilot, "Platzhalter, Paula")

        auswahl: Select[Any] = app.query_one(f"#board-assignee-{MODE_RELEVANT}", Select)
        alle = [wert for label, wert in auswahl._options if str(label) == t("board.filter.all")]
        await _filter_setzen(pilot, str(alle[0]))
        assert _sichtbare_tickets(app) == ["PROJ-1", "PROJ-2", "PROJ-3", "PROJ-4"]


async def test_verschwundene_person_faellt_auf_alle_zurueck() -> None:
    # Nach dem Neuladen kann die gewaehlte Person aus dem Bestand raus sein.
    # Bliebe der Filter stehen, staende die Ansicht ohne erkennbaren Grund leer.
    app = _BoardApp()
    async with app.run_test() as pilot:
        tabelle = app.query_one(TicketBoardTable)
        tabelle.set_board(_board())
        await pilot.pause()
        await _filter_setzen(pilot, "Beispiel, Bruno")
        assert _sichtbare_tickets(app) == ["PROJ-3"]

        neues_board = build_board(
            [_issue("PROJ-1", "Platzhalter, Paula")],
            CONFIG,
            NOW,
            account_id=ACCOUNT,
            browse_base="https://beispiel.atlassian.net",
        )
        tabelle.set_board(neues_board)
        await pilot.pause()

        assert _sichtbare_tickets(app) == ["PROJ-1"]
