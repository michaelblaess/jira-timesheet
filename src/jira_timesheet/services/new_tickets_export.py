"""Die neuen Tickets als JSON - der Ausgang fuer andere Programme.

Der Reiter "Neue Tickets" zeigt die Liste in der Oberflaeche. Dieses Modul
liefert dieselbe Liste ohne Oberflaeche, damit ein anderes Werkzeug (eine
Statuszeile, ein Mod, ein Skript) sie anzeigen kann, ohne selbst mit Jira zu
sprechen und ohne die Zugangsdaten zu kennen.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from jira_timesheet.i18n import t
from jira_timesheet.models.settings import Settings
from jira_timesheet.services.jira_client import JiraClientError
from jira_timesheet.services.new_tickets import DEFAULT_WINDOW, WINDOWS, window_start
from jira_timesheet.services.team import from_storage
from jira_timesheet.services.ticket_board import AccountIdError, Ticket
from jira_timesheet.services.ticket_board_loader import config_from, load_new_tickets

# Version des Formats. Wer die Ausgabe liest, kann daran erkennen, ob er sie versteht.
FORMAT = 1


def default_workdays(settings: Settings) -> int:
    """Der in der Oberflaeche zuletzt gewaehlte Zeitraum, in Arbeitstagen."""
    return WINDOWS.get(settings.new_tickets_window, WINDOWS[DEFAULT_WINDOW])


def ticket_to_dict(ticket: Ticket) -> dict[str, str]:
    """Die Felder eines Tickets, die eine Liste braucht - alles als Text.

    Args:
        ticket:
            Das Ticket aus der Auswertung.

    Returns:
        Schluessel, Titel, Typ, Prioritaet, Status, Ersteller, Bearbeiter,
        Anlagezeitpunkt (ISO 8601, leer wenn unbekannt) und Adresse.
    """
    return {
        "key": ticket.key,
        "summary": ticket.summary,
        "type": ticket.issue_type,
        "priority": ticket.priority,
        "status": ticket.status,
        "reporter": ticket.reporter,
        "assignee": ticket.assignee,
        "created": ticket.created.isoformat() if ticket.created else "",
        "url": ticket.url,
    }


def _failure(code: str, message: str) -> dict[str, Any]:
    """Ein gescheiterter Abruf: Kennung fuer Programme, Text fuer Menschen."""
    return {"format": FORMAT, "error": code, "message": message, "tickets": []}


async def export_new_tickets(settings: Settings, workdays: int, today: dt.date | None = None) -> dict[str, Any]:
    """Holt die neuen Tickets der Merkliste und liefert sie als einfache Struktur.

    Wirft nicht: jeder Ausgang, auch ein gescheiterter, ist eine gueltige
    Antwort mit eigener Kennung. Der Aufrufer muss nichts abfangen und kann
    den Grund trotzdem unterscheiden.

    Args:
        settings:
            Zugang, Host und Merkliste.
        workdays:
            Wie viele Arbeitstage zurueck, heute zaehlt zusaetzlich.
        today:
            Der Bezugstag, None nimmt das heutige Datum.

    Returns:
        ``{"format", "since", "tickets"}`` im Erfolgsfall, sonst zusaetzlich
        ``error`` (settings, team, account oder jira) und ``message``.
    """
    if not (settings.jira_host and settings.jira_token and settings.email):
        return _failure("settings", t("board.needs_settings"))
    members = [member for member in from_storage(settings.team_members).members if member.account_ids]
    if not members:
        return _failure("team", t("new.needs_team"))

    since = window_start(today or dt.date.today(), workdays)
    try:
        tickets = await load_new_tickets(settings, config_from(settings), members, since)
    except AccountIdError:
        return _failure("account", t("new.bad_account"))
    except JiraClientError as exc:
        return _failure("jira", t("new.failed", error=str(exc)))
    except Exception as exc:  # noqa: BLE001 - der Ausgang liefert immer JSON, nie einen Traceback
        return _failure("jira", t("new.failed", error=f"{type(exc).__name__}: {exc}"))

    return {
        "format": FORMAT,
        "since": since.isoformat(),
        "tickets": [ticket_to_dict(ticket) for ticket in tickets],
    }
