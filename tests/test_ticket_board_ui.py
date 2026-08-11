"""Tests fuer die Oberflaeche der Ticket-Ansichten.

Der Kern ist in test_ticket_board.py abgedeckt. Hier geht es um das, was die
TUI daraus macht: Gruppenzeilen, Filter, die Uebersetzung der Einstellungen
und die Darstellung der Auswertung.

Alle Zeitpunkte sind fest verdrahtet - ein Test, der am heutigen Datum haengt,
ist gruen bis zum naechsten Monatswechsel und danach ohne Code-Aenderung rot.
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Checkbox, DataTable, Input, Select
from textual_plotext import PlotextPlot

from jira_timesheet.i18n import load_locale, t
from jira_timesheet.models.settings import Settings
from jira_timesheet.screens.settings_screen import SettingsScreen
from jira_timesheet.services.ticket_board import (
    AgeBucket,
    Board,
    BoardConfig,
    Group,
    Marker,
    MonthValue,
    Role,
    Statistics,
    Ticket,
    build_board,
)
from jira_timesheet.services.ticket_board_loader import (
    MODE_ASSIGNED,
    MODE_RELEVANT,
    config_from,
    jqls_for,
)
from jira_timesheet.widgets.ticket_board_table import TicketBoardTable
from jira_timesheet.widgets.ticket_stats_panel import TicketStatsPanel

TZ = dt.timezone(dt.timedelta(hours=2))
NOW = dt.datetime(2026, 8, 5, 12, 0, tzinfo=TZ)
ACCOUNT = "712020:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OTHER = "712020:11111111-2222-3333-4444-555555555555"

CONFIG = BoardConfig(
    active_status=("In Arbeit",),
    backlog_status=("Bereit",),
    handback_status=("Bewertung",),
    acceptance_status=("Abnahme",),
    closing_status=("Abschluss",),
    priorities=("Blocker", "Hoch", "Mittel", "Niedrig"),
    high_priority_ranks=1,
)


@pytest.fixture(autouse=True)
def _german_labels() -> None:
    """Echte Beschriftungen laden - sonst stehen die i18n-Schluessel im Kopf."""
    load_locale("de")


def _stamp(moment: dt.datetime) -> str:
    """Formatiert einen Zeitpunkt so, wie Jira ihn liefert."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000%z")


def _issue(
    key: str,
    status: str,
    *,
    category: str = "indeterminate",
    days_idle: int = 1,
    priority: str = "Mittel",
    reporter: str = ACCOUNT,
) -> dict[str, Any]:
    """Baut eine Suchantwort-Zeile, wie Jira sie liefert."""
    updated = NOW - dt.timedelta(days=days_idle)
    return {
        "key": key,
        "fields": {
            "summary": f"Titel zu {key}",
            "status": {"name": status, "statusCategory": {"key": category}},
            "priority": {"name": priority},
            "issuetype": {"name": "Story"},
            "reporter": {"accountId": reporter, "displayName": "Wer Auch Immer"},
            "assignee": {"accountId": ACCOUNT, "displayName": "Ich Selbst"},
            "created": _stamp(NOW - dt.timedelta(days=400)),
            "updated": _stamp(updated),
            "issuelinks": [],
        },
    }


ISSUES = [
    _issue("PROJ-1", "In Arbeit", priority="Blocker", days_idle=2),
    _issue("PROJ-2", "In Arbeit", days_idle=400),
    _issue("PROJ-3", "Bereit", days_idle=5),
    _issue("PROJ-4", "Abnahme", days_idle=30),
    _issue("PROJ-5", "Bewertung", days_idle=3, reporter=OTHER),
]


def _board_mit_abgeschlossen() -> Board:
    """Ein Board mit einem wirklich fertigen Ticket.

    Die Rolle DONE ist der Kontrollblick: sichtbar, aber ohne Anspruch auf
    Aufmerksamkeit - deshalb startet die Gruppe zugeklappt.
    """
    return build_board(
        [*ISSUES, _issue("PROJ-9", "Erledigt", days_idle=100)],
        BoardConfig(
            active_status=CONFIG.active_status,
            backlog_status=CONFIG.backlog_status,
            handback_status=CONFIG.handback_status,
            acceptance_status=CONFIG.acceptance_status,
            closing_status=CONFIG.closing_status,
            done_status=("Erledigt",),
            priorities=CONFIG.priorities,
            high_priority_ranks=CONFIG.high_priority_ranks,
        ),
        NOW,
        account_id=ACCOUNT,
        browse_base="https://beispiel.atlassian.net",
    )


def _board() -> Board:
    """Ein fertig aufbereitetes Board aus dem echten Kern."""
    return build_board(
        ISSUES,
        CONFIG,
        NOW,
        account_id=ACCOUNT,
        browse_base="https://beispiel.atlassian.net",
    )


async def _warte_auf_diagramm(pilot: Any, app: App[Any], widget_id: str) -> str:
    """Wartet, bis ein Diagramm wirklich gezeichnet ist, und liefert es.

    Ein einzelnes ``pilot.pause()`` reicht dafuer nicht: solange das Layout
    nicht durch ist, liefert plotext nur einen leeren Rahmen ohne Titel. Unter
    Last passiert genau das - am 11.08.2026 hat dieser Test deshalb einen Push
    blockiert, obwohl am Code nichts falsch war. Gewartet wird deshalb auf den
    ZUSTAND (der Titel steht im Bild) und nicht auf eine geschaetzte Frist.

    Args:
        pilot:
            Der Textual-Pilot der laufenden App.
        app:
            Die App, in der das Diagramm haengt.
        widget_id:
            Kennung ohne Modus-Endung, etwa "stats-flow".

    Returns:
        Das gebaute Diagramm als Text.

    Raises:
        AssertionError:
            Wenn binnen zehn Sekunden kein Titel erscheint. Dann ist es kein
            Timing-Problem mehr, sondern ein echter Fehler.
    """
    grenze = time.monotonic() + 10.0
    gebaut = ""
    while time.monotonic() < grenze:
        gebaut = app.query_one(f"#{widget_id}-{MODE_ASSIGNED}", PlotextPlot).plt.build()
        # Ein leerer Rahmen enthaelt keinen Buchstaben - erst mit Beschriftung
        # ist das Diagramm fertig gezeichnet.
        if any(zeichen.isalpha() for zeichen in gebaut):
            return gebaut
        await pilot.pause()
    raise AssertionError(f"{widget_id}: nach 10 s kein gezeichnetes Diagramm")


class _BoardApp(App[None]):
    """Minimal-App, die nur die Ticket-Tabelle zeigt."""

    def __init__(self) -> None:
        super().__init__()
        # Gemeldete Ticketschluessel - so laesst sich pruefen, ob ein Klick
        # tatsaechlich beim Host ankommt.
        self.gemeldet: list[str] = []

    def compose(self) -> ComposeResult:
        yield TicketBoardTable(
            MODE_ASSIGNED,
            jira_host="https://beispiel.atlassian.net",
            id=f"board-{MODE_ASSIGNED}",
        )

    def on_ticket_board_table_ticket_selected(
        self, event: TicketBoardTable.TicketSelected
    ) -> None:
        self.gemeldet.append(event.ticket.key if event.ticket is not None else "None")


def _rows(table: DataTable[Any]) -> list[list[str]]:
    """Liest die Tabelle als Liste von Zeilen aus reinem Text."""
    return [
        [str(cell) for cell in table.get_row_at(index)]
        for index in range(table.row_count)
    ]


class TestKonfigurationsUebersetzung:
    """Aus den Einstellungen muss eine brauchbare Kern-Konfiguration werden."""

    def test_statuslisten_wandern_unveraendert_in_die_konfiguration(self) -> None:
        settings = Settings(
            board_active_status=["In Arbeit", "Im Review"],
            board_closing_status=["Abschluss"],
        )
        config = config_from(settings)
        assert config.active_status == ("In Arbeit", "Im Review")
        assert config.closing_status == ("Abschluss",)

    def test_leere_prioritaetsliste_faellt_auf_die_vorgabe_zurueck(self) -> None:
        # Ohne Rangfolge waere jede Prioritaet gleich dringend - die Vorgabe
        # des Kerns deckt mehrere gaengige Jira-Schemata ab.
        assert len(config_from(Settings()).priorities) > 1

    def test_schwelle_null_schaltet_die_rolle_ab(self) -> None:
        settings = Settings(
            board_threshold_active=5.0,
            board_threshold_acceptance=0.0,
            board_threshold_closing=0.0,
        )
        config = config_from(settings)
        assert config.threshold_of(Role.ACTIVE) == 5.0
        # Nicht 0.0, sondern gar kein Eintrag: der Kern erzeugt fuer diese
        # Rolle dann keinen Pile of Shame, statt bei jeder Regung anzuschlagen.
        assert config.threshold_of(Role.ACCEPTANCE) is None
        assert config.threshold_of(Role.CLOSING) is None

    def test_zugewiesene_fragen_die_abschluss_status_zusaetzlich_ab(self) -> None:
        # Sie fallen durch "statusCategory != Done" hindurch und brauchen
        # deshalb eine zweite Abfrage - sonst fehlen sie lautlos.
        jqls = list(jqls_for(MODE_ASSIGNED, CONFIG)(ACCOUNT))
        assert len(jqls) == 2
        assert "Abschluss" in jqls[1]

    def test_relevante_stellen_genau_eine_abfrage(self) -> None:
        jqls = list(jqls_for(MODE_RELEVANT, CONFIG)(ACCOUNT))
        assert len(jqls) == 1
        assert "assignee != currentUser()" in jqls[0]


class TestTabellenaufbau:
    """Gruppen, Zeilen und Merkmale muessen in der Tabelle ankommen."""

    async def test_jede_gruppe_bekommt_eine_ueberschrift_mit_anzahl(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        titles = [row[0] for row in rows]
        assert any(f"{t('board.group.active')} (2)" in title for title in titles)
        assert any(f"{t('board.group.backlog')} (1)" in title for title in titles)
        # Fuenf Tickets, vier Gruppenzeilen und drei Leerzeilen dazwischen.
        assert len(rows) == 12

    async def test_gruppen_sind_durch_eine_leerzeile_getrennt(self) -> None:
        """Im Terminal gibt es keine Linien - der Abstand macht die Gliederung."""
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        leer = [index for index, row in enumerate(rows) if not any(cell.strip() for cell in row)]
        # Genau eine Leerzeile vor jeder Gruppe ausser der ersten.
        assert len(leer) == 3
        # Nie zu Beginn - sonst faengt die Tabelle mit einer Luecke an.
        assert 0 not in leer
        for index in leer:
            assert rows[index + 1][0].startswith("▼")

    async def test_tickets_stehen_eingerueckt_unter_ihrer_gruppe(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        gruppen = [row[0] for row in rows if row[0].startswith("▼")]
        tickets = [row[0] for row in rows if "PROJ-" in row[0]]
        assert gruppen and tickets
        # Die Ueberschrift steht am linken Rand, die Tickets eingerueckt.
        assert all(not title.startswith(" ") for title in gruppen)
        assert all(key.startswith("  PROJ-") for key in tickets)

    async def test_gruppenzeile_verweist_auf_die_erklaerung(self) -> None:
        """Der Kurztitel allein sagt nicht, was zu tun ist.

        Der Hinweis stand frueher in der TITEL-Spalte und las sich dort wie
        die Ueberschrift des ersten Tickets - "es wird gerade gearbeitet" als
        Ticketname. Jetzt steht dort ein Fragezeichen, der Text haengt am
        Tooltip.
        """
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        gruppe = next(row for row in rows if t("board.group.handback") in row[0])
        assert gruppe[0].rstrip().endswith("(?)")
        # Die Titel-Spalte der Gruppenzeile bleibt leer.
        assert gruppe[-1] == ""
        # Gegenprobe: der Hinweistext taucht in KEINER Zelle mehr auf.
        assert all(t("board.group.handback_hint") not in zelle for zeile in rows for zelle in zeile)

    async def test_merkmale_stehen_in_der_zeile(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        verwaist = next(row for row in rows if row[0].strip() == "PROJ-2")
        assert t("board.marker.stale") in verwaist[5]

    async def test_zeilenzeiger_liefert_das_ticket_der_zeile(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            table = app.query_one(DataTable)
            # Zeile 0 ist eine Gruppe, Zeile 1 das erste Ticket.
            table.move_cursor(row=0)
            await pilot.pause()
            assert widget.current_ticket() is None
            table.move_cursor(row=1)
            await pilot.pause()
            assert widget.current_ticket() is not None


class TestFilter:
    """Die drei Filter muessen wirken und sich nicht gegenseitig aufheben."""

    async def test_statusfilter_zeigt_nur_den_gewaehlten_status(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            app.query_one(Select).value = "Bereit"
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        tickets = [row for row in rows if "PROJ-" in row[0]]
        assert [row[0].strip() for row in tickets] == ["PROJ-3"]
        # Die leeren Gruppen fallen weg, statt als Ueberschrift ohne Inhalt
        # stehen zu bleiben.
        assert len(rows) == 2

    async def test_statusauswahl_kennt_nur_vorkommende_werte(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            select = app.query_one(Select)
            labels = [str(label) for label, _value in select._options]

        assert t("board.filter.all") in labels
        assert "In Arbeit" in labels
        # Ein Status, den kein Ticket traegt, darf nicht zur Auswahl stehen.
        assert "Erledigt" not in labels

    async def test_handlungsbedarf_blendet_ruhige_tickets_aus(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            app.query_one(Checkbox).value = True
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        keys = {row[0].strip() for row in rows if "PROJ-" in row[0]}
        # PROJ-3 (Backlog, frisch, ohne Merkmal) muss verschwinden.
        assert "PROJ-3" not in keys
        assert "PROJ-2" in keys

    async def test_suche_trifft_schluessel_und_titel(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            app.query_one(Input).value = "proj-4"
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        assert [row[0].strip() for row in rows if "PROJ-" in row[0]] == ["PROJ-4"]

    async def test_hinweiszeile_nennt_gezeigte_und_gesamte_anzahl(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            app.query_one(Input).value = "PROJ-4"
            await pilot.pause()
            hint = str(app.query_one("#board-hint-assigned").render())

        assert hint == t("board.hint.filtered", shown=1, total=5)


def _statistik() -> Statistics:
    """Eine Auswertung mit Zulauf, Abgang und Altersverteilung."""
    return Statistics(
        months=[
            MonthValue(month="2026-07", inflow=4, outflow=1, cumulative=3),
            MonthValue(month="2026-08", inflow=2, outflow=5, cumulative=0),
        ],
        buckets=[AgeBucket(label="0-5", count=2), AgeBucket(label="> 60", count=1)],
        open_count=7,
        resolved_recent=3,
        lead_time_median=12.0,
    )


class _StatsHost(App[None]):
    """Minimal-App, die nur die Auswertung zeigt."""

    def __init__(self) -> None:
        super().__init__()
        self.angefragt = 0

    def compose(self) -> ComposeResult:
        yield TicketStatsPanel(MODE_ASSIGNED, id="board-stats")

    def on_ticket_stats_panel_requested(self, event: TicketStatsPanel.Requested) -> None:
        self.angefragt += 1


class TestAuswertung:
    """Die Diagramme duerfen nicht mehr behaupten, als die Zahlen hergeben."""

    async def test_diagramme_zeigen_die_reihen_mit_beschriftung(self) -> None:
        """Belegt am gebauten Diagramm, nicht an der Datenstruktur davor."""
        app = _StatsHost()
        async with app.run_test(size=(140, 34)) as pilot:
            await pilot.pause()
            app.query_one(TicketStatsPanel).set_statistics(_statistik())
            await pilot.pause()
            flow = app.query_one(f"#stats-flow-{MODE_ASSIGNED}", PlotextPlot).plt.build()
            ages = app.query_one(f"#stats-age-{MODE_ASSIGNED}", PlotextPlot).plt.build()

        # Die Legende benennt beide Reihen - sonst ist nicht zu erkennen,
        # welcher Balken welcher ist.
        assert t("board.stats.inflow") in flow
        assert t("board.stats.outflow") in flow
        # Die Zeitachse traegt die Monate, gekuerzt auf JJ-MM.
        assert "26-08" in flow
        assert "> 60" in ages

    async def test_ohne_monate_bricht_nichts(self) -> None:
        app = _StatsHost()
        async with app.run_test(size=(140, 34)) as pilot:
            await pilot.pause()
            app.query_one(TicketStatsPanel).set_statistics(Statistics(open_count=0))
            gebaut = await _warte_auf_diagramm(pilot, app, "stats-flow")

        # Kein Absturz, und die Ueberschrift steht trotzdem da.
        assert t("board.stats.flow") in gebaut

    async def test_aufklappen_fordert_die_zahlen_an(self) -> None:
        """Der Bereich ging auf und blieb leer - belegt am 06.08.2026.

        Textual postet ausschliesslich ``Collapsible.Expanded`` und
        ``Collapsible.Collapsed``. Ein Handler auf die gemeinsame Oberklasse
        ``Toggled`` wird nie gerufen (textual 8.2.8, _collapsible.py:218).
        """
        from textual.widgets import Collapsible

        class _StatsApp(App[None]):
            def __init__(self) -> None:
                super().__init__()
                self.angefragt = 0

            def compose(self) -> ComposeResult:
                yield TicketStatsPanel(MODE_ASSIGNED, id="board-stats")

            def on_ticket_stats_panel_requested(
                self, event: TicketStatsPanel.Requested
            ) -> None:
                self.angefragt += 1

        app = _StatsApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.angefragt == 0, "Zugeklappt darf nichts abgerufen werden."
            app.query_one(Collapsible).collapsed = False
            await pilot.pause()
            await pilot.pause()
            assert app.angefragt == 1

    async def test_vorhandene_zahlen_loesen_keinen_zweiten_abruf_aus(self) -> None:
        from textual.widgets import Collapsible

        class _StatsApp(App[None]):
            def __init__(self) -> None:
                super().__init__()
                self.angefragt = 0

            def compose(self) -> ComposeResult:
                yield TicketStatsPanel(MODE_ASSIGNED, id="board-stats")

            def on_ticket_stats_panel_requested(
                self, event: TicketStatsPanel.Requested
            ) -> None:
                self.angefragt += 1

        app = _StatsApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(TicketStatsPanel).set_statistics(Statistics(open_count=3))
            collapsible = app.query_one(Collapsible)
            collapsible.collapsed = False
            await pilot.pause()
            collapsible.collapsed = True
            collapsible.collapsed = False
            await pilot.pause()

        # Ein Abruf ueber die gesamte Historie kostet Zeit - zweimal
        # Auf- und Zuklappen darf ihn nicht wiederholen.
        assert app.angefragt == 0

    def test_kennzahlen_nennen_bestand_durchsatz_und_saldo(self) -> None:
        text = TicketStatsPanel.head_text(_statistik()).plain
        assert f"7 {t('board.stats.open')}" in text
        assert t("board.stats.lead_time") in text
        # Zulauf, Abgang und das Vorzeichen des Saldos - die eine Zahl, an
        # der man sieht, ob der Bestand waechst oder schrumpft.
        assert "6 / 6" in text
        assert "(+0)" in text


class TestEinstellungsseite:
    """Die Seite "Tickets" muss ihre Werte einsammeln."""

    async def test_listen_werden_zerlegt_und_zahlen_gelesen(self) -> None:
        screen = SettingsScreen(Settings().to_dict(), lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            screen.query_one("#set-board-active", Input).value = "In Arbeit, Im Review"
            screen.query_one("#set-board-closing", Input).value = "Abschluss"
            screen.query_one("#set-board-window-days", Input).value = "45"
            screen.query_one("#set-board-threshold-active", Input).value = "7,5"
            await pilot.pause()
            result: dict[str, object] = {}
            screen.collect_app_settings(result)

        assert result["board_active_status"] == ["In Arbeit", "Im Review"]
        assert result["board_closing_status"] == ["Abschluss"]
        assert result["board_window_days"] == 45
        # Deutsches Dezimalkomma muss durchgehen - sonst faellt der Wert
        # stillschweigend auf die Vorgabe zurueck.
        assert result["board_threshold_active"] == 7.5

    async def test_leeres_feld_bleibt_leer(self) -> None:
        """Keine Zuordnung ist eine gueltige Angabe, kein fehlender Wert."""
        screen = SettingsScreen(Settings().to_dict(), lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            result: dict[str, object] = {}
            screen.collect_app_settings(result)

        assert result["board_active_status"] == []
        assert result["board_priorities"] == []

    async def test_jedes_statusfeld_zeigt_ein_beispiel(self) -> None:
        """Ohne Platzhalter versteht die Seite niemand - belegt am 05.08.2026."""
        screen = SettingsScreen(Settings().to_dict(), lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            for widget_id in (
                "set-board-active",
                "set-board-backlog",
                "set-board-acceptance",
                "set-board-handback",
                "set-board-closing",
                "set-board-priorities",
            ):
                assert screen.query_one(f"#{widget_id}", Input).placeholder.strip()

    async def test_beispiele_verraten_keine_fremde_instanz(self) -> None:
        """Die Platzhalter sind erfunden und muessen es bleiben."""
        screen = SettingsScreen(Settings().to_dict(), lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            texte = " ".join(
                screen.query_one(f"#{widget_id}", Input).placeholder
                for widget_id in (
                    "set-board-active",
                    "set-board-backlog",
                    "set-board-acceptance",
                    "set-board-handback",
                    "set-board-closing",
                    "set-board-done",
                )
            ).casefold()

        # Die echten Statusnamen der vermessenen Instanz. Am 11.08.2026 waren
        # drei davon versehentlich als Platzhalter eingetragen - der Test hat
        # sie abgefangen, deshalb deckt er jetzt ALLE sechs Felder ab.
        for marker in (
            "in arbeit",
            "im code review",
            "fertig für entwicklung",
            "in abnahme",
            "evaluation",
            "schließen",
            "übergabe betrieb",
        ):
            assert marker not in texte


class TestLeereAnsicht:
    """Ohne Daten darf die Ansicht nicht wie ein Absturz aussehen."""

    async def test_hinweis_statt_leerer_flaeche(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.show_message("Tickets werden geladen ...")
            await pilot.pause()
            hint = str(app.query_one("#board-hint-assigned").render())
            assert hint == "Tickets werden geladen ..."
            assert app.query_one(DataTable).row_count == 0

    async def test_board_ohne_tickets_meldet_fehlanzeige(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(Board(groups=[Group(role=Role.ACTIVE, tickets=[])], tickets=[]))
            await pilot.pause()
            hint = str(app.query_one("#board-hint-assigned").render())

        assert hint == t("board.hint.empty")


class TestTicketVerweis:
    """Der Ticketschluessel muss anklickbar sein."""

    async def test_schluessel_traegt_den_verweis_auf_die_instanz(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            table = app.query_one(DataTable)
            zelle = table.get_cell_at((1, 0))

        assert any("link https://beispiel.atlassian.net/browse/" in str(span.style) for span in zelle.spans)

    async def test_ohne_host_kein_verweis(self) -> None:
        class _HostlessApp(App[None]):
            def compose(self) -> ComposeResult:
                yield TicketBoardTable(MODE_ASSIGNED, jira_host="", id="board-assigned")

        app = _HostlessApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            zelle = app.query_one(DataTable).get_cell_at((1, 0))

        assert not any("link" in str(span.style) for span in zelle.spans)


async def _settle(pilot: Any) -> None:
    """Wartet, bis der Aufbau der App zur Ruhe gekommen ist.

    Notwendig, weil die Stundenzettel-Tabelle sich ueber
    ``call_after_refresh`` selbst den Fokus holt (timesheet_table.py:197).
    TabbedContent folgt dem Fokus - ein zu frueh gesetzter Reiter springt
    dadurch auf die Liste zurueck. Genau daran ist der erste Entwurf dieser
    Tests gescheitert.
    """
    for _ in range(4):
        await pilot.pause()


class TestVerdrahtung:
    """Der Weg von der App in die Ansicht - ohne jeden Netzzugriff."""

    async def test_ohne_zugang_wird_nichts_abgerufen(self) -> None:
        """Ein Abruf ohne Zugangsdaten liefe in einen Fehler statt in einen Hinweis."""
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._settings.jira_host = ""
            app._settings.jira_token = ""
            app.query_one("#view-tabs").active = "tab-assigned"
            await pilot.pause()
            hint = str(app.query_one("#board-hint-assigned").render())
            assert hint == t("board.needs_settings")
            # Nicht als geladen vermerken - sonst bleibt der Hinweis fuer
            # immer stehen, auch nachdem der Zugang gepflegt wurde.
            assert app._board_loaded[MODE_ASSIGNED] is False

    async def test_zusammenfassung_zeigt_die_kennzahlen_der_ansicht(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._board_loaded[MODE_ASSIGNED] = True
            app.query_one("#view-tabs").active = "tab-assigned"
            await pilot.pause()
            app.query_one("#board-assigned", TicketBoardTable).set_board(_board())
            app._show_board_summary(MODE_ASSIGNED)
            await pilot.pause()
            items = app._board_items(_board(), MODE_ASSIGNED)

        labels = {item.label for item in items}
        assert t("board.summary.tickets") in labels
        # Was nicht vorkommt, steht auch nicht da - eine Leiste voller Nullen
        # verdeckt die Zahl, auf die es ankommt.
        assert t("board.summary.pile_of_shame") not in labels

    async def test_aktualisieren_gilt_in_allen_reitern(self) -> None:
        """F5 aktualisiert, was gerade zu sehen ist.

        Frueher lud "g" den Stundenzettel und F5 die Ticket-Ansichten - zwei
        Tasten fuer dieselbe Absicht. Seit dem 11.08.2026 gibt es nur noch
        F5, und die Taste gilt in jedem Reiter.
        """
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._settings.jira_host = "https://beispiel.atlassian.net"
            app._settings.email = "test@example.invalid"
            app._settings.jira_token = "geheim"

            for reiter in ("tab-list", "tab-relevant", "tab-team"):
                app.query_one("#view-tabs").active = reiter
                await pilot.pause()
                assert app.check_action("refresh", ()) is True, reiter

            # Ohne Zugangsdaten fuehrt die Taste nur in eine Fehlermeldung -
            # dann bleibt sie aus dem Footer draussen.
            app._settings.jira_token = ""
            assert app.check_action("refresh", ()) is None

    async def test_die_alte_generieren_taste_gibt_es_nicht_mehr(self) -> None:
        # Gegenprobe zur Zusammenlegung: bliebe die Bindung bestehen, haetten
        # wir zwei Tasten fuer dieselbe Absicht - und der Footer waere wieder
        # doppelt belegt.
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            aktionen = {
                binding.action
                for bindings in app._bindings.key_to_bindings.values()
                for binding in bindings
            }

        assert "generate" not in aktionen
        assert "refresh" in aktionen

    async def test_geaenderte_zuordnung_verwirft_die_geladenen_ansichten(self) -> None:
        """Ein altes Board waere nach der Aenderung schlicht falsch."""
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            vorher = app._board_fingerprint()
            app._settings.board_closing_status = ["Abschluss"]
            assert app._board_fingerprint() != vorher

    async def test_stundenzettel_aktionen_ruhen_in_den_ticket_reitern(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._board_loaded[MODE_ASSIGNED] = True
            app.query_one("#view-tabs").active = "tab-assigned"
            await pilot.pause()
            # Es gibt hier keine Stundenzettel-Zeile, auf die sie sich
            # beziehen koennten.
            assert app.check_action("show_details", ()) is False
            assert app.check_action("manual_entry", ()) is False
            assert app.check_action("delete_manual", ()) is None


class TestKontextmenue:
    """Der Rechtsklick-Pfad, an dem die Anwendung still ausgestiegen ist.

    Belegt am 06.08.2026: ``ContextMenuItem`` nimmt erst den Schluessel und
    dann die Beschriftung, ``ContextMenuScreen`` die Position als
    Schluesselwort ``at``. Beides war vertauscht - der Rechtsklick hat die
    Anwendung ohne jede Meldung beendet. Kein Test hatte den Pfad je
    ausgeloest.
    """

    async def _menu_screen(self, pilot: Any, app: Any) -> Any:
        """Loest den Rechtsklick auf der ersten Ticketzeile aus."""
        widget = app.query_one("#board-assigned", TicketBoardTable)
        widget.set_board(_board())
        await pilot.pause()
        ticket = _board().groups[0].tickets[0]
        widget.post_message(TicketBoardTable.TicketRightClicked(10, 5, ticket))
        await pilot.pause()
        await pilot.pause()
        return app.screen

    async def test_rechtsklick_oeffnet_das_menue_statt_zu_beenden(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._board_loaded[MODE_ASSIGNED] = True
            app.query_one("#view-tabs").active = "tab-assigned"
            await pilot.pause()
            screen = await self._menu_screen(pilot, app)

            # Die Anwendung laeuft noch, und das Menue liegt obenauf.
            assert app.is_running
            assert len(app.screen_stack) > 1
            assert type(screen).__name__ == "ContextMenuScreen"

    async def test_gewaehlte_aktion_kennt_ihr_ticket(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._board_loaded[MODE_ASSIGNED] = True
            app.query_one("#view-tabs").active = "tab-assigned"
            await pilot.pause()
            await self._menu_screen(pilot, app)

            geoeffnet: list[str] = []
            app._menu_ticket = _board().groups[0].tickets[0]
            import jira_timesheet.app as app_modul

            original = app_modul.webbrowser.open
            app_modul.webbrowser.open = lambda url, *a, **k: geoeffnet.append(str(url))
            try:
                app._on_board_menu("open_ticket")
            finally:
                app_modul.webbrowser.open = original

        assert geoeffnet and "beispiel.atlassian.net/browse/" in geoeffnet[0]


class TestAnonymisierung:
    """Fuer Screenshots duerfen keine echten Ticketdaten stehenbleiben."""

    def test_schluessel_titel_und_status_werden_ersetzt(self) -> None:
        from jira_timesheet.services.anonymizer import anonymize_board

        echt = _board()
        anonym = anonymize_board(echt)
        keys = {ticket.key for ticket in anonym.tickets}
        assert not keys & {ticket.key for ticket in echt.tickets}
        assert all("Titel zu PROJ" not in ticket.summary for ticket in anonym.tickets)
        # Statusnamen sind interne Prozessbezeichner des Betreibers.
        assert "In Arbeit" not in {ticket.status for ticket in anonym.tickets}

    def test_aussage_des_bildes_bleibt_erhalten(self) -> None:
        """Was nichts verraet, muss stehenbleiben - sonst zeigt das Bild nichts."""
        from jira_timesheet.services.anonymizer import anonymize_board

        echt = _board()
        anonym = anonymize_board(echt)
        assert [g.role for g in anonym.groups] == [g.role for g in echt.groups]
        # Je Gruppe vergleichen: die flache Liste baut die Kopie aus den
        # Gruppen neu auf und kann deshalb anders sortiert sein.
        for kopie, original in zip(anonym.groups, echt.groups, strict=True):
            assert [x.markers for x in kopie.tickets] == [x.markers for x in original.tickets]
            assert [x.idle_workdays for x in kopie.tickets] == [
                x.idle_workdays for x in original.tickets
            ]

    def test_verweis_zeigt_nicht_mehr_auf_die_echte_instanz(self) -> None:
        from jira_timesheet.services.anonymizer import anonymize_board

        for ticket in anonymize_board(_board()).tickets:
            assert "beispiel.atlassian.net" not in ticket.url

    async def test_umschalten_zeichnet_die_geladene_ansicht_neu(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._board_loaded[MODE_ASSIGNED] = True
            app.query_one("#view-tabs").active = "tab-assigned"
            await pilot.pause()
            board = _board()
            app._real_boards[MODE_ASSIGNED] = board
            app.query_one("#board-assigned", TicketBoardTable).set_board(board)
            await pilot.pause()

            app.action_toggle_anon()
            await pilot.pause()
            gezeigt = app.query_one("#board-assigned", TicketBoardTable).board
            assert gezeigt is not None
            # Ohne geladenen Stundenzettel darf das Umschalten trotzdem
            # wirken - sonst bliebe ein Screenshot der Ticket-Ansicht echt.
            assert app._anonymized is True
            assert "PROJ-1" not in {ticket.key for ticket in gezeigt.tickets}


class TestDringlichkeit:
    """Nur echte Unterlassungen werden rot - sonst faellt nichts mehr auf."""

    def test_ruhige_merkmale_bleiben_ruhig(self) -> None:
        ticket = Ticket(key="PROJ-9", markers=(Marker.ACCEPTANCE,))
        assert TicketBoardTable._marker_text(ticket).style == "yellow"

    def test_verwaistes_ticket_wird_rot(self) -> None:
        ticket = Ticket(key="PROJ-9", markers=(Marker.STALE,))
        assert TicketBoardTable._marker_text(ticket).style == "red"

    def test_ticket_ohne_merkmal_bleibt_leer(self) -> None:
        assert TicketBoardTable._marker_text(Ticket(key="PROJ-9")).plain == ""


class TestBedienungDerGruppen:
    """Klappen, Sortieren und der Klick auf die Ticketnummer.

    Alle vier Punkte hat Michael am 11.08.2026 am laufenden Programm gemeldet.
    """

    async def test_abgeschlossen_startet_zugeklappt(self) -> None:
        # 24 fertige Tickets fuellten den halben Bildschirm, ohne dass an
        # ihnen etwas zu tun waere.
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board_mit_abgeschlossen())
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        ueberschrift = next(row for row in rows if t("board.group.done") in row[0])
        assert ueberschrift[0].startswith("▶")
        # Die Anzahl steht trotzdem dran, sonst waere die Gruppe unsichtbar.
        assert "(1)" in ueberschrift[0]
        assert not any(row[0].strip() == "PROJ-9" for row in rows)

    async def test_klick_auf_die_gruppe_klappt_sie_auf(self) -> None:
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board_mit_abgeschlossen())
            await pilot.pause()
            widget._toggle_group(Role.DONE)
            await pilot.pause()
            rows = _rows(app.query_one(DataTable))

        ueberschrift = next(row for row in rows if t("board.group.done") in row[0])
        assert ueberschrift[0].startswith("▼")
        assert any(row[0].strip() == "PROJ-9" for row in rows)

    async def test_kopfklick_sortiert_nur_innerhalb_der_gruppe(self) -> None:
        # Der Kern der Anforderung: die Gliederung bleibt, nur die Ordnung
        # innerhalb einer Gruppe aendert sich.
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            table = app.query_one(DataTable)
            vorher = [row[0] for row in _rows(table) if not row[0].startswith("  ")]

            spalte = table.columns[widget._col_keys[6]]
            table.post_message(DataTable.HeaderSelected(table, spalte.key, 6, spalte.label))
            await pilot.pause()
            rows = _rows(table)

        # Die Gruppen stehen weiterhin in derselben Reihenfolge.
        assert [row[0] for row in rows if not row[0].startswith("  ")] == vorher

        # Innerhalb JEDER Gruppe ist nach Titel sortiert - ueber die Gruppen
        # hinweg ausdruecklich nicht, sonst waere die Gliederung aufgeloest.
        gruppen: list[list[str]] = []
        for row in rows:
            if not row[0].startswith("  "):
                gruppen.append([])
            elif gruppen:
                gruppen[-1].append(row[-1])
        gefuellt = [g for g in gruppen if len(g) > 1]
        assert gefuellt, "keine Gruppe mit mehr als einem Ticket - Test sagt nichts"
        for titel in gefuellt:
            assert titel == sorted(titel, key=str.casefold)

    async def test_dritter_kopfklick_stellt_die_vorgabe_wieder_her(self) -> None:
        # Ohne Rueckweg waere die Reihenfolge des Kerns nach dem ersten Klick
        # unerreichbar - und die traegt eine Aussage.
        app = _BoardApp()
        async with app.run_test() as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            table = app.query_one(DataTable)
            spalte = table.columns[widget._col_keys[6]]
            for _ in range(3):
                table.post_message(
                    DataTable.HeaderSelected(table, spalte.key, 6, spalte.label)
                )
                await pilot.pause()

        assert widget._sort_col == ""
        assert widget._sort_desc is False

    async def test_klick_auf_die_nummer_meldet_das_ticket(self) -> None:
        # Textuals DataTable meldet einen Mausklick NICHT als Auswahl - eine
        # unterstrichene Nummer, die auf Klick nichts tut, ist aber genau die
        # Enttaeuschung, die gemeldet wurde.
        app = _BoardApp()
        async with app.run_test(size=(120, 30)) as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            table = app.query_one(DataTable)
            # Bildzeile 2 ist Tabellenzeile 1: darueber liegen Spaltenkopf
            # und Gruppenueberschrift. Welches Ticket dort steht, bestimmt
            # die Reihenfolge des Kerns (aeltestes oben) - also ablesen
            # statt raten.
            erwartet = _rows(table)[1][0].strip()
            await pilot.click(table, offset=(4, 2))
            await pilot.pause()

        assert app.gemeldet == [erwartet]
        assert erwartet.startswith("PROJ-")

    async def test_klick_in_andere_spalten_oeffnet_nichts(self) -> None:
        # Sonst startet jeder Versuch, eine Zeile auszuwaehlen, den Browser.
        app = _BoardApp()
        async with app.run_test(size=(120, 30)) as pilot:
            widget = app.query_one(TicketBoardTable)
            widget.set_board(_board())
            await pilot.pause()
            table = app.query_one(DataTable)
            await pilot.click(table, offset=(35, 2))
            await pilot.pause()

        assert app.gemeldet == []
