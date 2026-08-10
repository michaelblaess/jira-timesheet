"""Verdrahtung zwischen Jira-Client und dem Kern der Ticket-Ansichten.

Der Client kennt die Auswertung nicht, der Kern kennt keinen Client - dieses
Modul bringt beide zusammen und ist die einzige Stelle, die beide Seiten
sieht. Es kennt dafuer keine Oberflaeche: die Funktionen sind gewoehnliche
Coroutinen und melden Zwischenstaende ueber Rueckrufe. So laufen sie in der
TUI ebenso wie in einem Test.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Sequence

from jira_timesheet.models.settings import Settings
from jira_timesheet.services.jira_client import JiraClient
from jira_timesheet.services.team import TeamMember
from jira_timesheet.services.ticket_board import (
    DEFAULT_PRIORITIES,
    FIELDS,
    STATS_FIELDS,
    Board,
    BoardConfig,
    Role,
    Statistics,
    WorklogInfo,
    assigned_jql,
    build_board,
    build_statistics,
    closing_jql,
    history_jql,
    parse_ts,
    pending_worklog_keys,
    relevant_jql,
)

# Die Ansichten. Der Wert wandert in Widget-Kennungen und Log-Zeilen,
# deshalb sind es Zeichenketten und keine Aufzaehlung.
MODE_ASSIGNED = "assigned"
MODE_RELEVANT = "relevant"
MODE_TEAM = "team"

# Ein Rueckruf fuer Log-Zeilen. Nichts tun ist der Normalfall im Test.
Reporter = Callable[[str], None]

# Rueckruf vor dem zweiten, teuren Durchgang: so viele Tickets werden auf
# ihre Buchungslage geprueft. Bewusst eine Zahl und kein fertiger Satz - der
# Wortlaut gehoert in die Oberflaeche, die uebersetzt.
CountReporter = Callable[[int], None]


def config_from(settings: Settings) -> BoardConfig:
    """Baut die Kern-Konfiguration aus den Benutzereinstellungen.

    Diese Uebersetzung liegt bewusst hier und nicht im Kern: der Kern soll die
    Einstellungen nicht kennen, und die Einstellungen nicht den Kern.

    Args:
        settings:
            Die geladenen Benutzereinstellungen.

    Returns:
        Die Konfiguration fuer den Kern. Nicht gesetzte Schwellen (0) fehlen
        im Ergebnis - diese Rolle erzeugt dann keinen Pile of Shame.
    """
    thresholds: dict[Role, float] = {}
    for role, value in (
        (Role.ACTIVE, settings.board_threshold_active),
        (Role.ACCEPTANCE, settings.board_threshold_acceptance),
        (Role.CLOSING, settings.board_threshold_closing),
    ):
        if value > 0:
            thresholds[role] = float(value)

    return BoardConfig(
        active_status=tuple(settings.board_active_status),
        backlog_status=tuple(settings.board_backlog_status),
        handback_status=tuple(settings.board_handback_status),
        acceptance_status=tuple(settings.board_acceptance_status),
        closing_status=tuple(settings.board_closing_status),
        priorities=(
            tuple(settings.board_priorities)
            if settings.board_priorities
            else DEFAULT_PRIORITIES
        ),
        stale_days=settings.board_stale_days,
        window_days=settings.board_window_days,
        thresholds=thresholds,
    )


def build_client(settings: Settings, on_log: Reporter | None = None) -> JiraClient:
    """Erzeugt den Jira-Client aus den Einstellungen."""
    return JiraClient(
        host=settings.jira_host,
        email=settings.email,
        token=settings.jira_token,
        budget_field=settings.budget_field,
        legacy=settings.use_legacy_api,
        proxy=settings.proxy_url,
        on_log=on_log,
    )


def jqls_for(
    mode: str,
    config: BoardConfig,
    member: TeamMember | None = None,
) -> Callable[[str], Sequence[str]]:
    """Liefert die Ausdruck-Fabrik einer Ansicht.

    Die Ausdruecke kommen als Fabrik statt als fertige Liste, weil der Teil
    "relevant" die eigene accountId braucht - und die steht erst fest, wenn
    die Sitzung offen ist.

    Args:
        mode:
            MODE_ASSIGNED, MODE_RELEVANT oder MODE_TEAM.
        config:
            Die Konfiguration, liefert Zeitfenster und Abschluss-Status.
        member:
            Bei MODE_TEAM die gemeinte Person. Sonst ohne Bedeutung.

    Returns:
        Eine Funktion, die zur accountId die JQL-Ausdruecke baut.

    Raises:
        ValueError:
            Bei MODE_TEAM ohne Person. Ohne Kennung faellt die Abfrage sonst
            auf currentUser() zurueck und zeigte die eigenen Tickets unter
            fremdem Namen an.
    """
    if mode == MODE_TEAM and (member is None or not member.account_ids):
        raise ValueError("MODE_TEAM braucht ein Mitglied mit mindestens einer Kennung")

    ids: Sequence[str] = member.account_ids if mode == MODE_TEAM and member else ()

    def build(account_id: str) -> Sequence[str]:
        if mode == MODE_RELEVANT:
            return [relevant_jql(account_id, config.window_days)]
        # Die Abschluss-Status fallen durch "statusCategory != Done" hindurch
        # und brauchen deshalb eine zweite Abfrage.
        return [assigned_jql(ids), closing_jql(config.closing_status, ids)]

    return build


async def load_board(
    settings: Settings,
    config: BoardConfig,
    mode: str,
    on_worklog_check: CountReporter | None = None,
    on_log: Reporter | None = None,
    member: TeamMember | None = None,
) -> Board:
    """Holt eine Ticket-Ansicht und baut sie ueber den Kern auf.

    Args:
        settings:
            Zugang und Host.
        config:
            Die Kern-Konfiguration, ueblicherweise aus config_from.
        mode:
            MODE_ASSIGNED, MODE_RELEVANT oder MODE_TEAM.
        on_worklog_check:
            Rueckruf mit der Anzahl der Tickets, deren Buchungslage im
            zweiten Durchgang geprueft wird.
        on_log:
            Rueckruf fuer die ausfuehrliche Ausgabe, inklusive der Ausdruecke.
        member:
            Bei MODE_TEAM die gemeinte Person.

    Returns:
        Das fertige Board.
    """
    announce = on_worklog_check or (lambda _count: None)
    client = build_client(settings, on_log)

    account_id, issues = await client.fetch_issues(
        jqls_for(mode, config, member), FIELDS
    )
    now = dt.datetime.now(dt.UTC)

    # In der Fremdsicht ist die gemeinte Person nicht der angemeldete
    # Benutzer. Ohne diese Umstellung waeren die Autoren-Merkmale gegen die
    # falsche Person gerechnet.
    ids: Sequence[str] = member.account_ids if mode == MODE_TEAM and member else ()
    own_id = ids[0] if ids else account_id

    board = build_board(
        issues,
        config,
        now,
        account_id=own_id,
        browse_base=settings.jira_host,
        account_ids=ids,
    )

    if mode != MODE_ASSIGNED:
        # Der Pile of Shame beruht auf Buchungszeiten. Ueber eine andere
        # Person waere das eine Buchungskontrolle und keine Handlungshilfe -
        # deshalb entfaellt der zweite, teure Durchgang hier ganz. Die
        # Buchungsdaten werden also nicht etwa geholt und verworfen, sie
        # werden gar nicht erst angefordert.
        return board

    keys = pending_worklog_keys(board, config)
    if not keys:
        return board

    announce(len(keys))
    stats = await client.fetch_worklog_stats(keys)
    worklogs = {
        key: WorklogInfo(count=count, last=parse_ts(started))
        for key, (count, started) in stats.items()
    }
    return build_board(
        issues,
        config,
        now,
        account_id=account_id,
        browse_base=settings.jira_host,
        worklogs=worklogs,
    )


async def load_statistics(
    settings: Settings,
    on_log: Reporter | None = None,
) -> Statistics:
    """Holt die Ticket-Historie und wertet sie fuer die Diagramme aus.

    Bewusst getrennt vom Listen-Abruf: die Historie braucht eine weitere
    Abfrage ueber alle Tickets, offen wie erledigt.

    Args:
        settings:
            Zugang und Host.
        on_log:
            Rueckruf fuer die ausfuehrliche Ausgabe.

    Returns:
        Die ausgewerteten Zahlen.
    """
    client = build_client(settings, on_log)
    _, issues = await client.fetch_issues(lambda _aid: [history_jql()], STATS_FIELDS)
    return build_statistics(issues, dt.datetime.now(dt.UTC))
