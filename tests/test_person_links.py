"""Personen-Links: vom Kontextmenue einer Ticketliste nach "Mein Team".

Erkannt wird eine Person an ihrer accountId, nicht am Namen. Wer nicht auf
der Merkliste steht, erscheint voruebergehend als Gast und laesst sich per
Knopf aufnehmen - wie in der Qt-Fassung.
"""

from __future__ import annotations

import json
from typing import Any

from textual.app import App, ComposeResult
from textual.widgets import Button, Select, TabbedContent

from jira_timesheet.i18n import load_locale, t
from jira_timesheet.models.settings import Settings
from jira_timesheet.services.anonymizer import anonymize_board
from jira_timesheet.services.team import TeamMember
from jira_timesheet.services.ticket_board import Board, Group, Role, Ticket
from jira_timesheet.services.ticket_board_loader import MODE_TEAM
from jira_timesheet.widgets.ticket_board_table import TicketBoardTable

load_locale("de")

# Erfundene Kennungen im Format von Jira Cloud.
ID_ANNA = "712020:00000000-0000-0000-0000-000000000001"
ID_GERDA = "712020:00000000-0000-0000-0000-000000000002"


def _ticket(**felder: Any) -> Ticket:
    """Ein Ticket mit Bearbeiterin Anna und Autorin Gerda, anpassbar."""
    werte: dict[str, Any] = {
        "key": "PROJ-1",
        "assignee": "Muster, Anna",
        "assignee_id": ID_ANNA,
        "reporter": "Gast, Gerda",
        "reporter_id": ID_GERDA,
    }
    werte.update(felder)
    return Ticket(**werte)


def _merkliste(*eintraege: tuple[str, str]) -> None:
    """Schreibt eine Merkliste in die (isolierte) Einstellungsdatei."""
    Settings.SETTINGS_FILE.write_text(
        json.dumps(
            {"team_members": [{"display_name": name, "account_ids": [kennung]} for name, kennung in eintraege]}
        ),
        encoding="utf-8",
    )


async def _settle(pilot: Any) -> None:
    """Wartet, bis der Aufbau zur Ruhe gekommen ist (siehe test_ticket_board_ui)."""
    for _ in range(4):
        await pilot.pause()


class _TeamApp(App[None]):
    """Nur die Tabelle "Mein Team", mit Protokoll der Meldungen."""

    def __init__(self, members: list[str]) -> None:
        super().__init__()
        self.tabelle = TicketBoardTable(MODE_TEAM, members=members, id="board-team")
        self.wechsel: list[str] = []
        self.aufnahmen = 0

    def compose(self) -> ComposeResult:
        yield self.tabelle

    def on_ticket_board_table_member_changed(self, event: TicketBoardTable.MemberChanged) -> None:
        self.wechsel.append(event.name)

    def on_ticket_board_table_guest_add_requested(self, event: TicketBoardTable.GuestAddRequested) -> None:
        self.aufnahmen += 1


def _knopf_sichtbar(tabelle: TicketBoardTable) -> bool:
    return tabelle.query_one(f"#board-add-guest-{MODE_TEAM}", Button).has_class("-visible")


class TestGastImAuswahlfeld:
    """Das Widget fuer sich."""

    async def test_gast_wird_angehaengt_und_gewaehlt(self) -> None:
        app = _TeamApp(["Muster, Anna"])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.tabelle.show_guest("Gast, Gerda")
            await pilot.pause()
            select = app.tabelle.query_one(f"#board-member-{MODE_TEAM}", Select)
            beschriftungen = [str(prompt) for prompt, _ in select._options]
            assert app.tabelle.guest_selected
            assert app.tabelle.member == ""
            assert t("board.filter.guest", name="Gast, Gerda") in beschriftungen
            assert "Muster, Anna" in beschriftungen
            assert _knopf_sichtbar(app.tabelle)
            # Die Anwendung laedt selbst - ein MemberChanged loeste einen
            # zweiten Abruf aus.
            assert app.wechsel == []

    async def test_gast_ohne_merkliste(self) -> None:
        app = _TeamApp([])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.tabelle.show_guest("Gast, Gerda")
            await pilot.pause()
            assert app.tabelle.guest_selected

    async def test_geaenderte_merkliste_behaelt_den_gewaehlten_gast(self) -> None:
        app = _TeamApp(["Muster, Anna"])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.tabelle.show_guest("Gast, Gerda")
            app.tabelle.set_members(["Muster, Anna", "Beispiel, Reiner"])
            await pilot.pause()
            assert app.tabelle.guest_selected
            assert app.wechsel == []

    async def test_gast_entfernen_rueckt_auf_die_merkliste(self) -> None:
        app = _TeamApp(["Muster, Anna"])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.tabelle.show_guest("Gast, Gerda")
            await pilot.pause()
            app.tabelle.clear_guest()
            await pilot.pause()
            assert not app.tabelle.guest_selected
            assert app.tabelle.guest == ""
            assert app.tabelle.member == "Muster, Anna"
            assert not _knopf_sichtbar(app.tabelle)
            assert app.wechsel == []

    async def test_person_waehlen_meldet_keinen_wechsel(self) -> None:
        app = _TeamApp(["Muster, Anna", "Beispiel, Reiner"])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.tabelle.select_member("Beispiel, Reiner")
            await pilot.pause()
            assert app.tabelle.member == "Beispiel, Reiner"
            assert app.wechsel == []

    async def test_benutzer_waehlt_den_gast_wieder(self) -> None:
        # Wer von Hand zurueck auf den Gast geht, will dessen Tickets sehen -
        # das ist ein echter Wechsel und muss gemeldet werden.
        app = _TeamApp(["Muster, Anna"])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.tabelle.show_guest("Gast, Gerda")
            await pilot.pause()
            select = app.tabelle.query_one(f"#board-member-{MODE_TEAM}", Select)
            select.value = "Muster, Anna"
            await pilot.pause()
            assert not _knopf_sichtbar(app.tabelle)
            select.value = next(wert for _, wert in select._options if wert != "Muster, Anna")
            await pilot.pause()
            assert app.tabelle.guest_selected
            assert app.wechsel == ["Muster, Anna", ""]

    async def test_knopf_meldet_die_aufnahme(self) -> None:
        app = _TeamApp(["Muster, Anna"])
        async with app.run_test() as pilot:
            await pilot.pause()
            app.tabelle.show_guest("Gast, Gerda")
            await pilot.pause()
            app.tabelle.query_one(f"#board-add-guest-{MODE_TEAM}", Button).press()
            await pilot.pause()
            assert app.aufnahmen == 1


class TestKontextmenue:
    """Welche Eintraege das Menue einer Ticketzeile anbietet."""

    async def test_bearbeiter_und_autor(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            eintraege = app._person_menu_items(_ticket())
        # Ohne Merkliste steht hinter jeder Person auch "zu meinem Team hinzufuegen".
        assert [e.label for e in eintraege] == [
            t("menu.person_tickets", name="Muster, Anna"),
            t("menu.add_to_team", name="Muster, Anna"),
            t("menu.person_tickets", name="Gast, Gerda"),
            t("menu.add_to_team", name="Gast, Gerda"),
        ]
        assert all(e.enabled for e in eintraege)

    async def test_dieselbe_person_nur_einmal(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            eintraege = app._person_menu_items(_ticket(reporter="Muster, Anna", reporter_id=ID_ANNA))
        assert [e.label for e in eintraege] == [
            t("menu.person_tickets", name="Muster, Anna"),
            t("menu.add_to_team", name="Muster, Anna"),
        ]

    async def test_ohne_kennung_bleibt_ein_gesperrter_eintrag(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            eintraege = app._person_menu_items(_ticket(assignee_id="", reporter_id="kein gueltiges Format!"))
        assert [(e.label, e.enabled) for e in eintraege] == [(t("menu.person_tickets_none"), False)]

    async def test_im_screenshot_modus_gesperrt(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app._anonymized = True
            eintraege = app._person_menu_items(_ticket())
        assert [(e.label, e.enabled) for e in eintraege] == [(t("menu.person_tickets_none"), False)]

    def test_anonymisierung_leert_die_kennungen(self) -> None:
        echt = Board(groups=[Group(role=Role.ACTIVE, tickets=[_ticket()])], tickets=[_ticket()])
        kopie = anonymize_board(echt).tickets[0]
        assert (kopie.assignee_id, kopie.reporter_id) == ("", "")


class TestWegNachMeinTeam:
    """Die Anwendung: Menueaktion, Reiterwechsel, Gast und Aufnahme."""

    async def test_person_von_der_merkliste_wird_gewaehlt(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        _merkliste(("Anna", ID_ANNA), ("Reiner Beispiel", ID_GERDA.replace("2", "3")))
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            # Jira nennt sie anders als die Merkliste - erkannt wird sie an der Kennung.
            app.show_person_tickets(ID_ANNA, "Muster, Anna")
            await _settle(pilot)
            widget = app._board_widget(MODE_TEAM)
            assert app.query_one("#view-tabs", TabbedContent).active == "tab-team"
            assert widget.member == "Anna"
            assert not widget.guest_selected
            member = app._current_member()
            assert member is not None and member.account_ids == (ID_ANNA,)

    async def test_unbekannte_person_erscheint_als_gast(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        _merkliste(("Anna", ID_ANNA))
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app.show_person_tickets(ID_GERDA, "Gast, Gerda")
            await _settle(pilot)
            assert app.query_one("#view-tabs", TabbedContent).active == "tab-team"
            assert app._board_widget(MODE_TEAM).guest_selected
            assert app._current_member() == TeamMember(display_name="Gast, Gerda", account_ids=(ID_GERDA,))

    async def test_ungueltige_kennung_aendert_nichts(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app.show_person_tickets("kein gueltiges Format!", "Irgendwer")
            await _settle(pilot)
            assert app.query_one("#view-tabs", TabbedContent).active == "tab-list"
            assert app._team_guest is None

    async def test_menueaktion_fuehrt_zur_person(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            ticket = _ticket()
            app._menu_ticket = ticket
            app._person_menu_items(ticket)
            app._on_board_menu("person-1")
            await _settle(pilot)
            assert app.query_one("#view-tabs", TabbedContent).active == "tab-team"
            assert app._current_member() == TeamMember(display_name="Gast, Gerda", account_ids=(ID_GERDA,))

    async def test_gast_aufnehmen_speichert_die_merkliste(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        _merkliste(("Anna", ID_ANNA))
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app.show_person_tickets(ID_GERDA, "Gast, Gerda")
            await _settle(pilot)
            widget = app._board_widget(MODE_TEAM)
            widget.post_message(TicketBoardTable.GuestAddRequested())
            await _settle(pilot)
            assert widget.member == "Gast, Gerda"
            assert not widget.guest_selected
            assert app._team_guest is None

        gespeichert = json.loads(Settings.SETTINGS_FILE.read_text(encoding="utf-8"))["team_members"]
        assert {(e["display_name"], tuple(e["account_ids"])) for e in gespeichert} == {
            ("Anna", (ID_ANNA,)),
            ("Gast, Gerda", (ID_GERDA,)),
        }

    async def test_gleicher_name_bekommt_eine_nummer(self) -> None:
        from jira_timesheet.app import JiraTimesheetApp

        _merkliste(("Gast, Gerda", ID_ANNA))
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app.show_person_tickets(ID_GERDA, "Gast, Gerda")
            await _settle(pilot)
            app._board_widget(MODE_TEAM).post_message(TicketBoardTable.GuestAddRequested())
            await _settle(pilot)
            assert app._board_widget(MODE_TEAM).member == "Gast, Gerda (2)"

    async def test_gast_in_den_einstellungen_aufgenommen(self) -> None:
        # Wer die Person im Einstellungsdialog selbst eintraegt, sieht danach
        # denselben Menschen unter dem Namen der Merkliste - nicht jemand anderen.
        from jira_timesheet.app import JiraTimesheetApp

        _merkliste(("Anna", ID_ANNA))
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await _settle(pilot)
            app.show_person_tickets(ID_GERDA, "Gast, Gerda")
            await _settle(pilot)
            app._on_settings_closed(
                {
                    "team_members": [
                        {"display_name": "Anna", "account_ids": [ID_ANNA]},
                        {"display_name": "Gerda", "account_ids": [ID_GERDA]},
                    ]
                }
            )
            await _settle(pilot)
            widget = app._board_widget(MODE_TEAM)
            assert widget.member == "Gerda"
            assert not widget.guest_selected
            assert app._team_guest is None
