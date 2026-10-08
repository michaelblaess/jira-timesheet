"""Tests fuer den JSON-Ausgang der neuen Tickets - ohne Oberflaeche, ohne Netz."""

from __future__ import annotations

import datetime as dt
from typing import Any
from unittest import mock

from jira_timesheet.models.settings import Settings
from jira_timesheet.services import new_tickets_export
from jira_timesheet.services.jira_client import JiraClientError
from jira_timesheet.services.new_tickets_export import (
    FORMAT,
    default_workdays,
    export_new_tickets,
    ticket_to_dict,
)
from jira_timesheet.services.ticket_board import AccountIdError, Ticket

ANNA_ID = "712020:aaaaaaaa-0000-0000-0000-000000000001"
# Dienstag, 22.09.2026 - der Vortag ist ein Montag.
TUESDAY = dt.date(2026, 9, 22)

TICKET = Ticket(
    key="ABC-7",
    summary="Zähler läuft über",
    status="Offen",
    priority="High",
    issue_type="Bug",
    reporter="Anna",
    assignee="",
    created=dt.datetime(2026, 9, 22, 8, 30, tzinfo=dt.UTC),
    url="https://jira.example.com/browse/ABC-7",
)


def complete_settings(**changes: Any) -> Settings:
    """Einstellungen mit Zugang und einer Person in der Merkliste."""
    settings = Settings(
        jira_host="https://jira.example.com",
        jira_token="geheim",
        email="anna@example.com",
        team_members=[{"display_name": "Anna", "account_ids": [ANNA_ID]}],
    )
    for name, value in changes.items():
        setattr(settings, name, value)
    return settings


def test_ticket_to_dict_liefert_nur_text() -> None:
    """Alle Felder sind Text, der Anlagezeitpunkt steht in ISO 8601."""
    row = ticket_to_dict(TICKET)

    assert row == {
        "key": "ABC-7",
        "summary": "Zähler läuft über",
        "type": "Bug",
        "priority": "High",
        "status": "Offen",
        "reporter": "Anna",
        "assignee": "",
        "created": "2026-09-22T08:30:00+00:00",
        "url": "https://jira.example.com/browse/ABC-7",
    }
    assert ticket_to_dict(Ticket(key="ABC-8"))["created"] == ""


def test_default_workdays_folgt_dem_gewaehlten_zeitraum() -> None:
    """Der zuletzt gewaehlte Zeitraum gilt, ein unbekannter faellt auf einen Tag."""
    assert default_workdays(complete_settings(new_tickets_window="3T")) == 3
    assert default_workdays(complete_settings(new_tickets_window="kaputt")) == 1


async def test_ohne_zugang_kommt_die_kennung_settings() -> None:
    """Fehlende Zugangsdaten sind ein eigener Ausgang, kein Netzverkehr."""
    result = await export_new_tickets(complete_settings(jira_token=""), 1, TUESDAY)

    assert result["error"] == "settings"
    assert result["tickets"] == []
    assert result["message"]


async def test_ohne_merkliste_kommt_die_kennung_team() -> None:
    """Eine leere Merkliste ist ein eigener Ausgang."""
    result = await export_new_tickets(complete_settings(team_members=[]), 1, TUESDAY)

    assert result["error"] == "team"


async def test_erfolg_liefert_zeitraum_und_tickets() -> None:
    """Der Abruf reicht bis zum Montag zurueck und liefert die Tickets als Text."""
    loader = mock.AsyncMock(return_value=[TICKET])
    with mock.patch.object(new_tickets_export, "load_new_tickets", loader):
        result = await export_new_tickets(complete_settings(), 1, TUESDAY)

    assert result == {"format": FORMAT, "since": "2026-09-21", "tickets": [ticket_to_dict(TICKET)]}
    assert loader.await_args is not None
    assert loader.await_args.args[3] == dt.date(2026, 9, 21)
    assert [member.display_name for member in loader.await_args.args[2]] == ["Anna"]


async def test_fehler_des_abrufs_werden_zu_kennungen() -> None:
    """Kein Ausgang wirft: Jira-Fehler, kaputte Kennung und alles andere liefern JSON."""
    cases: list[tuple[Exception, str]] = [
        (JiraClientError("HTTP 401"), "jira"),
        (AccountIdError("kaputt"), "account"),
        (RuntimeError("unerwartet"), "jira"),
    ]
    for error, code in cases:
        with mock.patch.object(new_tickets_export, "load_new_tickets", mock.AsyncMock(side_effect=error)):
            result = await export_new_tickets(complete_settings(), 1, TUESDAY)

        assert result["error"] == code
        assert result["tickets"] == []
